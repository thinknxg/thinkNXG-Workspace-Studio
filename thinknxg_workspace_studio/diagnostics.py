"""'Check a user': replay the v16 boot as one user and report every gate between a published
studio and what that user sees (workspace, module sidebar, Dock rail, home page).

It calls Frappe's own boot functions as that user, so the answer is what the desk computes, and
any exception raised along the way (for example by another app's permission hook) is reported
with its traceback instead of being lost.
"""

import frappe
from frappe.utils import cint

from thinknxg_workspace_studio import schema


def _reset_request_caches():
    cache = getattr(frappe.local, "request_cache", None)
    if cache is not None:
        cache.clear()
    frappe.local.dock_cache = {"app_dock": {}, "mounts": None}


class Report:
    def __init__(self):
        self.rows = []

    def add(self, check, ok, detail="", trace=None):
        self.rows.append({"check": check, "ok": ok, "detail": detail, "trace": trace})
        return ok

    def run(self, check, fn):
        """Run `fn`; it returns (ok, detail). Exceptions become a failed row with traceback."""
        try:
            ok, detail = fn()
            return self.add(check, ok, detail)
        except Exception as e:
            return self.add(check, False, f"{type(e).__name__}: {e}", frappe.get_traceback())


def check_user(studio_name, user):
    studio = frappe.get_doc("Studio Workspace", studio_name)
    index = schema.loads(studio.published_index, [])
    title = (studio.workspace_title or studio.title).strip()
    module = next((e["name"] for e in index if e.get("doctype") == "Module Def"), None) or studio.module
    personal = (studio.publish_mode or "").startswith("Personal")
    workspaces = [e["name"] for e in index if e.get("doctype") == "Workspace"]
    own_copy = f"{title}-{user}"
    expected_ws = own_copy if own_copy in workspaces else (title if title in workspaces else None)
    app = (studio.get("dock_app") or "").strip() or (
        "erpnext" if "erpnext" in frappe.get_installed_apps() else "frappe"
    )
    rep = Report()

    # ---------------------------------------------------------------- as admin: static facts
    u = frappe.db.get_value("User", user, ["enabled", "user_type", "default_workspace"], as_dict=True)
    if not u:
        rep.add("User exists", False, user)
        return {"rows": rep.rows}
    rep.add("User is enabled", bool(u.enabled))
    rep.add("User is a desk (System) user", u.user_type == "System User", u.user_type)
    if studio.status not in ("Published", "Modified"):
        rep.add("Studio is published", False, studio.status)
    rep.add(
        "User has a workspace from this studio",
        bool(expected_ws),
        expected_ws or "Not in the published audience (check roles / users, then publish again)",
    )
    if module:
        placement = frappe.db.get_value("Module Def", module, "app_name")
        rep.add("Studio module is placed in the Dock app", placement == app, f"{module} → app_name = {placement or '(none)'}; Dock app = {app}")
    rep.add(
        "Default workspace",
        not cint(studio.set_as_default) or u.default_workspace == expected_ws,
        f"User.default_workspace = {u.default_workspace or '(empty)'}"
        + ("" if cint(studio.set_as_default) else " — 'Set as default workspace' is off on the studio"),
    )

    # ---------------------------------------------------------------- as the user: the boot
    actor = frappe.session.user
    frappe.set_user(user)
    _reset_request_caches()
    try:
        roles = frappe.get_roles(user)
        rep.add("Roles", True, ", ".join(r for r in roles if r not in ("All", "Guest")))

        def blocked():
            from frappe.utils.modules import get_blocked_modules

            b = get_blocked_modules(user)
            return (module not in b, ("Module is blocked for this user (User → Modules)" if module in b else f"{len(b)} module(s) blocked, not this one"))

        if module:
            rep.run("Module is not blocked", blocked)

        def pages():
            from frappe.desk.desktop import get_workspaces

            names = {p.name for p in get_workspaces()["pages"]}
            return (expected_ws in names, f"{expected_ws} {'is' if expected_ws in names else 'is NOT'} in the user's permitted workspaces")

        if expected_ws:
            rep.run("Workspace is visible to the user", pages)

        sidebars = {}

        def module_sidebar():
            from frappe.boot import get_module_sidebars

            sidebars.update(get_module_sidebars())
            entry = sidebars.get(module)
            if not entry:
                return False, "Module sidebar resolved to nothing for this user, so the Dock drops the pin"
            items = entry.get("items") if isinstance(entry, dict) else getattr(entry, "items", [])
            return True, f"{len(items or [])} item(s); app = {entry.get('app') if isinstance(entry, dict) else ''}"

        if module:
            rep.run("Module sidebar builds for the user", module_sidebar)

        def dock():
            from frappe.desk.doctype.dock.dock import dock_key, resolve_dock

            rails = resolve_dock()
            rail = rails.get(app)
            if rail is None:
                return False, f"No resolved '{app}' rail for this user (apps with rails: {', '.join(rails) or 'none'})"
            key = dock_key({"link_type": "Workspace", "link_to": expected_ws})
            found = next((r for r in rail if dock_key(r) == key), None)
            if not found:
                return False, f"The pin for {expected_ws} is not on the '{app}' rail ({len(rail)} entries)"
            if found.get("hidden"):
                return False, "The pin is on the rail but hidden"
            return True, f"On the '{app}' rail ({len(rail)} entries)"

        if expected_ws and frappe.db.exists("DocType", "Dock"):
            rep.run("Dock pin resolves for the user", dock)

        def apps():
            from frappe.boot import get_app_data

            names = [a.get("app_name") for a in get_app_data()]
            return (app in names, f"Apps the user can open: {', '.join(names)}")

        rep.run("User can open the Dock app", apps)

        def home():
            from frappe.website.utils import get_home_page

            frappe.cache.hdel("home_page", user)
            hp = get_home_page()
            return (not cint(studio.set_as_default) or (expected_ws and expected_ws.lower().replace(" ", "-") in hp.lower()) or "desk" in hp, f"Home page after login: /{hp}")

        rep.run("Login home page", home)
    finally:
        frappe.set_user(actor)
        _reset_request_caches()

    return {"rows": rep.rows, "workspace": expected_ws, "module": module, "app": app, "mode": "Personal" if personal else "Shared"}
