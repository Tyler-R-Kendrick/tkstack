"""Graphify source packaging, scoped state, and native AST/CLI/MCP/hook contracts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import install
import graphify_install
import graphify_adapter
import python_runtime
import setup_integrations


class GraphifyIntegrationTests(unittest.TestCase):
    def test_official_identity_and_pins_have_licenses_and_exact_inventory(self):
        source = json.loads((ROOT / 'sources.lock.json').read_text())['sources']['graphify']
        self.assertEqual(source['repository'], 'https://github.com/Graphify-Labs/graphify')
        self.assertEqual(len(source['revision']), 40)
        self.assertEqual(source['version'], '0.9.97')
        for name in ('LICENSE', 'LICENSE-MIT', 'NOTICE'):
            self.assertIn(name, source['files'])
        recipe = (ROOT / 'harnesses/graphify/requirements.in').read_text().strip()
        self.assertEqual(recipe, 'graphifyy[mcp]==0.9.97')
        lock = (ROOT / 'harnesses/graphify/requirements.lock').read_text()
        self.assertIn('graphifyy==0.9.97', lock)
        self.assertIn('--hash=sha256:', lock)
        install.verify_vendor(ROOT)

    def test_first_install_plans_all_native_skill_links_before_generated_views_exist(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = json.loads((ROOT / 'sources.lock.json').read_text())['sources']['graphify']
            (root / 'sources.lock.json').write_text(json.dumps({'version': 1, 'sources': {'graphify': source}}))
            plan = install.link_plan(root, root / 'target', ['codex', 'claude', 'cursor'])
            self.assertEqual({target.parent.name for _, target in plan}, {'skills'})
            self.assertEqual(len(plan), 3)
            self.assertTrue(all(target.name == 'graphify' for _, target in plan))
            self.assertFalse((root / '.tkstack').exists())
            self.assertEqual(len({source for source, _ in plan}), 3)

    def test_native_views_keep_profiles_references_and_remove_global_auto_install(self):
        source = json.loads((ROOT / 'sources.lock.json').read_text())['sources']['graphify']
        for harness in ('codex', 'claude', 'cursor'):
            destination = graphify_install.view_directory(ROOT, 'graphify', harness) / 'graphify'
            files = graphify_install.render(ROOT, 'graphify', source['skill_templates'][harness], destination)
            text = files['SKILL.md'].decode()
            self.assertIn('name: graphify', text)
            self.assertIn('.tkstack/graphify', text)
            self.assertNotIn('graphify-out', text)
            self.assertNotIn('uv tool install', text)
            self.assertNotIn('--break-system-packages', text)
            self.assertIn('scripts/tool.py graphify query', text)
            self.assertIn('scripts/python', files)
            self.assertEqual(sum(name.startswith('references/') for name in files), 8)

    def test_doctor_detects_corrupt_generated_views_without_repair_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = json.loads((ROOT / 'sources.lock.json').read_text())['sources']['graphify']
            source = {**source, 'skill_templates': {'default': source['skill_templates']['default']}}
            (root / 'sources.lock.json').write_text(json.dumps({'version': 1, 'sources': {'graphify': source}}))
            import shutil
            shutil.copytree(ROOT / 'vendor/graphify', root / 'vendor/graphify')
            graphify_install.prepare_views(root)
            graphify_install.check_views(root)
            target = graphify_install.view_directory(root, 'graphify') / 'graphify/SKILL.md'
            target.write_text(target.read_text().replace('.tkstack/graphify', 'graphify-out'))
            before = target.read_bytes()
            with self.assertRaisesRegex(ValueError, 'missing or stale'):
                graphify_install.check_views(root)
            self.assertEqual(target.read_bytes(), before)
            graphify_install.prepare_views(root)
            graphify_install.check_views(root)
            launcher = target.parent / 'scripts/python'
            launcher.chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'missing or stale'):
                graphify_install.check_views(root)
            graphify_install.prepare_views(root)
            graphify_install.check_views(root)

    def test_runtime_environment_is_read_only_for_queries_and_rejects_state_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.git').mkdir()
            with patch.object(Path, 'cwd', return_value=root), patch.dict(os.environ, {'GRAPHIFY_OUT': '', 'TKSTACK_WORKSPACE_DIR': ''}):
                environment = graphify_adapter.runtime_environment(ROOT, ['query', 'symbol'])
                self.assertEqual(environment['GRAPHIFY_OUT'], str(root / '.tkstack/graphify'))
                self.assertEqual(environment['GRAPHIFY_NO_AUTO_REFRESH'], '1')
                self.assertFalse((root / '.tkstack').exists())
                graphify_adapter.runtime_environment(ROOT, ['extract', '.'])
                self.assertTrue((root / '.tkstack/.gitignore').is_file())
            with patch.dict(os.environ, {'GRAPHIFY_OUT': str(root / 'outside')}):
                with self.assertRaises(ValueError):
                    graphify_adapter.runtime_environment(ROOT, ['extract', '.'])

    def test_clone_defaults_and_multifolder_extraction_have_private_separate_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.git').mkdir()
            with patch.object(Path, 'cwd', return_value=root), patch.dict(os.environ, {'GRAPHIFY_OUT': '', 'TKSTACK_WORKSPACE_DIR': ''}):
                args = graphify_adapter.managed_arguments(ROOT, ['clone', 'https://github.com/owner/project.git'])
                self.assertEqual(args[-2:], ['--out', str(root / '.tkstack/graphify/repos/owner/project')])
                (root / 'first').mkdir()
                (root / 'second').mkdir()
                first = graphify_adapter.runtime_environment(ROOT, ['extract', './first'])
                second = graphify_adapter.runtime_environment(ROOT, ['extract', './second'])
                self.assertNotEqual(first['GRAPHIFY_OUT'], second['GRAPHIFY_OUT'])
                self.assertEqual(first['GRAPHIFY_OUT'], str(root / 'first/.tkstack/graphify'))
                self.assertEqual(second['GRAPHIFY_OUT'], str(root / 'second/.tkstack/graphify'))
                with self.assertRaisesRegex(ValueError, 'must exist'):
                    graphify_adapter.runtime_environment(ROOT, ['extract', './missing'])
                self.assertFalse((root / 'missing').exists())
                for command in ('install', 'uninstall', 'global'):
                    with self.assertRaises(ValueError):
                        graphify_adapter.managed_arguments(ROOT, [command])

    def test_guard_registration_is_native_claude_only_and_runtime_gated(self):
        with patch.object(setup_integrations, 'ready', return_value=False):
            hooks = setup_integrations.hook_entries(ROOT, 'claude')
            self.assertNotIn('graphify', json.dumps(hooks))
        with patch.object(setup_integrations, 'ready', return_value=True):
            for harness in ('codex', 'claude', 'cursor'):
                hooks = setup_integrations.hook_entries(ROOT, harness)
                self.assertEqual('graphify' in json.dumps(hooks), harness == 'claude')


@unittest.skipUnless(os.environ.get('TKSTACK_GRAPHIFY_NATIVE'), 'Set TKSTACK_GRAPHIFY_NATIVE=1 for the installed locked runtime contracts')
class NativeGraphifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.fixture = Path(cls.temporary.name) / 'project with spaces'
        cls.fixture.mkdir()
        subprocess.run(['git', 'init', '-q', str(cls.fixture)], check=True)
        (cls.fixture / 'arithmetic.py').write_text('def double(value):\n    return value * 2\n\ndef calculate(value):\n    return double(value) + 1\n')
        (cls.fixture / 'test_arithmetic.py').write_text('from arithmetic import calculate\n\ndef test_calculate():\n    assert calculate(3) == 7\n')
        cls.environment = {key: value for key, value in os.environ.items() if key not in ('GRAPHIFY_OUT', 'TKSTACK_WORKSPACE_DIR')}
        result = cls.invoke('extract', str(cls.fixture), '--code-only', '--no-cluster', '--max-workers', '2')
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def invoke(cls, *args, input=None):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/tool.py'), 'graphify', *args],
                              cwd=cls.fixture, env=cls.environment, input=input,
                              capture_output=True, text=True, timeout=90)

    def test_native_ast_calls_queries_paths_and_negative_lookup(self):
        tool = json.loads((ROOT / 'harnesses/integrations.json').read_text())['tools']['graphify']
        self.assertTrue(python_runtime.package_ready(ROOT, 'graphify', tool))
        graph = json.loads((self.fixture / '.tkstack/graphify/graph.json').read_text())
        labels = {item['id']: item['label'] for item in graph['nodes']}
        self.assertEqual(graph['input_tokens'], 0)
        self.assertEqual(graph['output_tokens'], 0)
        self.assertTrue(any(labels[edge['source']] == 'calculate()' and labels[edge['target']] == 'double()'
                            and edge['relation'] == 'calls' and edge['confidence'] == 'EXTRACTED' for edge in graph['edges']))
        result = self.invoke('query', 'calculate')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('calculate()', result.stdout)
        result = self.invoke('path', 'calculate', 'double')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('calculate() --calls [EXTRACTED]--> double()', result.stdout)
        self.assertEqual(self.invoke('explain', 'unknown_fixture_symbol_93827').returncode, 4)
        self.assertFalse((self.fixture / 'graphify-out').exists())

    def test_generated_native_python_launcher_uses_the_frozen_interpreter(self):
        launcher = ROOT / '.tkstack/skill-views/graphify/codex/graphify/scripts/python'
        result = subprocess.run([str(launcher), '-c', 'from graphify.paths import GRAPHIFY_OUT;import importlib.metadata;print(importlib.metadata.version("graphifyy"));print(GRAPHIFY_OUT)'],
                                cwd=self.fixture, env=self.environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('0.9.97', result.stdout)
        self.assertIn('/.tkstack/graphify', result.stdout)

    def test_native_hook_nudges_without_denying_or_global_refresh(self):
        payload = {'session_id': 'tkstack-fixture', 'cwd': str(self.fixture), 'tool_name': 'Grep', 'tool_input': {'pattern': 'calculate'}}
        command = [sys.executable, str(ROOT / 'scripts/run_hook.py'), 'graphify', 'claude', 'search']
        result = subprocess.run(command, cwd=self.fixture, env=self.environment, input=json.dumps(payload), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout)
        self.assertIn('graphify', json.dumps(response).lower())
        self.assertNotIn('deny', json.dumps(response).lower())

    def test_native_mcp_initializes_queries_and_keeps_projects_separate(self):
        other = Path(self.temporary.name) / 'second project'
        other.mkdir()
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        (other / 'other.py').write_text('def triple(value):\n    return value * 3\n')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/tool.py'), 'graphify', 'extract', str(other), '--code-only', '--no-cluster', '--max-workers', '2'],
                                cwd=other, env=self.environment, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        program = r'''import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def run():
 params=StdioServerParameters(command=sys.executable,args=[sys.argv[1],'graphify','mcp'],cwd=sys.argv[2],env=dict(os.environ))
 async with stdio_client(params) as (read,write):
  async with ClientSession(read,write) as session:
   await session.initialize()
   listing=await session.list_tools()
   assert {'query_graph','shortest_path','graph_stats'} <= {item.name for item in listing.tools}
   first=await session.call_tool('query_graph',{'question':'calculate'})
   first=first.model_dump(mode='json',by_alias=True)
   assert 'calculate()' in json.dumps(first), first
   second=await session.call_tool('query_graph',{'question':'triple','project_path':sys.argv[3]})
   second=second.model_dump(mode='json',by_alias=True)
   assert 'triple()' in json.dumps(second) and 'calculate()' not in json.dumps(second), second
   missing=await session.call_tool('unknown_tkstack_tool',{})
   missing=missing.model_dump(mode='json',by_alias=True)
   assert 'Unknown tool: unknown_tkstack_tool' in json.dumps(missing), missing
   print(json.dumps({'tools':len(listing.tools),'first_project':'calculate','second_project':'triple','unknown_tool_reported':True}))
asyncio.run(run())
'''
        result = subprocess.run([str(ROOT / '.tkstack/runtime/graphify/bin/python'), '-B', '-c', program,
                                 str(ROOT / 'scripts/tool.py'), str(self.fixture), str(other)],
                                env=self.environment, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['unknown_tool_reported'])


if __name__ == '__main__':
    unittest.main()
