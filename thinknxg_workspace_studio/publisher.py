"""Publishes Studio Workspace designs into real thinkNXG documents and rolls them back.

v16 navigation (thinkNXG version-16, autumn 2026) is built from modules:

  * Workspace        - the page, filed under the studio's own custom module
  * Module Def       - one custom module per studio (unless the studio names one). Its sidebar is
                       what the desk shows next to the workspace, and a dock entry opens it.
  * Custom Sidebar   - the studio's menu, as the site layer (Shared) or per-user layers (Personal)
  * Dock             - native per-app dock, site layer (no audience) or per-user layers (audience),
                       merged into the existing rail unless "Replace" is chosen
  * User.default_workspace

Older v16 builds without `Custom Sidebar`/`Dock` fall back to `Workspace Sidebar` and
`Desktop Icon`. Dock items the native Dock cannot hold are served by the Studio Quick Launch bar
(`published_dock_json`). All writes are snapshotted so a publish can be rolled back.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from thinknxg_workspace_studio import schema

WS_TABLES = ("shortcuts", "links", "charts", "number_cards", "quick_lists", "custom_blocks")
QUERY_REPORT_TYPES = ("Query Report", "Script Report", "Custom Report")
STRIP_KEYS = ("creation", "modified", "modified_by", "owner", "docstatus", "idx", "_user_tags",
              "_comments", "_assign", "_liked_by", "_seen")
CHILD_STRIP_KEYS = STRIP_KEYS + ("name", "parent", "parentfield", "parenttype")
# Documents this studio owns outright and may delete when they drop out of the audience.
MANAGED_DOCTYPES = ("Workspace", "Workspace Sidebar", "Desktop Icon", "Custom Sidebar")
# Everything recorded in the published index (Module Def is kept, Dock rows are removed by key).
INDEXED_DOCTYPES = MANAGED_DOCTYPES + ("Module Def", "Dock")
PRIVATE_MODULE = "Private"
CUSTOM_MODULE = "Custom Workspaces"
DEFAULT_DOCK_ICON = "data-table-soft"
# v16 module icons that ship in the desk sprite. A studio with no icon gets one of these, picked
# from its name, so several studios on one rail are told apart at a glance.
FRAPPE_DOCK_ICONS = (
    "automation-cycle-soft", "code-app-soft", "contacts-cards-soft", "email-envelope-soft",
    "geo-pin-soft", "integrations-cable-soft", "printing-printer-soft", "system-monitor-soft",
    "users-soft", "website-browser-soft", "workflow-builder-soft",
)
ERPNEXT_DOCK_ICONS = (
    "asset-hand-soft", "calculator-soft", "factory-soft", "gantt-chart-soft", "handshake-soft",
    "headset-soft", "portal-user-soft", "quality-seal-soft", "shelf-rack-soft",
    "shopping-cart-soft", "sliders-soft", "storefront-soft",
)
# Workspace Studio is itself a v16 Dock app ("Workspaces"), usable instead of thinkNXG ERP's rail.
STUDIO_APP = "thinknxg_workspace_studio"
STUDIO_APP_TITLE = "Workspaces"


def studio_setting(field, default):
    """Single-value setting that may not exist yet (before migrate)."""
    try:
        value = frappe.db.get_single_value("Workspace Studio Settings", field)
    except Exception:
        return default
    return default if value is None else value
MAX_LAYER_USERS = 500


def is_shared_app_icon(doctype, name):
    """The Workspaces app's desktop icon is shared by every studio; no studio may delete it."""
    return doctype == "Desktop Icon" and frappe.db.get_value(
        "Desktop Icon", name, ["icon_type", "app"], as_dict=True
    ) == {"icon_type": "App", "app": STUDIO_APP}


def keys_claimed_by_others(studio, dock_name):
    """Dock keys other studios still have on the same layer (e.g. a shared URL)."""
    out = set()
    for other in frappe.get_all(
        "Studio Workspace",
        filters={"name": ["!=", studio], "status": ["in", ["Published", "Modified"]]},
        fields=["published_index"],
    ):
        for e in schema.loads(other.published_index, []):
            if e.get("doctype") == "Dock" and e.get("name") == dock_name:
                out.update(e.get("keys") or [])
    return out


def retire_dock_layer(name, keys, created):
    """Take one studio's entries out of a Dock layer.

    Other studios may share the layer, so only this studio's entries are removed. A layer the
    studio created is deleted outright when what is left is just the native rail it was seeded
    from, which gives the user the live native Dock back instead of a frozen copy.
    Returns ('removed' | 'entries removed' | None, snapshot-before).
    """
    from frappe.desk.doctype.dock import dock as D

    if not frappe.db.exists("Dock", name):
        return None, None
    doc = frappe.get_doc("Dock", name)
    before = _jsonable(doc)
    keys = set(keys or [])
    remaining = [r for r in (doc.get("items") or []) if D.dock_key(r) not in keys]
    if created:
        native = {D.dock_key(e) for e in D.resolve_app_dock(doc.app, upto="site" if doc.user else "app", gated=False)}
        if all(D.dock_key(r) in native for r in remaining):
            frappe.delete_doc("Dock", name, ignore_permissions=True, force=True)
            return "removed", before
    doc.set("items", remaining)
    doc.save(ignore_permissions=True)
    return "entries removed", before


def native_navigation():
    """True on v16 builds that navigate by module sidebars and the layered Dock."""
    return bool(frappe.db.exists("DocType", "Custom Sidebar") and frappe.db.exists("DocType", "Dock"))


def slug(text):
    return (text or "").strip().lower().replace(" ", "-")


def _jsonable(doc):
    return json.loads(frappe.as_json(doc.as_dict(no_default_fields=False)))


def pick_option(df, candidates):
    """Return the first candidate that is a valid option of a Select field."""
    if not df:
        return None
    if df.fieldtype != "Select":
        return candidates[0] if candidates else None
    options = [o.strip() for o in (df.options or "").split("\n") if o.strip()]
    lowered = {o.lower(): o for o in options}
    for c in candidates:
        if c and c.lower() in lowered:
            return lowered[c.lower()]
    return None


