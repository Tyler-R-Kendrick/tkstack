"""Cross-stage and timeout tests for native process-group supervision."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/hill-climb/scripts'
sys.path.insert(0, str(SCRIPTS))
from experiment_runner import run_trial


@unittest.skipUnless(sys.platform.startswith('linux') and hasattr(os, 'waitid') and hasattr(os, 'WNOWAIT'),
                     'requires Linux non-reaping wait')
class ProcessIsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.case = self.root / 'case'
        self.case.write_text('case')
        self.executable = Path(sys.executable).resolve()
        self.native = SCRIPTS / 'experiment_native_check.py'

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def commit(self):
        self.git('add', '.')
        self.git('-c', 'user.name=T', '-c', 'user.email=t@e', 'commit', '-qm', 'base')
        return self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')

    def test_closed_pipe_child_cannot_modify_quality_stage(self):
        (self.repo / 'quality.txt').write_text('1')
        child = ("import time,pathlib; pathlib.Path('child-ready').write_text('ready'); "
                 "p=pathlib.Path('trigger'); "
                 "exec('while not p.exists():\\n time.sleep(.01)'); "
                 "pathlib.Path('quality.txt').write_text('3')")
        parent = ("import subprocess,sys,time,pathlib; "
                  f"subprocess.Popen([sys.executable,'-c',{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                  "p=pathlib.Path('child-ready'); exec('while not p.exists():\\n time.sleep(.01)'); "
                  "print('Ran 1 test in 0.01s')")
        (self.repo / 'test.py').write_text(parent)
        commit, tree = self.commit()
        judge = self.root / 'judge.py'
        judge.write_text("import sys,time,json,hashlib; from pathlib import Path; "
                         "Path('trigger').write_text('go'); time.sleep(.3); "
                         "q=int(Path('quality.txt').read_text()); "
                         "print(json.dumps({'case_sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),"
                         "'metrics':{'quality':q}}))")
        config = {'argv': [str(self.executable), 'test.py'], 'work_regex': r'Ran (?P<count>\d+) tests? in',
                  'gate': 'tests', 'metric': 'pass',
                  'quality': {'argv': [str(self.executable), str(judge), '{{case_file}}'],
                              'judge_file': str(judge), 'judge_sha256': self.sha(judge),
                              'executable_sha256': self.sha(self.executable)}}
        config_path = self.root / 'config.json'
        config_path.write_text(json.dumps(config))
        registry = {'target': {'argv': [str(self.executable), str(self.native), '--config', str(config_path),
                                         '--case-file', str(self.case)], 'cwd': '.'}}
        result = run_trial(self.repo, commit, tree, registry, ['target'], 'target', timeout=10)
        self.assertEqual(result['status'], 'passed', str(result))
        self.assertEqual(json.loads(result['stdout'])['metrics']['quality'], 1)

    def test_outer_timeout_stops_active_stage_group_and_descendants(self):
        started, child_pid, release = self.root / 'stage.pid', self.root / 'child.pid', self.root / 'release'
        self.addCleanup(release.touch)
        child = ("import os,time; from pathlib import Path; "
                 f"Path({str(child_pid)!r}).write_text(str(os.getpid())); "
                 f"p=Path({str(release)!r}); exec('while not p.exists():\\n time.sleep(.01)')")
        parent = ("import os,subprocess,sys,time; from pathlib import Path; "
                  f"Path({str(started)!r}).write_text(str(os.getpid())); "
                  f"subprocess.Popen([sys.executable,'-c',{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                  f"p=Path({str(child_pid)!r}); exec('while not p.exists():\\n time.sleep(.01)'); "
                  f"p=Path({str(release)!r}); exec('while not p.exists():\\n time.sleep(.01)')")
        (self.repo / 'test.py').write_text(parent)
        commit, tree = self.commit()
        config = {'argv':[str(self.executable),'test.py'], 'work_regex':r'Ran (?P<count>\d+) tests? in',
                  'gate':'tests', 'metric':'pass'}
        config_path = self.root / 'config.json'; config_path.write_text(json.dumps(config))
        registry = {'target': {'argv':[str(self.executable),str(self.native),'--config',str(config_path),
                                      '--case-file',str(self.case)],'cwd':'.'}}
        result = run_trial(self.repo,commit,tree,registry,['target'],'target',timeout=3)
        self.assertEqual(result['status'],'timeout',str(result))
        self.assertTrue(started.exists() and child_pid.exists(), 'both stage and child must have started')
        release.write_text('go')
        for path in (started, child_pid):
            pid = int(path.read_text())
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                stat = Path(f'/proc/{pid}/stat')
                try:
                    state = stat.read_text().split()[2]
                except FileNotFoundError:
                    break
                if state == 'Z':
                    break
                time.sleep(.01)
            else:
                self.fail(f'process {pid} survived outer timeout')

    def test_outer_timeout_during_handshake_cannot_start_target(self):
        (self.repo / 'source').write_text('x')
        commit, tree = self.commit()
        spawned, ran = self.root / 'supervisor.pid', self.root / 'target-ran'
        wrapper = self.root / 'wrapper.py'
        wrapper.write_text(
            "import importlib.util,sys,time\nfrom pathlib import Path\n"
            f"sys.path.insert(0,{str(SCRIPTS)!r})\n"
            f"spec=importlib.util.spec_from_file_location('native',{str(self.native)!r})\n"
            "native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)\n"
            "original=native.subprocess.Popen\n"
            "def delayed(*args,**kwargs):\n"
            " p=original(*args,**kwargs)\n"
            f" Path({str(spawned)!r}).write_text(str(p.pid))\n"
            " time.sleep(5)\n return p\n"
            "native.subprocess.Popen=delayed\n"
            f"native.execute([sys.executable,'-c',{('from pathlib import Path; Path(' + repr(str(ran)) + ').write_text(\'ran\')')!r}],10,1024)\n")
        registry = {'target': {'argv': [str(self.executable), str(wrapper)], 'cwd': '.'}}
        result = run_trial(self.repo, commit, tree, registry, ['target'], 'target', timeout=3)
        self.assertEqual(result['status'], 'timeout', str(result))
        self.assertTrue(spawned.exists(), 'timeout must occur after supervisor starts')
        pid = int(spawned.read_text())
        deadline = time.monotonic() + 3
        stopped = False
        while time.monotonic() < deadline:
            stat = Path(f'/proc/{pid}/stat')
            try:
                state = stat.read_text().split()[2]
            except FileNotFoundError:
                stopped = True
                break
            if state == 'Z':
                stopped = True
                break
            time.sleep(0.01)
        self.assertTrue(stopped, 'supervisor did not exit after parent closed handshake')
        self.assertFalse(ran.exists())


if __name__ == '__main__':
    unittest.main()
