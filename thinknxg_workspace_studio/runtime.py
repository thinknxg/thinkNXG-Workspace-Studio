"""Desk runtime: resolves which published Dock applies to the current user."""

import frappe
from frappe.utils import cint

from thinknxg_workspace_studio import schema

CACHE_PREFIX = "wss_runtime::"
QUERY_REPORT_TYPES = ("Query Report", "Script Report", "Custom Report")
VIEW_ROUTES = {
    "": None,
    "List": None,
    "Report Builder": "Report",
    "Dashboard": "Dashboard",
    "Calendar": "Calendar",
    "Kanban": "Kanban",
}


def _cache():
    return frappe.cache() if callable(frappe.cache) else frappe.cache


def clear_runtime_cache(*args, **kwargs):
    try:
        _cache().delete_keys(CACHE_PREFIX)
    except Exception:
        pass


@frappe.whitelist()
def get_runtime_config():
    user = frappe.session.user
    if user == "Guest":
        return {}
    settings = frappe.get_cached_doc("Workspace Studio Settings")
    if not cint(settings.enable_dock):
        return {"dock": None}
    key = CACHE_PREFIX + user
    cached = _cache().get_value(key)
    if cached is not None:
        return cached
    result = {
        "dock": resolve_dock(user),
        "hide_on_mobile": cint(settings.hide_dock_on_mobile),
        "offset": cint(settings.dock_offset) or 14,
    }
    minutes = cint(settings.runtime_cache_minutes) or 10
    _cache().set_value(key, result, expires_in_sec=minutes * 60)
    return result


def match_rank(targets, user, user_roles):
    """Lower is better: 0 = user target, 1 = role target, 2 = no audience (everyone)."""
    if not targets:
        return 2
    if any(t.target_type == "User" and t.user == user for t in targets):
        return 0
    if any(t.target_type == "Role" and t.role in user_roles for t in targets):
        return 1
    return None


def resolve_dock(user):
    studios = frappe.get_all(
        "Studio Workspace",
        filters={"status": ["in", ["Published", "Modified"]], "enable_dock": 1},
        fields=["name", "priority", "published_dock_json"],
    )
    studios = [s for s in studios if s.published_dock_json]
    if not studios:
        return None
    targets = frappe.get_all(
        "Studio Target",
        filters={"parenttype": "Studio Workspace", "parent": ["in", [s.name for s in studios]]},
        fields=["parent", "target_type", "role", "user"],
    )
    by_parent = {}
    for t in targets:
        by_parent.setdefault(t.parent, []).append(t)

    user_roles = frappe.get_roles(user)
    candidates = []
    for s in studios:
        rank = match_rank(by_parent.get(s.name, []), user, user_roles)
        if rank is not None:
            candidates.append((rank, -cint(s.priority), s.name, s))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[:3])
    studio = candidates[0][3]

    dock = schema.normalize_dock(schema.loads(studio.published_dock_json, {}))
    if not dock["enabled"]:
        return None
    items = []
    for it in dock["items"]:
        if it["type"] == "separator":
            if items and items[-1]["type"] != "separator":
                items.append(it)
            continue
        if not schema.visible_for(it["roles"], user_roles):
            continue
        action = resolve_action(it, user, user_roles)
        if action:
            items.append(
                {
                    "type": "item",
                    "label": it["label"],
                    "icon": it["icon"],
                    "color": it["color"],
                    "action": action,
                }
            )
    while items and items[-1]["type"] == "separator":
        items.pop()
    if not items:
        return None
    dock["items"] = items
    dock["studio"] = studio.name
    return dock


def resolve_action(item, user, user_roles):
    lt, target = item["link_type"], item["link_to"]
    try:
        if lt == "URL":
            return {"kind": "url", "url": item["url"], "new_tab": item["new_tab"]} if item["url"] else None
        if not target:
            return None
        if lt in ("DocType", "New"):
            if not frappe.db.exists("DocType", target):
                return None
            if lt == "New":
                return {"kind": "new", "doctype": target} if frappe.has_permission(target, "create", user=user) else None
            if not frappe.has_permission(target, "read", user=user):
                return None
            view = item.get("doc_view") or ""
            if view == "Tree":
                return {"kind": "route", "route": ["Tree", target]}
            if view == "New":
                return {"kind": "new", "doctype": target}
            sub = VIEW_ROUTES.get(view)
            return {"kind": "route", "route": ["List", target, sub] if sub else ["List", target]}
        if lt == "Report":
            info = frappe.db.get_value("Report", target, ["report_type", "ref_doctype"], as_dict=True)
            if not info or not frappe.get_doc("Report", target).is_permitted():
                return None
            if info.report_type in QUERY_REPORT_TYPES:
                return {"kind": "route", "route": ["query-report", target]}
            return {"kind": "route", "route": ["List", info.ref_doctype, "Report", target]}
        if lt == "Page":
            if not frappe.db.exists("Page", target) or not frappe.get_doc("Page", target).is_permitted():
                return None
            return {"kind": "route", "route": [target]}
        if lt == "Dashboard":
            return {"kind": "route", "route": ["dashboard-view", target]} if frappe.db.exists("Dashboard", target) else None
        if lt == "Workspace":
            ws = frappe.db.get_value("Workspace", target, ["name", "title", "public", "for_user"], as_dict=True)
            if not ws:
                return None
            if not cint(ws.public):
                if ws.for_user != user:
                    return None
                return {"kind": "route", "route": ["private", _slug(ws.title or ws.name)]}
            roles = frappe.get_all("Has Role", filters={"parent": ws.name, "parenttype": "Workspace"}, pluck="role")
            if roles and not set(roles) & set(user_roles):
                return None
            return {"kind": "route", "route": [_slug(ws.title or ws.name)]}
    except Exception:
        frappe.log_error(title="Workspace Studio: dock item resolution failed")
        return None
    return None


def _slug(text):
    return (text or "").strip().lower().replace(" ", "-")