class Publisher:
    def __init__(self, studio):
        self.doc = studio
        self.layout = schema.normalize_layout(schema.loads(studio.layout_json, {}))
        self.sidebar = schema.normalize_sidebar(schema.loads(studio.sidebar_json, {}))
        self.dock = schema.normalize_dock(schema.loads(studio.dock_json, {}))
        self.snapshots = []
        self.documents = []
        self.warnings = []
        self.prev_index = schema.loads(studio.published_index, [])
        self.owned = {(d.get("doctype"), d.get("name")) for d in self.prev_index}
        self.title = (studio.workspace_title or studio.title).strip()
        self.native = native_navigation()
        self._module = None
        
    # ------------------------------------------------------------------ helpers
    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)

    def snapshot(self, doctype, name):
        if frappe.db.exists(doctype, name):
            before = _jsonable(frappe.get_doc(doctype, name))
        else:
            before = None
        self.snapshots.append({"doctype": doctype, "name": name, "before": before})

    def record(self, doctype, name, action, route=None, **extra):
        self.documents.append({"doctype": doctype, "name": name, "action": action, "route": route, **extra})

    def guard_ownership(self, doctype, name):
        if not frappe.db.exists(doctype, name):
            return
        if (doctype, name) in self.owned or cint(self.doc.take_over_existing):
            return
        frappe.throw(
            _(
                "{0} '{1}' already exists and is not managed by this studio. Change the Workspace Label, "
                "or tick 'Allow replacing an existing workspace with the same label'."
            ).format(_(doctype), name)
        )

    def filter_values(self, doctype, values, context):
        meta = frappe.get_meta(doctype)
        out = {}
        for key, value in values.items():
            df = meta.get_field(key)
            if not df:
                continue
            if df.fieldtype == "Select" and value not in (None, ""):
                picked = pick_option(df, [value])
                if picked is None:
                    self.warn(f"{context}: '{value}' is not a valid {df.label or key} here, left blank.")
                    continue
                value = picked
            out[key] = value
        return out

    # ------------------------------------------------------------------ module
    def module_for(self, public, for_user):
        """Module a published workspace is filed under."""
        if self.native:
            return self.ensure_module()
        # pre-sidebar-layer builds: thinkNXG's own triage
        if not public:
            target = PRIVATE_MODULE
        elif self.doc.module and self.doc.module != PRIVATE_MODULE:
            return self.doc.module
        else:
            target = CUSTOM_MODULE
        try:
            from frappe.desk.doctype.workspace.workspace import triage_module

            return triage_module(None if public else for_user)
        except ImportError:
            pass
        if not frappe.db.exists("Module Def", target):
            frappe.get_doc({"doctype": "Module Def", "module_name": target, "custom": 1}).insert(
                ignore_permissions=True
            )
        return target

    def ensure_module(self):
        """The module that carries this studio's workspace, sidebar and dock entry.

        A module the studio names is used as it is. Otherwise the studio gets its own custom
        module named after the workspace label, placed in the Dock app (`app_name`). v16 draws
        the rail of the app that owns the sidebar on screen, so an unplaced module shows no Dock
        at all on its own workspace. Placing it does not list it for everyone: once a Dock layer
        is saved, only the entries that layer names are shown.
        """
        if self._module:
            return self._module
        chosen = (self.doc.module or "").strip()
        if chosen and chosen != PRIVATE_MODULE:
            self._module = chosen
            return chosen

        for candidate in (self.title, f"{self.title} Workspace", f"{self.title} Studio"):
            existing = frappe.db.get_value("Module Def", candidate, "name")
            if existing:
                if ("Module Def", existing) in self.owned or self.can_adopt_module(existing):
                    self._module = existing
                    self.place_module(existing)
                    self.record("Module Def", existing, "kept")
                    break
                continue
            if frappe.db.exists("DocType", "Sidebar") and frappe.db.exists("Sidebar", candidate):
                continue
            module = frappe.get_doc(
                {"doctype": "Module Def", "module_name": candidate, "custom": 1, "app_name": self.dock_app()}
            )
            # The studio supplies the page the module opens on, so skip v16's auto-created one.
            previous = frappe.flags.in_import
            frappe.flags.in_import = True
            try:
                module.insert(ignore_permissions=True)
            finally:
                frappe.flags.in_import = previous
            self.snapshots.append({"doctype": "Module Def", "name": module.name, "before": None})
            self.record("Module Def", module.name, "created")
            self._module = module.name
            break
        else:
            frappe.throw(
                _("Could not find a free module name for {0}. Set a Module on the studio.").format(self.title)
            )
        if self._module != self.title:
            self.warn(
                f"A module called '{self.title}' already exists and belongs to something else, "
                f"so this studio uses its own module '{self._module}'."
            )
        return self._module

    def can_adopt_module(self, module):
        """A custom module left behind by this studio (e.g. after delete/recreate or unpublish):
        exact name, custom, not claimed by another studio, and holding nothing but workspaces."""
        info = frappe.db.get_value("Module Def", module, ["name", "custom"], as_dict=True)
        if not info or info.name != module or not cint(info.custom):
            return False
        for other in frappe.get_all("Studio Workspace", filters={"name": ["!=", self.doc.name]}, fields=["published_index"]):
            if any(e.get("doctype") == "Module Def" and e.get("name") == module for e in schema.loads(other.published_index, [])):
                return False
        if frappe.db.exists("DocType", {"module": module}) or frappe.db.exists("Report", {"module": module}):
            return False
        return True

    def place_module(self, module):
        """Keep the studio's own module placed in the current Dock app."""
        app = self.dock_app()
        if frappe.db.get_value("Module Def", module, "app_name") == app:
            return
        self.snapshot("Module Def", module)
        frappe.db.set_value("Module Def", module, "app_name", app)
        frappe.clear_cache()

    @property
    def page_title(self):
        """Title (and URL) of the published workspace pages.

        v16 refuses a workspace whose title gives the same /desk URL as a DocType, Page or another
        Workspace (`validate_route_conflict`, which raises a NameError with no message). A label
        such as 'Estimation' clashes with an Estimation DocType, so the page gets the first free
        title of '<Label>', '<Label> Workspace', '<Label> Desk', '<Label> Home'. The Dock entry
        and sidebar header keep showing the label.
        """
        if getattr(self, "_page_title", None):
            return self._page_title
        from frappe.desk.utils import slug as route_slug

        taken = {}
        for dt in ("DocType", "Page"):
            for n in frappe.get_all(dt, pluck="name"):
                taken.setdefault(route_slug(n), f"{_(dt)} '{n}'")
        for n in frappe.get_all("Workspace", pluck="name"):
            if ("Workspace", n) in self.owned:
                continue
            taken.setdefault(route_slug(n), f"{_('Workspace')} '{n}'")
        candidates = [self.title] + [f"{self.title} {s}" for s in ("Workspace", "Desk", "Home")]
        candidates += [f"{self.title} {i}" for i in range(2, 50)]
        pick = next((c for c in candidates if route_slug(c) not in taken), None)
        if not pick:
            frappe.throw(_("Could not find a free page title for {0}. Change the Workspace Label.").format(self.title))
        if pick != self.title:
            self.warn(
                f"The label '{self.title}' would share the URL /desk/{route_slug(self.title)} with the "
                f"{taken[route_slug(self.title)]}, which v16 does not allow, so the page is published as "
                f"'{pick}' (/desk/{route_slug(pick)}). The Dock and sidebar still show '{self.title}'. "
                "Change the Workspace Label to choose another name."
            )
        self._page_title = pick
        return pick

    # ------------------------------------------------------------------ audience
    def target_roles(self):
        return [t.role for t in self.doc.targets if t.target_type == "Role" and t.role]

    def target_users(self):
        return [t.user for t in self.doc.targets if t.target_type == "User" and t.user]

    def users_for_roles(self, roles):
        """Enabled desk users holding any of `roles`.

        v16 never stores its automatic roles on a user: "Desk User" and "All" mean every desk
        user, "Administrator" means the Administrator account. Administrator is otherwise
        included only when the role is explicitly assigned to it.
        """
        if not roles:
            return []
        everyone = {"Desk User", "All"} & set(roles)
        stored = [r for r in roles if r not in ("Desk User", "All", "Guest", "Administrator")]
        filters = {"enabled": 1, "user_type": "System User"}
        if everyone:
            users = frappe.get_all("User", filters=filters, pluck="name")
        else:
            parents = (
                frappe.get_all(
                    "Has Role", filters={"role": ["in", stored], "parenttype": "User"}, pluck="parent", distinct=True
                )
                if stored
                else []
            )
            users = frappe.get_all("User", filters={**filters, "name": ["in", parents]}, pluck="name") if parents else []
        if "Administrator" in roles and "Administrator" not in users:
            users.append("Administrator")
        users = [u for u in users if u != "Guest"]
        if not users:
            self.warn(
                "No enabled desk user holds the audience role(s): " + ", ".join(roles)
                + ". Assign the role to at least one user, or add users individually."
            )
        return users

    def resolve_users(self):
        users = self.users_for_roles(self.target_roles())
        for u in self.target_users():
            if u not in users and frappe.db.get_value("User", u, "enabled"):
                users.append(u)
        return users

    # ------------------------------------------------------------------ workspace
    def find_workspace(self, label, for_user):
        if frappe.db.exists("Workspace", label):
            return label
        return frappe.db.get_value("Workspace", {"label": label, "for_user": for_user or ""}, "name")

    def upsert_workspace(self, label, public, for_user, roles, payload):
        existing = self.find_workspace(label, for_user)
        if existing:
            self.guard_ownership("Workspace", existing)
            self.snapshot("Workspace", existing)
            ws = frappe.get_doc("Workspace", existing)
            action = "updated"
        else:
            self.snapshots.append({"doctype": "Workspace", "name": label, "before": None})
            ws = frappe.new_doc("Workspace")
            action = "created"

        meta = frappe.get_meta("Workspace")
        values = {
            "label": label,
            "title": self.page_title,
            "public": 1 if public else 0,
            "for_user": for_user or "",
            "icon": self.doc.icon or None,
            "indicator_color": self.doc.indicator_color or None,
            "parent_page": (self.doc.parent_page or "") if public else "",
            "module": self.module_for(public, for_user),
            "type": "Workspace",
            "standard": 0,
            "sequence_id": self.doc.sequence_id or 0,
            "is_hidden": 0,
            "content": json.dumps(payload["content"]),
        }
        for key, value in self.filter_values("Workspace", values, "Workspace").items():
            ws.set(key, value)

        for table in WS_TABLES + ("roles",):
            if meta.has_field(table):
                ws.set(table, [])
        for table in WS_TABLES:
            df = meta.get_field(table)
            if not df:
                if payload[table]:
                    self.warn(f"Workspace has no '{table}' table on this version; those blocks were skipped.")
                continue
            for row in payload[table]:
                ws.append(table, self.filter_values(df.options, row, f"Workspace {table}"))
        if meta.has_field("roles"):
            for role in roles:
                ws.append("roles", {"role": role})

        self.enrich_report_links(ws)

        if existing:
            ws.save(ignore_permissions=True)
        else:
            ws.insert(ignore_permissions=True)

        self.record("Workspace", ws.name, action, ("/desk/" + slug(self.page_title)) if public else None)
        return ws.name

    def enrich_report_links(self, ws):
        for row in ws.get("links") or []:
            if row.get("link_type") == "Report" and row.get("link_to"):
                info = frappe.db.get_value("Report", row.link_to, ["report_type", "ref_doctype"], as_dict=True)
                if not info:
                    self.warn(f"Report '{row.link_to}' was not found.")
                    continue
                row.is_query_report = 1 if info.report_type in QUERY_REPORT_TYPES else 0
                if row.meta.has_field("report_ref_doctype"):
                    row.report_ref_doctype = info.ref_doctype

    # ------------------------------------------------------------------ sidebar
    def publish_legacy_sidebar(self, name):
        if not frappe.db.exists("DocType", "Workspace Sidebar"):
            self.warn("This site has no 'Workspace Sidebar' DocType (pre-v16), so the left menu was not published.")
            return
        rows = schema.flatten_sidebar(self.sidebar)
        if not rows:
            self.warn("The sidebar is empty, so it was not published.")
            return

        meta = frappe.get_meta("Workspace Sidebar")
        table_df = meta.get_field("items") or next((d for d in meta.fields if d.fieldtype == "Table"), None)
        if not table_df:
            self.warn("Workspace Sidebar has no item table on this version; sidebar skipped.")
            return
        child_meta = frappe.get_meta(table_df.options)
        type_df = child_meta.get_field("type")
        lt_df = child_meta.get_field("link_type")

        mapped = []
        for r in rows:
            candidates = {
                "section": ["Section Break", "Section", "Card Break"],
                "link": ["Link"],
                "spacer": ["Spacer", "Divider", "Separator"],
            }[r["kind"]]
            rtype = pick_option(type_df, candidates) if type_df else None
            if type_df and rtype is None:
                self.warn(f"Sidebar item type '{r['kind']}' is not supported here; '{r.get('label')}' skipped.")
                continue
            row = {
                "type": rtype,
                "label": r.get("label") or "",
                "icon": r.get("icon") or None,
                "child": r.get("child", 0),
                "indent": r.get("indent", 0),
                "collapsible": r.get("collapsible", 0),
                "keep_closed": r.get("keep_closed", 0),
            }
            if r["kind"] == "link":
                link_type = r["link_type"]
                if link_type == "URL":
                    picked = pick_option(lt_df, ["URL", "External Link", "Link"]) if lt_df else "URL"
                    row.update({"link_type": picked, "url": r["url"], "link_to": None})
                    if not child_meta.has_field("url"):
                        self.warn(f"Sidebar link '{r['label']}' points to a URL, which this version cannot store.")
                        continue
                else:
                    picked = pick_option(lt_df, [link_type]) if lt_df else link_type
                    if lt_df and picked is None:
                        self.warn(f"Sidebar link type '{link_type}' is not available; '{r['label']}' skipped.")
                        continue
                    row.update({"link_type": picked, "link_to": r["link_to"]})
            mapped.append({k: v for k, v in row.items() if child_meta.has_field(k)})

        existing = frappe.db.exists("Workspace Sidebar", name)
        if existing:
            self.guard_ownership("Workspace Sidebar", name)
            self.snapshot("Workspace Sidebar", name)
            sb = frappe.get_doc("Workspace Sidebar", name)
            action = "updated"
        else:
            self.snapshots.append({"doctype": "Workspace Sidebar", "name": name, "before": None})
            sb = frappe.new_doc("Workspace Sidebar")
            action = "created"
        header = {
            "title": name,
            "label": name,
            "header_icon": self.doc.icon or None,
            "icon": self.doc.icon or None,
            "module": self.module_for(True, None),
        }
        sb.update(self.filter_values("Workspace Sidebar", header, "Workspace Sidebar"))
        sb.set(table_df.fieldname, [])
        for row in mapped:
            sb.append(table_df.fieldname, row)
        try:
            if existing:
                sb.save(ignore_permissions=True)
            else:
                sb.insert(ignore_permissions=True, set_name=name)
            self.record("Workspace Sidebar", sb.name, action)
        except Exception as e:  # schema differences must not block the workspace itself
            frappe.log_error(title="Workspace Studio: sidebar publish failed")
            self.snapshots.pop()
            self.warn(f"Sidebar could not be saved on this version: {e}")

    # ------------------------------------------------------------------ desktop icon
    def publish_desktop_icon(self, name, sidebar_published):
        if not frappe.db.exists("DocType", "Desktop Icon"):
            self.warn("This site has no 'Desktop Icon' DocType, so no desktop icon was created.")
            return
        meta = frappe.get_meta("Desktop Icon")
        lt_df = meta.get_field("link_type")
        prefs = ["Workspace Sidebar", "Workspace", "External", "Link"] if sidebar_published else ["Workspace", "External", "Link"]
        link_type = pick_option(lt_df, prefs) if lt_df else None
        values = {
            "label": name,
            "icon": self.doc.icon or None,
            "icon_type": "Link",
            "hidden": 0,
            "standard": 0,
            "link_type": link_type,
            "link_to": name if link_type in ("Workspace Sidebar", "Workspace") else None,
            "sidebar": name if link_type == "Workspace Sidebar" else None,
            "link": "/desk/" + slug(self.title),
            "idx": cint(self.doc.sequence_id),
        }
        existing = frappe.db.exists("Desktop Icon", name)
        if existing:
            self.guard_ownership("Desktop Icon", name)
            self.snapshot("Desktop Icon", name)
            icon = frappe.get_doc("Desktop Icon", name)
            action = "updated"
        else:
            self.snapshots.append({"doctype": "Desktop Icon", "name": name, "before": None})
            icon = frappe.new_doc("Desktop Icon")
            action = "created"
        icon.update(self.filter_values("Desktop Icon", values, "Desktop Icon"))
        if icon.meta.has_field("roles"):
            icon.set("roles", [{"role": r} for r in self.target_roles()])
        try:
            if existing:
                icon.save(ignore_permissions=True)
            else:
                icon.insert(ignore_permissions=True, set_name=name)
            self.record("Desktop Icon", icon.name, action)
        except Exception as e:
            frappe.log_error(title="Workspace Studio: desktop icon publish failed")
            self.snapshots.pop()
            self.warn(f"Desktop icon could not be saved on this version: {e}")

    # ------------------------------------------------------------------ defaults
    def set_default_workspace(self, mapping):
        if not frappe.get_meta("User").has_field("default_workspace"):
            self.warn("User has no 'default_workspace' field on this version; default not set.")
            return
        mapping = self.default_owner_filter(mapping)
        for user, ws_name in mapping.items():
            old = frappe.db.get_value("User", user, "default_workspace")
            if old == ws_name:
                continue
            self.snapshots.append(
                {"doctype": "User", "name": user, "field": "default_workspace", "before": old}
            )
            frappe.db.set_value("User", user, "default_workspace", ws_name, update_modified=False)
            frappe.clear_cache(user=user)
        if mapping:
            self.record("User", f"{len(mapping)} user(s)", "default workspace set")

    def default_owner_filter(self, mapping):
        """Keep only users for whom this studio should own the default workspace: this studio is
        their highest-priority published studio with 'Set as default' on, and they are not an
        Administrator/System Manager reached through a role (setting)."""
        explicit = set(self.target_users())
        exclude = cint(studio_setting("exclude_managers_from_dock", 1))
        mine = cint(self.doc.get("priority"))
        rivals = [
            s for s in frappe.get_all(
                "Studio Workspace",
                filters={"name": ["!=", self.doc.name], "status": ["in", ["Published", "Modified"]], "set_as_default": 1},
                fields=["name", "priority", "published_index"],
            )
        ]
        kept, managers, lost = {}, 0, {}
        for user, ws in mapping.items():
            if exclude and user not in explicit and (user == "Administrator" or "System Manager" in frappe.get_roles(user)):
                managers += 1
                continue
            winner = None
            for r in rivals:
                rank = (cint(r.priority), r.name < self.doc.name)
                if rank <= (mine, False):
                    continue
                ws_names = {e.get("name") for e in schema.loads(r.published_index, []) if e.get("doctype") == "Workspace"}
                if frappe.db.get_value("User", user, "default_workspace") in ws_names:
                    winner = r.name
                    break
            if winner:
                lost[user] = winner
                continue
            kept[user] = ws
        if managers:
            self.warn(f"The default workspace of {managers} Administrator/System Manager account(s) was left unchanged.")
        if lost:
            self.warn(
                f"{len(lost)} user(s) keep the default workspace of a higher-priority studio ("
                + ", ".join(sorted(set(lost.values()))) + "). Raise this studio's Priority to take over."
            )
        return kept

    # ------------------------------------------------------------------ native sidebar (v16)
    def sidebar_rows(self, user_roles, home):
        """Custom Sidebar rows for one layer. The studio's workspace always comes first, so the
        module opens on it."""
        rows = []
        if home:
            rows.append(
                {"type": "Link", "label": self.title, "link_type": "Workspace", "link_to": home,
                 "icon": self.doc.icon or None, "child": 0, "added": 1, "open_in_new_tab": 0}
            )
        for r in schema.flatten_sidebar(self.sidebar, user_roles):
            row = {"added": 1, "child": r.get("child", 0), "label": r.get("label") or "",
                   "icon": r.get("icon") or None, "open_in_new_tab": 0}
            if r["kind"] == "section":
                row.update({"type": "Section Break", "collapsible": r.get("collapsible", 1),
                            "keep_closed": r.get("keep_closed", 0), "key": "wss-" + r["id"]})
            elif r["kind"] == "spacer":
                row.update({"type": "Spacer", "key": "wss-" + r["id"]})
            else:
                if r["link_type"] == "URL":
                    row.update({"type": "Link", "link_type": "URL", "url": r["url"], "link_to": None})
                else:
                    row.update({"type": "Link", "link_type": r["link_type"], "link_to": r["link_to"]})
                if home and row.get("link_type") == "Workspace" and row.get("link_to") == home:
                    continue
            rows.append(row)
        return rows

    def publish_native_sidebar(self, layers):
        """`layers` is a list of (user or None, home workspace name)."""
        from frappe.desk.doctype.custom_sidebar.custom_sidebar import _save_customization, get_customization

        module = self.ensure_module()
        if not self.sidebar["items"]:
            self.warn("The sidebar menu is empty; the module shows only the workspace itself.")
        if any(user is None for user, _home in layers) and _sidebar_has_roles(self.sidebar):
            self.warn("Sidebar items limited to roles are shown to everyone in Shared mode (each link is still permission-checked).")
        for user, home in layers:
            rows = self.sidebar_rows(frappe.get_roles(user) if user else None, home)
            existing = get_customization(module, user)
            if existing:
                self.snapshot("Custom Sidebar", existing.name)
            _save_customization(module, rows, user=user, label=self.title, header_icon=self.doc.icon or None)
            layer = get_customization(module, user)
            if not layer:
                self.warn(f"The sidebar layer for {user or 'the site'} could not be saved.")
                continue
            if not existing:
                self.snapshots.append({"doctype": "Custom Sidebar", "name": layer.name, "before": None})
            self.record("Custom Sidebar", layer.name, "updated" if existing else "created",
                        layer=user or "site")

    # ------------------------------------------------------------------ native dock (v16)
    def dock_app(self):
        if getattr(self, "_dock_app", None):
            return self._dock_app
        self._dock_app = self._resolve_dock_app()
        return self._dock_app

    def _resolve_dock_app(self):
        installed = frappe.get_installed_apps()
        app = (self.doc.get("dock_app") or "").strip()
        if app and app in installed:
            return app
        if app:
            self.warn(f"Dock app '{app}' is not installed; using the default rail ({schema.app_label('erpnext') if 'erpnext' in installed else schema.app_label('frappe')}) instead.")
        return "erpnext" if "erpnext" in installed else "frappe"

    def ensure_studio_icon(self):
        """Give a studio without an icon a distinct v16 module icon, stored on the studio so it
        never changes and is visible (and editable) in the designer. Icons other studios hold
        are skipped, so several studios on one rail look different."""
        if self.doc.icon:
            return self.doc.icon
        import hashlib

        palette = FRAPPE_DOCK_ICONS + (ERPNEXT_DOCK_ICONS if "erpnext" in frappe.get_installed_apps() else ())
        used = set(
            frappe.get_all("Studio Workspace", filters={"name": ["!=", self.doc.name], "icon": ["is", "set"]}, pluck="icon")
        )
        start = int(hashlib.md5(self.doc.name.encode()).hexdigest(), 16) % len(palette)
        pick = next((palette[(start + i) % len(palette)] for i in range(len(palette)) if palette[(start + i) % len(palette)] not in used), palette[start])
        self.doc.db_set("icon", pick, update_modified=False)
        self.doc.icon = pick
        return pick

    def studio_dock_icon(self):
        return self.doc.icon or self.ensure_studio_icon()

    def native_dock_entries(self, user_roles, home):
        """Dock entries for one layer. The first pins the layer's own workspace: the shared one
        on the site layer, the user's personal copy on a user layer. v16 derives the sidebar
        from the workspace's module, so it opens with the studio's menu beside it."""
        entries = [{"link_type": "Workspace", "link_to": home, "title": self.title,
                    "icon": self.studio_dock_icon(), "hidden": 0}]
        for it in self.dock["items"]:
            if not schema.is_native_dock_item(it) or not schema.visible_for(it["roles"], user_roles):
                continue
            entry = {"link_type": it["link_type"], "title": it["label"],
                     "icon": it["icon"] or DEFAULT_DOCK_ICON, "hidden": 0}
            if it["link_type"] == "URL":
                if not it["url"]:
                    continue
                entry["url"] = it["url"]
            else:
                if not it["link_to"]:
                    continue
                entry["link_to"] = it["link_to"]
            entries.append(entry)
        return entries

    def dock_layers(self, shared_name, default_map):
        """Which Dock layers to write: the site layer when there is no audience, otherwise one
        user layer per audience member pinned to that member's workspace (shared or personal).
        Administrator and System Managers that reach the audience only through a role are left
        alone unless the setting says otherwise, so their native rail never changes."""
        if not (self.target_roles() or self.target_users()):
            return [(None, shared_name)] if shared_name else []
        explicit = set(self.target_users())
        exclude = cint(studio_setting("exclude_managers_from_dock", 1))
        layers, skipped = [], []
        for user, workspace in default_map.items():
            if exclude and user not in explicit and (
                user == "Administrator" or "System Manager" in frappe.get_roles(user)
            ):
                skipped.append(user)
                continue
            layers.append((user, workspace))
        if skipped:
            self.warn(
                f"The Dock of {len(skipped)} Administrator/System Manager account(s) was left unchanged. "
                "Add them as individual users to include them."
            )
        if len(layers) > MAX_LAYER_USERS:
            self.warn(f"The audience has {len(layers)} users; the Dock is only written for the first {MAX_LAYER_USERS}.")
            layers = layers[:MAX_LAYER_USERS]
        return layers

    def publish_native_dock(self, layers):
        """`layers` is [(user or None, workspace)].

        * Merge (default): the rail keeps every entry it had. On another app's rail (thinkNXG ERP)
          the studio's entries go *after* the native ones, because an app's tile and desktop icon
          open the first entry of its rail. On the Workspaces app they go first.
        * Replace: the user's rail holds only the studio's entries. Never applied to another
          app's site-wide rail, so users outside the audience keep their native Dock.
        * A layer the studio created is deleted when its user leaves the audience, so the user
          gets the native rail back exactly.
        """
        from frappe.desk.doctype.dock import dock as D

        app = self.dock_app()
        own_app = app == STUDIO_APP
        replace = (self.doc.get("dock_mode") or "").startswith("Replace")
        previous_keys, previous_created = set(), set()
        for e in self.prev_index:
            if e.get("doctype") == "Dock":
                previous_keys.update(e.get("keys") or [])
                if e.get("created"):
                    previous_created.add(e["name"])
        if not layers:
            return
        if any(u is None for u, _w in layers) and _dock_has_roles(self.dock):
            self.warn("Extra Dock items limited to roles are shown to everyone on the site-wide Dock (the workspace pin itself follows the workspace's roles).")
        user_layers = [u for u, _w in layers if u]
        if user_layers and not replace:
            self.warn(
                f"The Dock was written to {len(user_layers)} user layer(s) on the {schema.app_label(app)} rail. Those users keep "
                "their current entries, but later site-wide Dock changes will not reach them until they leave the audience."
            )
        for user, home in layers:
            replace_this = replace
            if replace and user is None and not own_app:
                replace_this = False
                self.warn(
                    f"Replace mode never rewrites the site-wide {schema.app_label(app)} rail (everyone would lose it). "
                    "Set an audience to replace the rail for those users only; the entries were merged instead."
                )
            ours = self.native_dock_entries(frappe.get_roles(user) if user else None, home)
            keys = {D.dock_key(e) for e in ours}
            existing = D.get_dock(app, user=user)
            if existing:
                self.snapshot("Dock", existing.name)
            if replace_this:
                rows = ours
                if own_app:
                    # keep the designer's own entry so managers can still reach the Studio
                    below = D.resolve_app_dock(app, upto="site", gated=False)
                    rows = ours + [r for r in below if r.get("link_type") == "Sidebar" and r.get("link_to") == "Workspace Studio"]
            else:
                current = D.get_user_dock(app, user) if user else []
                if not current:
                    current = D.resolve_app_dock(app, upto="site", gated=False)
                stale = keys | previous_keys
                rest = [r for r in current if D.dock_key(r) not in stale]
                rows = ours + rest if own_app else rest + ours
            rows = self.order_studio_pins(rows, keys, D)
            rows = [{k: r.get(k) for k in ("link_type", "link_to", "url", "icon", "title", "hidden")} for r in rows]
            D._save_layer(app, rows, user=user, require_visible=False)
            layer = D.get_dock(app, user=user)
            if not layer:
                self.warn(f"The Dock layer for {user or 'the site'} could not be saved.")
                continue
            created = not existing or layer.name in previous_created
            if not existing:
                self.snapshots.append({"doctype": "Dock", "name": layer.name, "before": None})
            self.record("Dock", layer.name, "updated" if existing else "created",
                        layer=f"{schema.app_label(app)} / {user or 'site'}", keys=sorted(keys), created=1 if created else 0)

    def studio_pin_priorities(self, D):
        """dock_key -> (priority, studio) for every studio's workspace pin, this one included."""
        if getattr(self, "_pin_priorities", None) is not None:
            return self._pin_priorities
        out = {}
        for s in frappe.get_all(
            "Studio Workspace", filters={"status": ["in", ["Published", "Modified"]]},
            fields=["name", "priority", "published_index"],
        ):
            if s.name == self.doc.name:
                continue
            for e in schema.loads(s.published_index, []):
                if e.get("doctype") == "Workspace":
                    out[D.dock_key({"link_type": "Workspace", "link_to": e.get("name")})] = (cint(s.priority), s.name)
        self._pin_priorities = out
        return out

    def order_studio_pins(self, rows, my_keys, D):
        """Studio workspace pins sit together, highest priority first (ties by name), wherever
        the studio block is on the rail. Other entries keep their order. The app tile opens the
        first entry, so on the Workspaces app that is the user's highest-priority studio."""
        prio = dict(self.studio_pin_priorities(D))
        mine = (cint(self.doc.get("priority")), self.doc.name)
        for r in rows:
            k = D.dock_key(r)
            if k in my_keys and r.get("link_type") == "Workspace":
                prio[k] = mine
        pins = [r for r in rows if D.dock_key(r) in prio]
        if len(pins) < 2:
            return rows
        ordered = iter(sorted(pins, key=lambda r: (-prio[D.dock_key(r)][0], prio[D.dock_key(r)][1])))
        return [next(ordered) if D.dock_key(r) in prio else r for r in rows]

    def ensure_app_desktop_icon(self):
        """Desktop icon (v16 Desktop Icon grid) for the Workspaces app. The Apps screen tile comes
        from the app hook and needs nothing stored."""
        if not frappe.db.exists("DocType", "Desktop Icon"):
            return
        name = frappe.db.get_value("Desktop Icon", {"icon_type": "App", "app": STUDIO_APP}, "name")
        if name:
            if cint(frappe.db.get_value("Desktop Icon", name, "hidden")):
                self.snapshot("Desktop Icon", name)
                frappe.db.set_value("Desktop Icon", name, "hidden", 0)
                self.record("Desktop Icon", name, "shown")
            else:
                self.record("Desktop Icon", name, "kept")
            if frappe.db.get_value("Desktop Icon", name, "link") != "/desk/wss-home":
                frappe.db.set_value("Desktop Icon", name, {"link_type": "External", "link": "/desk/wss-home"})
            return
        label = STUDIO_APP_TITLE if not frappe.db.exists("Desktop Icon", STUDIO_APP_TITLE) else f"thinkNXG {STUDIO_APP_TITLE}"
        icon = frappe.new_doc("Desktop Icon")
        icon.update(self.filter_values("Desktop Icon", {
            "label": label, "icon_type": "App", "app": STUDIO_APP, "link_type": "External",
            "link": "/desk/wss-home", "logo_url": "/assets/thinknxg_workspace_studio/images/logo.svg",
            "hidden": 0, "standard": 0,
        }, "Desktop Icon"))
        icon.insert(ignore_permissions=True)
        self.snapshots.append({"doctype": "Desktop Icon", "name": icon.name, "before": None})
        self.record("Desktop Icon", icon.name, "created")

    def remove_dock_layer(self, entry):
        """Undo this studio's Dock entries for a user who left the audience."""
        keys = set(entry.get("keys") or []) - keys_claimed_by_others(self.doc.name, entry.get("name"))
        action, before = retire_dock_layer(entry.get("name"), keys, entry.get("created"))
        if action:
            self.snapshots.append({"doctype": "Dock", "name": entry.get("name"), "before": before})
            self.record("Dock", entry.get("name"), action)

    # ------------------------------------------------------------------ run
    def run(self):
        mode = self.doc.publish_mode or "Shared (Role-based)"
        roles = self.target_roles()
        users = self.target_users()
        default_map = {}
        layer_homes = []  # (user or None, workspace) for sidebar layers

        if not self.layout["blocks"]:
            frappe.throw(_("The layout is empty. Add at least one block before publishing."))
        if self.native:
            self.ensure_studio_icon()

        if mode.startswith("Shared"):
            payload, warns = schema.build_workspace_payload(self.layout)
            for w in warns:
                self.warn(w)
            if any(b["roles"] for b in self.layout["blocks"]):
                self.warn(
                    "Some blocks have role visibility. In Shared mode everyone who can open the workspace sees "
                    "them (records stay permission-checked). Use Personal mode to hide them per user."
                )
            if not roles and not users:
                self.warn("No audience set: the shared workspace is visible to every desk user.")
            shared_name = self.upsert_workspace(self.page_title, True, None, roles, payload)
            layer_homes.append((None, shared_name))
            for user in self.users_for_roles(roles):
                default_map[user] = shared_name
            for user in users:
                personal = self.publish_personal(user)
                default_map[user] = personal
                layer_homes.append((user, personal))
        else:
            audience = self.resolve_users()
            if not audience:
                frappe.throw(_("Personal mode needs at least one role or user in the audience."))
            if len(audience) > MAX_LAYER_USERS:
                frappe.throw(_("Personal mode would create {0} workspaces. Narrow the audience or use Shared mode.").format(len(audience)))
            for user in audience:
                name = self.publish_personal(user)
                default_map[user] = name
                layer_homes.append((user, name))

        if self.native:
            if cint(self.doc.publish_sidebar):
                self.publish_native_sidebar(layer_homes)
            if cint(self.doc.enable_dock):
                shared = next((w for u, w in layer_homes if u is None), None)
                self.publish_native_dock(self.dock_layers(shared, default_map))
            if cint(self.doc.create_desktop_icon):
                if self.dock_app() == STUDIO_APP:
                    self.ensure_app_desktop_icon()
                else:
                    self.warn(f"Desktop icons are added for the Workspaces app only; {schema.app_label(self.dock_app())} already has its own.")
        else:
            sidebar_ok = False
            if cint(self.doc.publish_sidebar):
                before = len(self.documents)
                self.publish_legacy_sidebar(self.title)
                sidebar_ok = len(self.documents) > before
            if cint(self.doc.create_desktop_icon):
                self.publish_desktop_icon(self.title, sidebar_ok)
            if cint(self.doc.enable_dock):
                self.warn("This build has no native Dock; dock items are shown in the Studio Quick Launch bar.")

        if cint(self.doc.set_as_default):
            self.set_default_workspace(default_map)

        # Clean up what earlier publishes created that is no longer part of the audience.
        current = {(d["doctype"], d["name"]) for d in self.documents if d["action"] != "removed"}
        for entry in self.prev_index:
            doctype, name = entry.get("doctype"), entry.get("name")
            if (doctype, name) in current:
                continue
            if doctype == "Dock":
                self.remove_dock_layer(entry)
            elif doctype in MANAGED_DOCTYPES and frappe.db.exists(doctype, name) and not is_shared_app_icon(doctype, name):
                self.snapshot(doctype, name)
                frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
                self.record(doctype, name, "removed")

    def publish_personal(self, user):
        user_roles = frappe.get_roles(user)
        payload, warns = schema.build_workspace_payload(self.layout, user_roles=user_roles)
        for w in warns:
            self.warn(w)
        return self.upsert_workspace(f"{self.page_title}-{user}", False, user, [], payload)

    def index(self):
        out, seen = [], set()
        for d in self.documents:
            if d["doctype"] not in INDEXED_DOCTYPES or d["action"] in ("removed", "entries removed"):
                continue
            if (d["doctype"], d["name"]) in seen:
                continue
            seen.add((d["doctype"], d["name"]))
            entry = {"doctype": d["doctype"], "name": d["name"]}
            if d.get("keys"):
                entry["keys"] = d["keys"]
            if d.get("created"):
                entry["created"] = 1
            out.append(entry)
        return out


