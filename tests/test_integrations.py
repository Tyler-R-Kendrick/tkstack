"""harnesses/integrations.json is a retained pin file, not an applied installer input."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class IntegrationsPinTests(unittest.TestCase):
    def test_integrations_json_parses(self):
        document = json.loads((ROOT / "harnesses" / "integrations.json").read_text())
        self.assertEqual(document["version"], 1)
        tools = document["tools"]
        self.assertIsInstance(tools, dict)
        self.assertTrue(tools)
        for name, tool in tools.items():
            self.assertIsInstance(name, str)
            self.assertTrue(name)
            self.assertIsInstance(tool, dict)
            self.assertIsInstance(tool.get("kind"), str)
            self.assertTrue(tool["kind"])


if __name__ == "__main__":
    unittest.main()
