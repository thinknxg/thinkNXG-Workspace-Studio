"""Pure unit tests for schema transforms (no bench needed): `python -m pytest tests/test_schema.py`."""

import json
import unittest

from thinknxg_workspace_studio import schema


class TestLayout(unittest.TestCase):
    def test_normalize_clamps_and_dedupes_ids(self):
        layout = schema.normalize_layout(
            {"blocks": [
                {"id": "a", "type": "shortcut", "col": 40, "data": {"link_to": "ToDo"}},
                {"id": "a", "type": "chart", "col": 0, "data": {}},
                {"type": "bogus"},
            ]}
        )
        self.assertEqual(len(layout["blocks"]), 2)
        self.assertEqual(layout["blocks"][0]["col"], 12)
        self.assertEqual(layout["blocks"][1]["col"], 1)
        self.assertNotEqual(layout["blocks"][0]["id"], layout["blocks"][1]["id"])
        self.assertEqual(layout["blocks"][0]["data"]["label"], "ToDo")

    def test_payload_round_trip(self):
        layout = schema.starter_layout("Home")
        payload, warnings = schema.build_workspace_payload(layout)
        self.assertEqual(warnings, [])
        types = [c["type"] for c in payload["content"]]
        self.assertEqual(types.count("shortcut"), 4)
        self.assertEqual(len(payload["shortcuts"]), 4)
        card_break = [l for l in payload["links"] if l["type"] == "Card Break"][0]
        self.assertEqual(card_break["link_count"], 3)
        ql = payload["quick_lists"][0]
        self.assertEqual(json.loads(ql["quick_list_filter"])[0][:4], ["ToDo", "status", "=", "Open"])

        ws = dict(payload, content=json.dumps(payload["content"]))
        back, warns = schema.workspace_to_layout(ws)
        self.assertEqual(warns, [])
        self.assertEqual([b["type"] for b in back["blocks"]], [b["type"] for b in layout["blocks"]])
        self.assertEqual(back["blocks"][0]["data"]["text"], "Home")
        self.assertEqual(back["blocks"][-1]["data"]["filters"], [["status", "=", "Open"]])

    def test_unique_labels(self):
        layout = {"blocks": [
            {"type": "shortcut", "data": {"label": "Sales", "link_to": "Sales Order"}},
            {"type": "shortcut", "data": {"label": "Sales", "link_to": "Sales Invoice"}},
        ]}
        payload, _ = schema.build_workspace_payload(layout)
        self.assertEqual([s["label"] for s in payload["shortcuts"]], ["Sales", "Sales (2)"])
        self.assertEqual(payload["content"][1]["data"]["shortcut_name"], "Sales (2)")

    def test_role_filtering_and_skips(self):
        layout = {"blocks": [
            {"type": "shortcut", "roles": ["Accounts User"], "data": {"link_to": "Journal Entry"}},
            {"type": "shortcut", "data": {"link_to": "ToDo"}},
            {"type": "chart", "data": {}},
        ]}
        payload, warnings = schema.build_workspace_payload(layout, user_roles=["Sales User"])
        self.assertEqual([s["link_to"] for s in payload["shortcuts"]], ["ToDo"])
        self.assertEqual(len(warnings), 1)
        payload, _ = schema.build_workspace_payload(layout)
        self.assertEqual(len(payload["shortcuts"]), 2)

    def test_header_escaping(self):
        payload, _ = schema.build_workspace_payload({"blocks": [{"type": "header", "data": {"text": "<script>x</script>"}}]})
        self.assertIn("&lt;script&gt;", payload["content"][0]["data"]["text"])

    def test_stats_filter_dict(self):
        payload, _ = schema.build_workspace_payload(
            {"blocks": [{"type": "shortcut", "data": {"link_to": "ToDo", "filters": [["ToDo", "status", "=", "Open"]]}}]}
        )
        self.assertEqual(json.loads(payload["shortcuts"][0]["stats_filter"]), {"status": ["=", "Open"]})


class TestSidebarDock(unittest.TestCase):
    def test_sidebar_nesting_flattened(self):
        sb = schema.normalize_sidebar({"items": [
            {"type": "section", "label": "A", "children": [
                {"type": "section", "children": [{"type": "link", "link_to": "ToDo"}]},
                {"type": "spacer"},
            ]},
            {"type": "link", "link_type": "URL", "url": "https://x.y"},
        ]})
        self.assertEqual(len(sb["items"]), 2)
        self.assertEqual([c["type"] for c in sb["items"][0]["children"]], ["link", "spacer"])
        rows = schema.flatten_sidebar(sb)
        self.assertEqual([r["kind"] for r in rows], ["section", "link", "spacer", "link"])
        self.assertEqual(rows[1]["child"], 1)
        back = schema.sidebar_from_rows(
            [{"type": "Section Break", "label": "A"}, {"type": "Link", "label": "ToDo", "link_to": "ToDo", "child": 1}]
        )
        self.assertEqual(back["items"][0]["children"][0]["link_to"], "ToDo")

    def test_sidebar_role_filter(self):
        sb = {"items": [{"type": "section", "label": "Fin", "roles": ["Accounts User"], "children": [{"type": "link", "link_to": "GL"}]}]}
        self.assertEqual(schema.flatten_sidebar(sb, ["Sales User"]), [])

    def test_sidebar_from_layout(self):
        sb = schema.sidebar_from_layout(schema.starter_layout())
        self.assertEqual([s["label"] for s in sb["items"]], ["Shortcuts", "Daily Work"])

    def test_dock_normalize(self):
        d = schema.normalize_dock({"position": "top", "items": [
            {"type": "item", "link_type": "New", "link_to": "ToDo", "color": "red;}"},
            {"type": "separator"},
        ]})
        self.assertEqual(d["position"], "bottom")
        self.assertEqual(d["items"][0]["color"], "#4f46e5")
        self.assertEqual(d["items"][1]["type"], "separator")


if __name__ == "__main__":
    unittest.main()