def _sidebar_has_roles(sidebar):
    for it in sidebar["items"]:
        if it.get("roles") or any(c.get("roles") for c in it.get("children") or []):
            return True
    return False


def _dock_has_roles(dock):
    return any(i.get("roles") for i in dock["items"] if schema.is_native_dock_item(i))


# ---------------------------------------------------------------------- entry points
def _as_admin(fn, *args):
    actor = frappe.session.user
    frappe.set_user("Administrator")
    try:
        return fn(*args)
    finally:
        frappe.set_user(actor)


def _log(studio, action, status, documents, warnings, snapshots, actor):
    log = frappe.get_doc(
        {
            "doctype": "Studio Publish Log",
            "studio": studio,
            "action": action,
            "status": status,
            "published_on": now_datetime(),
            "published_by": actor,
            "documents": "\n".join(
                f"{d['action']}: {d['doctype']} {d['name']}" for d in documents
            ),
            "warnings": "\n".join(warnings),
            "snapshot": frappe.as_json(snapshots),
        }
    )
    log.insert(ignore_permissions=True)
    return log.name


def publish(name):
    actor = frappe.session.user
    studio = frappe.get_doc("Studio Workspace", name)
    publisher = Publisher(studio)
    try:
        _as_admin(publisher.run)
    except Exception as e:
        trace = frappe.get_traceback()
        frappe.db.rollback()
        detail = str(e).strip() or _("no message")
        if isinstance(e, frappe.ValidationError) and str(e).strip():
            message = detail
        else:
            message = _("Publishing failed ({0}): {1}").format(type(e).__name__, detail)
        err = frappe.log_error(title=f"Workspace Studio: publish failed ({name})", message=trace)
        err_name = getattr(err, "name", None)
        if err_name:
            message += " " + _("Full traceback: Error Log {0}").format(err_name)
        _log(name, "Publish", "Failed", [], [message, trace] + publisher.warnings, [], actor)
        frappe.db.commit()
        frappe.throw(message, title=_("Publish failed"))

    status = "Partial" if publisher.warnings else "Success"
    log_name = _log(name, "Publish", status, publisher.documents, publisher.warnings, publisher.snapshots, actor)

    studio.reload()
    studio.flags.from_publisher = True
    studio.status = "Published"
    studio.version = cint(studio.version) + 1
    studio.last_published_on = now_datetime()
    studio.last_published_by = actor
    studio.published_index = json.dumps(publisher.index())
    studio.published_summary = "\n".join(
        f"{d['doctype']}: {d['name']}" for d in publisher.documents if d["action"] != "removed"
    )
    quick = schema.quick_launch_dock(publisher.dock) if publisher.native else publisher.dock
    studio.published_dock_json = json.dumps(quick) if cint(studio.enable_dock) and quick["items"] else ""
    studio.save(ignore_permissions=True)

    from thinknxg_workspace_studio.runtime import clear_runtime_cache

    clear_runtime_cache()
    return {
        "status": status,
        "documents": publisher.documents,
        "warnings": publisher.warnings,
        "log": log_name,
        "version": studio.version,
    }


