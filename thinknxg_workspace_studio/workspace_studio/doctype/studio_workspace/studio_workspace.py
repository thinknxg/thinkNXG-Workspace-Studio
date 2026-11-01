import json

import frappe
from frappe import _
from frappe.model.document import Document

from thinknxg_workspace_studio import schema

DESIGN_FIELDS = ("layout_json", "sidebar_json", "dock_json")


class StudioWorkspace(Document):
    def validate(self):
        self.title = (self.title or "").strip()
        self.workspace_title = (self.workspace_title or self.title).strip()
        if len(self.workspace_title) > 100:
            frappe.throw(_("Workspace Label must be 100 characters or fewer."))

        # Designer state is never edited by hand; keep it canonical.
        self.layout_json = json.dumps(schema.normalize_layout(schema.loads(self.layout_json, {})))
        self.sidebar_json = json.dumps(schema.normalize_sidebar(schema.loads(self.sidebar_json, {})))
        self.dock_json = json.dumps(schema.normalize_dock(schema.loads(self.dock_json, {})))

        self._validate_targets()

        if not self.flags.from_publisher and not self.is_new() and self.status == "Published":
            watched = DESIGN_FIELDS + (
                "workspace_title",
                "icon",
                "indicator_color",
                "parent_page",
                "module",
                "sequence_id",
                "publish_mode",
                "set_as_default",
                "publish_sidebar",
                "create_desktop_icon",
                "enable_dock",
                "dock_app",
                "dock_mode",
            )
            if any(self.has_value_changed(f) for f in watched) or self._targets_changed():
                self.status = "Modified"

    def _validate_targets(self):
        seen, rows = set(), []
        for row in self.targets:
            value = row.role if row.target_type == "Role" else row.user
            if not value:
                continue
            key = (row.target_type, value)
            if key in seen:
                continue
            seen.add(key)
            if row.target_type == "Role":
                row.user = None
            else:
                row.role = None
            rows.append(row)
        self.set("targets", rows)

    def _targets_changed(self):
        before = self.get_doc_before_save()
        if not before:
            return False

        def key(doc):
            return sorted((t.target_type, t.role or t.user or "") for t in doc.targets)

        return key(before) != key(self)

    def on_trash(self):
        if self.status in ("Published", "Modified") and not self.flags.ignore_published_check:
            frappe.throw(
                _("Unpublish this studio before deleting it, so the workspaces it created are removed cleanly.")
            )
        # The publish logs belong to the studio; they would otherwise block the delete (LinkExistsError).
        for log in frappe.get_all("Studio Publish Log", filters={"studio": self.name}, pluck="name"):
            frappe.delete_doc("Studio Publish Log", log, ignore_permissions=True, force=True)
