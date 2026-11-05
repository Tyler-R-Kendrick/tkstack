"""Graphify is linked as a copy of the upstream skill text."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))
import install


class GraphifyInstallTests(unittest.TestCase):
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

    def test_prepare_graphify_copies_upstream_skill_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = json.loads((ROOT / 'sources.lock.json').read_text())['sources']['graphify']
            (root / 'sources.lock.json').write_text(json.dumps({'version': 1, 'sources': {'graphify': source}}))
            shutil.copytree(ROOT / 'vendor/graphify', root / 'vendor/graphify')
            install.prepare_graphify(root)
            upstream = root / 'vendor/graphify'
            for harness, profile in source['skill_templates'].items():
                view = install.skill_view(root, 'graphify', harness) / 'graphify'
                skill = view / 'SKILL.md'
                original = upstream / profile['entrypoint']
                self.assertEqual(skill.read_bytes(), original.read_bytes())
                references = upstream / profile['references']
                copied = sorted(path.name for path in (view / 'references').glob('*.md'))
                self.assertEqual(copied, sorted(path.name for path in references.glob('*.md')))
                sample = next(references.glob('*.md'))
                self.assertEqual((view / 'references' / sample.name).read_bytes(), sample.read_bytes())
            outside = root / 'outside'
            outside.mkdir()
            planted = install.skill_view(root, 'graphify', 'codex')
            if planted.exists():
                shutil.rmtree(planted)
            planted.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'must not be a symlink'):
                install.prepare_graphify(root)


if __name__ == '__main__':
    unittest.main()