def unpublish(name):
    actor = frappe.session.user
    studio = frappe.get_doc("Studio Workspace", name)
    index = schema.loads(studio.published_index, [])
    snapshots, documents = [], []

    def run():
        for entry in index:
            doctype, docname = entry.get("doctype"), entry.get("name")
            if doctype == "Dock":
                keys = set(entry.get("keys") or []) - keys_claimed_by_others(name, docname)
                action, before = retire_dock_layer(docname, keys, entry.get("created"))
                if action:
                    snapshots.append({"doctype": "Dock", "name": docname, "before": before})
                    documents.append({"doctype": "Dock", "name": docname, "action": action})
                continue
            if doctype not in MANAGED_DOCTYPES or not frappe.db.exists(doctype, docname) or is_shared_app_icon(doctype, docname):
                continue
            snapshots.append({"doctype": doctype, "name": docname, "before": _jsonable(frappe.get_doc(doctype, docname))})
            frappe.delete_doc(doctype, docname, ignore_permissions=True, force=True)
            documents.append({"doctype": doctype, "name": docname, "action": "removed"})
        if frappe.get_meta("User").has_field("default_workspace"):
            names = [e.get("name") for e in index if e.get("doctype") == "Workspace"]
            if names:
                for user, ws in frappe.get_all(
                    "User", filters={"default_workspace": ["in", names]}, fields=["name", "default_workspace"], as_list=True
                ):
                    snapshots.append({"doctype": "User", "name": user, "field": "default_workspace", "before": ws})
                    frappe.db.set_value("User", user, "default_workspace", None, update_modified=False)

    _as_admin(run)
    log_name = _log(name, "Unpublish", "Success", documents, [], snapshots, actor)
    studio.flags.from_publisher = True
    studio.status = "Draft"
    studio.published_index = "[]"
    studio.published_summary = ""
    studio.published_dock_json = ""
    studio.save(ignore_permissions=True)

    from thinknxg_workspace_studio.runtime import clear_runtime_cache

    clear_runtime_cache()
    return {"documents": documents, "log": log_name}


