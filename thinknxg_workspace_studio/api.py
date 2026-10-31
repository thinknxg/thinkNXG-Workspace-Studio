"""Whitelisted API used by the Workspace Studio designer page."""

import json

import frappe
from frappe import _
from frappe.utils import cint

from thinknxg_workspace_studio import publisher, schema

MANAGER_ROLES = ("System Manager", "Workspace Studio Manager")
PROP_FIELDS = (
    "workspace_title",
    "icon",
    "indicator_color",
    "parent_page",
    "module",
    "sequence_id",
    "publish_mode",
    "priority",
    "set_as_default",
    "take_over_existing",
    "publish_sidebar",
    "create_desktop_icon",
    "enable_dock",
    "dock_app",
    "dock_mode",
)
PACKAGE_FORMAT = "thinknxg-workspace-studio/1"


def _check():
    frappe.only_for(MANAGER_ROLES)


def has_app_permission():
    return bool(set(MANAGER_ROLES) & set(frappe.get_roles()))


def _parse(value, default):
    return schema.loads(value, default)


def _studio_payload(doc):
    logs = frappe.get_all(
        "Studio Publish Log",
        filters={"studio": doc.name},
        fields=["name", "action", "status", "published_on", "published_by", "rolled_back", "documents", "warnings"],
        order_by="creation desc",
        limit=15,
    )
    return {
        "name": doc.name,
        "title": doc.title,
        "status": doc.status,
        "modified": str(doc.modified),
        "version": doc.version,
        "last_published_on": str(doc.last_published_on or ""),
        "props": {f: doc.get(f) for f in PROP_FIELDS},
        "targets": [{"target_type": t.target_type, "role": t.role, "user": t.user} for t in doc.targets],
        "layout": schema.normalize_layout(_parse(doc.layout_json, {})),
        "sidebar": schema.normalize_sidebar(_parse(doc.sidebar_json, {})),
        "dock": schema.normalize_dock(_parse(doc.dock_json, {})),
        "published_index": _parse(doc.published_index, []),
        "logs": logs,
    }


@frappe.whitelist()
def get_studios():
    _check()
    rows = frappe.get_all(
        "Studio Workspace",
        fields=["name", "title", "workspace_title", "status", "icon", "publish_mode", "modified", "version",
                "layout_json", "enable_dock"],
        order_by="modified desc",
    )
    out = []
    for r in rows:
        layout = schema.normalize_layout(_parse(r.pop("layout_json"), {}))
        counts = {}
        for b in layout["blocks"]:
            counts[b["type"]] = counts.get(b["type"], 0) + 1
        r["block_count"] = len(layout["blocks"])
        r["block_types"] = counts
        r["modified"] = str(r["modified"])
        out.append(r)
    return out


@frappe.whitelist()
def get_studio(name):
    _check()
    return _studio_payload(frappe.get_doc("Studio Workspace", name))


@frappe.whitelist(methods=["POST"])
def create_studio(title, workspace_title=None, template="starter"):
    _check()
    title = (title or "").strip()
    if not title:
        frappe.throw(_("Studio Name is required."))
    if frappe.db.exists("Studio Workspace", title):
        frappe.throw(_("A studio named {0} already exists.").format(title))
    label = (workspace_title or title).strip()
    layout = schema.starter_layout(label) if template == "starter" else schema.blank_layout(label)
    sidebar = schema.sidebar_from_layout(layout) if template == "starter" else {"items": []}
    doc = frappe.get_doc(
        {
            "doctype": "Studio Workspace",
            "title": title,
            "workspace_title": label,
            "layout_json": json.dumps(layout),
            "sidebar_json": json.dumps(sidebar),
            "dock_json": json.dumps(schema.default_dock()),
        }
    )
    doc.insert()
    return doc.name


@frappe.whitelist(methods=["POST"])
def save_studio(name, payload, expected_modified=None):
    _check()
    data = _parse(payload, {})
    doc = frappe.get_doc("Studio Workspace", name)
    if expected_modified and str(doc.modified) != str(expected_modified):
        frappe.throw(
            _("{0} was changed by someone else after you opened it. Reload the designer to get the latest version.").format(name),
            title=_("Out of date"),
        )
    props = data.get("props") or {}
    for field in PROP_FIELDS:
        if field in props:
            doc.set(field, props[field])
    if "layout" in data:
        doc.layout_json = json.dumps(data["layout"])
    if "sidebar" in data:
        doc.sidebar_json = json.dumps(data["sidebar"])
    if "dock" in data:
        doc.dock_json = json.dumps(data["dock"])
    if "targets" in data:
        doc.set("targets", [])
        for t in data["targets"] or []:
            if t.get("target_type") in ("Role", "User"):
                doc.append("targets", {"target_type": t["target_type"], "role": t.get("role"), "user": t.get("user")})
    doc.save()
    return {"modified": str(doc.modified), "status": doc.status}


@frappe.whitelist(methods=["POST"])
def publish(name):
    _check()
    return publisher.publish(name)


@frappe.whitelist(methods=["POST"])
def unpublish(name):
    _check()
    return publisher.unpublish(name)


@frappe.whitelist(methods=["POST"])
def rollback(log_name):
    _check()
    return publisher.rollback(log_name)


@frappe.whitelist(methods=["POST"])
def delete_studio(name):
    _check()
    doc = frappe.get_doc("Studio Workspace", name)
    if doc.status in ("Published", "Modified"):
        publisher.unpublish(name)
        doc.reload()
    doc.flags.ignore_published_check = True
    doc.delete()
    return True


