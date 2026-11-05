"""Lever's paired statistics helper stays the upstream script."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent


class LeverTests(unittest.TestCase):
    def test_paired_statistics_helper_runs_and_enforces_minimum_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            samples = Path(temporary) / 'samples.jsonl'
            script = ROOT / 'vendor/lever/skills/experiment-arms/scripts/arm_stats.py'
            for rounds, expected in [(6, 'KEEP'), (3, 'INCONCLUSIVE')]:
                with self.subTest(rounds=rounds):
                    rows = [{'round': number, 'arm': arm, 'value': value}
                            for number in range(rounds) for arm, value in [('control', 100), ('treatment', 80)]]
                    samples.write_text(''.join(json.dumps(row) + '\n' for row in rows))
                    result = subprocess.run([sys.executable, str(script), str(samples),
                                             '--control', 'control', '--bar-pct', '5', '--boot', '100'],
                                            capture_output=True, text=True, check=True)
                    self.assertIn(expected, result.stdout)


if __name__ == '__main__':
    unittest.main()
