"""End-to-end check on a real v16 site.

    bench --site <site> execute thinknxg_workspace_studio.tests.e2e_v16.run

Creates test users and studios (prefixed E2E), publishes them, and prints what each user's desk
boot receives. Safe to re-run; it unpublishes and recreates its own records.
"""

import json
import traceback

import frappe

from thinknxg_workspace_studio import api, diagnostics, publisher, schema

USERS = {
    "e2e.sales1@example.com": ["Sales User"],
    "e2e.sales2@example.com": ["Sales User"],
    "e2e.manager@example.com": ["Sales User", "System Manager"],
}


def _user(email, roles):
    if not frappe.db.exists("User", email):
        u = frappe.new_doc("User")
        u.email = email
        u.first_name = email.split("@")[0]
        u.send_welcome_email = 0
        u.insert(ignore_permissions=True)
    u = frappe.get_doc("User", email)
    u.set("roles", [])
    for r in roles:
        u.append("roles", {"role": r})
    u.flags.ignore_permissions = True
    u.save(ignore_permissions=True)


def _studio(title, dock_app="", mode="Shared (Role-based)", dock_mode="Add to the app's Dock", dock_items=None, priority=10):
    if frappe.db.exists("Studio Workspace", title):
        doc = frappe.get_doc("Studio Workspace", title)
        if doc.status in ("Published", "Modified"):
            publisher.unpublish(title)
        doc = frappe.get_doc("Studio Workspace", title)
        doc.flags.ignore_published_check = True
        doc.delete(ignore_permissions=True)
    api.create_studio(title)
    doc = frappe.get_doc("Studio Workspace", title)
    doc.publish_mode = mode
    doc.dock_app = dock_app
    doc.dock_mode = dock_mode
    doc.set_as_default = 1
    doc.priority = priority
    doc.create_desktop_icon = 1 if dock_app == "thinknxg_workspace_studio" else 0
    doc.set("targets", [{"target_type": "Role", "role": "Sales User"}])
    dock = schema.default_dock()
    dock["items"] = dock_items or [
        {"type": "item", "label": "Docs", "link_type": "URL", "url": "https://docs.thinknxg.com"},
        {"type": "item", "label": "New To Do", "link_type": "New", "link_to": "ToDo"},
    ]
    doc.dock_json = json.dumps(dock)
    doc.save(ignore_permissions=True)
    return title


def _publish(title):
    try:
        res = publisher.publish(title)
        print(f"  publish {title}: {res['status']}")
        for d in res["documents"]:
            print(f"     {d['action']:>16}  {d['doctype']}: {d['name']}")
        for w in res["warnings"]:
            print(f"     note: {w}")
        return True
    except Exception:
        print(f"  publish {title}: FAILED")
        print("     " + traceback.format_exc().replace("\n", "\n     "))
        frappe.db.rollback()
        return False


def _boot_as(user):
    """What the desk boot gives `user`: rails, module sidebars, workspaces, home."""
    from frappe.boot import get_app_data, get_module_sidebars
    from frappe.desk.desktop import get_workspaces
    from frappe.desk.doctype.dock.dock import resolve_dock

    actor = frappe.session.user
    frappe.set_user(user)
    diagnostics._reset_request_caches()
    try:
        out = {}
        out["pages"] = sorted(p.name for p in get_workspaces()["pages"] if "E2E" in p.name or "Workspace Studio" in p.name)
        sidebars = get_module_sidebars()
        out["sidebars"] = {k: [i.get("label") for i in v.get("items", [])] for k, v in sidebars.items() if "E2E" in k}
        out["sidebar_app"] = {k: v.get("app") for k, v in sidebars.items() if "E2E" in k}
        rails = resolve_dock()
        out["rails"] = {a: [(r.get("title") or r.get("link_to") or r.get("url"), r.get("link_type"), r.get("hidden")) for r in rail] for a, rail in rails.items() if a in ("erpnext", "thinknxg_workspace_studio")}
        apps = get_app_data()
        out["apps"] = [(a["app_name"], a.get("on_apps_screen"), len(a.get("dock") or [])) for a in apps]
        out["default_workspace"] = frappe.db.get_value("User", user, "default_workspace")
        return out
    finally:
        frappe.set_user(actor)
        diagnostics._reset_request_caches()


def run():
    frappe.set_user("Administrator")
    for email, roles in USERS.items():
        _user(email, roles)
    frappe.db.commit()

    print("\n== 1. Shared studio on the thinkNXG ERP rail (your ESTIMATION case)")
    _studio("E2E ESTIMATION")
    _publish("E2E ESTIMATION")
    frappe.db.commit()

    print("\n== 2. Three studios on the Workspaces app")
    frappe.db.set_value("User", "e2e.manager@example.com", "default_workspace", None)
    for t, prio in (("E2E Finance Desk", 10), ("E2E Sales Desk", 30), ("E2E Ops Desk", 20)):
        _studio(t, dock_app="thinknxg_workspace_studio", priority=prio)
        _publish(t)
        frappe.db.commit()

    for user in ["Administrator", *USERS]:
        print(f"\n== boot as {user}")
        print(json.dumps(_boot_as(user), indent=1, default=str))

    print("\n== unpublish E2E Ops Desk: the other studios must stay on the rail")
    publisher.unpublish("E2E Ops Desk")
    frappe.db.commit()
    for user in ("e2e.sales1@example.com", "e2e.manager@example.com"):
        b = _boot_as(user)
        print(f"  {user}: Workspaces rail = {[x[0] for x in b['rails'].get('thinknxg_workspace_studio', []) if not x[2]]}")
    _publish("E2E Ops Desk")
    frappe.db.commit()

    print("\n== check_user e2e.sales1 on E2E Sales Desk")
    for r in diagnostics.check_user("E2E Sales Desk", "e2e.sales1@example.com")["rows"]:
        print(f"  {'OK ' if r['ok'] else 'BAD'} {r['check']}: {r['detail']}")
        if r.get("trace"):
            print("     " + r["trace"][-800:].replace("\n", "\n     "))