@frappe.whitelist()
def get_workspaces():
    _check()
    return frappe.get_all(
        "Workspace",
        filters={"public": 1},
        fields=["name", "title", "module", "icon"],
        order_by="sequence_id asc, title asc",
    )


@frappe.whitelist()
def read_workspace(workspace):
    """Return a workspace converted to designer layout + sidebar (no save)."""
    _check()
    ws = frappe.get_doc("Workspace", workspace)
    if not ws.public and ws.for_user != frappe.session.user:
        frappe.throw(_("You can only import public workspaces or your own private ones."))
    layout, warnings = schema.workspace_to_layout(ws.as_dict())
    sidebar = None
    if frappe.db.exists("DocType", "Workspace Sidebar") and frappe.db.exists("Workspace Sidebar", ws.name):
        sb = frappe.get_doc("Workspace Sidebar", ws.name)
        table = next((df.fieldname for df in sb.meta.get_table_fields()), None)
        if table:
            sidebar = schema.sidebar_from_rows([r.as_dict() for r in sb.get(table)])
    if not sidebar or not sidebar["items"]:
        sidebar = schema.sidebar_from_layout(layout)
    return {
        "layout": layout,
        "sidebar": sidebar,
        "warnings": warnings,
        "props": {"icon": ws.icon, "indicator_color": ws.get("indicator_color"), "parent_page": ws.parent_page},
        "roles": [r.role for r in ws.get("roles") or []],
    }


@frappe.whitelist(methods=["POST"])
def import_from_workspace(workspace, title):
    _check()
    data = read_workspace(workspace)
    name = create_studio(title, workspace_title=title, template="blank")
    doc = frappe.get_doc("Studio Workspace", name)
    doc.layout_json = json.dumps(data["layout"])
    doc.sidebar_json = json.dumps(data["sidebar"])
    for key, value in data["props"].items():
        if value:
            doc.set(key, value)
    for role in data["roles"]:
        doc.append("targets", {"target_type": "Role", "role": role})
    doc.save()
    return {"name": doc.name, "warnings": data["warnings"]}


@frappe.whitelist()
def resolve_audience(name):
    _check()
    doc = frappe.get_doc("Studio Workspace", name)
    p = publisher.Publisher(doc)
    users = p.resolve_users()
    details = frappe.get_all("User", filters={"name": ["in", users or [""]]}, fields=["name", "full_name", "user_image"])
    return {"count": len(users), "users": details[:200], "everyone": not doc.targets}


@frappe.whitelist()
def export_package(name):
    _check()
    doc = frappe.get_doc("Studio Workspace", name)
    return {
        "format": PACKAGE_FORMAT,
        "title": doc.title,
        "props": {f: doc.get(f) for f in PROP_FIELDS if f != "take_over_existing"},
        "targets": [{"target_type": t.target_type, "role": t.role, "user": t.user} for t in doc.targets],
        "layout": schema.normalize_layout(_parse(doc.layout_json, {})),
        "sidebar": schema.normalize_sidebar(_parse(doc.sidebar_json, {})),
        "dock": schema.normalize_dock(_parse(doc.dock_json, {})),
    }


@frappe.whitelist(methods=["POST"])
def import_package(package, title=None):
    _check()
    data = _parse(package, {})
    if data.get("format") != PACKAGE_FORMAT:
        frappe.throw(_("This file is not a Workspace Studio package."))
    title = (title or data.get("title") or "").strip()
    if not title:
        frappe.throw(_("Studio Name is required."))
    base, i = title, 2
    while frappe.db.exists("Studio Workspace", title):
        title = f"{base} ({i})"
        i += 1
    doc = frappe.new_doc("Studio Workspace")
    doc.title = title
    for field in PROP_FIELDS:
        if field in (data.get("props") or {}):
            doc.set(field, data["props"][field])
    doc.layout_json = json.dumps(data.get("layout") or {})
    doc.sidebar_json = json.dumps(data.get("sidebar") or {})
    doc.dock_json = json.dumps(data.get("dock") or {})
    for t in data.get("targets") or []:
        value = t.get("role") if t.get("target_type") == "Role" else t.get("user")
        doctype = "Role" if t.get("target_type") == "Role" else "User"
        if value and frappe.db.exists(doctype, value):
            doc.append("targets", t)
    doc.insert()
    return doc.name


@frappe.whitelist(methods=["POST"])
def duplicate_studio(name, title):
    _check()
    package = export_package(name)
    return import_package(json.dumps(package), title)


@frappe.whitelist()
def report_type(report):
    _check()
    return frappe.db.get_value("Report", report, "report_type")


@frappe.whitelist()
def get_meta_hints():
    """Small lists the designer offers as quick picks."""
    _check()
    return {
        "has_sidebar_doctype": bool(frappe.db.exists("DocType", "Workspace Sidebar")),
        "has_desktop_icon_doctype": bool(frappe.db.exists("DocType", "Desktop Icon")),
        "native_navigation": bool(frappe.db.exists("DocType", "Custom Sidebar") and frappe.db.exists("DocType", "Dock")),
        "installed_apps": frappe.get_installed_apps(),
        "frappe_version": frappe.__version__,
        "dock_enabled": cint(frappe.db.get_single_value("Workspace Studio Settings", "enable_dock")),
    }
