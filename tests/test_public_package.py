"""Static review of the export reviewers can import into n8n."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestN8NImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flow = json.loads((ROOT / "workflows" / "n8n-import-demo.json").read_text())

    def test_is_not_active(self):
        self.assertFalse(self.flow["active"])

    def test_one_manual_trigger(self):
        names = [n["type"] for n in self.flow["nodes"]]
        self.assertEqual(names.count("n8n-nodes-base.manualTrigger"), 1)

    def test_has_nine_executable_decision_stages(self):
        self.assertEqual(sum(n["type"] == "n8n-nodes-base.code" for n in self.flow["nodes"]), 9)

    def test_no_network_or_credential_nodes(self):
        for n in self.flow["nodes"]:
            self.assertNotIn("credentials", n)
            self.assertNotIn("webhook", n["type"].lower())
            self.assertNotIn("httpRequest", n["type"])
            self.assertNotIn("googleSheets", n["type"])
            self.assertNotIn("googleChat", n["type"])

    def test_all_nodes_are_connected_in_order(self):
        nodes = self.flow["nodes"]
        for left, right in zip(nodes, nodes[1:]):
            outgoing = self.flow["connections"][left["name"]]["main"][0]
            self.assertEqual(outgoing[0]["node"], right["name"])

    def test_synthetic_fixture_embedded(self):
        self.assertIn("synthetic", self.flow["nodes"][1]["parameters"]["jsCode"])


if __name__ == "__main__":
    unittest.main()