def _restore(doctype, before):
    data = {k: v for k, v in before.items() if k not in STRIP_KEYS}
    meta = frappe.get_meta(doctype)
    for df in meta.get_table_fields():
        rows = data.get(df.fieldname) or []
        data[df.fieldname] = [{k: v for k, v in r.items() if k not in CHILD_STRIP_KEYS} for r in rows]
    name = before.get("name")
    if frappe.db.exists(doctype, name):
        doc = frappe.get_doc(doctype, name)
        for df in meta.get_table_fields():
            doc.set(df.fieldname, [])
        data.pop("name", None)
        doc.update(data)
        doc.save(ignore_permissions=True)
    else:
        data.pop("name", None)
        data["doctype"] = doctype
        doc = frappe.get_doc(data)
        doc.insert(ignore_permissions=True, set_name=name)


def rollback(log_name):
    actor = frappe.session.user
    log = frappe.get_doc("Studio Publish Log", log_name)
    if log.rolled_back:
        frappe.throw(_("This action was already rolled back."))
    if log.action == "Rollback" or log.status == "Failed":
        frappe.throw(_("Only successful Publish or Unpublish actions can be rolled back."))
    snapshots = schema.loads(log.snapshot, [])
    restored = []

    def run():
        for snap in reversed(snapshots):
            doctype, name, before = snap.get("doctype"), snap.get("name"), snap.get("before")
            if snap.get("field"):
                frappe.db.set_value(doctype, name, snap["field"], before, update_modified=False)
                restored.append({"doctype": doctype, "name": name, "action": f"{snap['field']} restored"})
            elif before is None:
                if frappe.db.exists(doctype, name):
                    frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
                    restored.append({"doctype": doctype, "name": name, "action": "removed"})
            else:
                _restore(doctype, before)
                restored.append({"doctype": doctype, "name": name, "action": "restored"})

    _as_admin(run)
    log.db_set("rolled_back", 1)
    _log(log.studio, "Rollback", "Success", restored, [f"Rolled back {log_name}"], [], actor)

    studio = frappe.get_doc("Studio Workspace", log.studio)
    studio.flags.from_publisher = True
    if log.action == "Publish":
        studio.status = "Modified" if cint(studio.version) > 1 else "Draft"
    else:
        studio.status = "Published"
        studio.published_index = json.dumps(
            [{"doctype": s["doctype"], "name": s["name"]} for s in snapshots if not s.get("field")]
        )
    studio.save(ignore_permissions=True)

    from thinknxg_workspace_studio.runtime import clear_runtime_cache

    clear_runtime_cache()
    return {"documents": restored}
