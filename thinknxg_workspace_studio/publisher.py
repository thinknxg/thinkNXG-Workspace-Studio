"""Publishes Studio Workspace designs into real Frappe documents and rolls them back.

Targets (all introspected through DocType meta, so the publisher adapts to the
exact v16 schema on the site and logs anything it had to skip):
  * Workspace            - layout blocks, shortcuts, cards, charts, number cards, quick lists
  * Workspace Sidebar    - left sidebar menu (v16)
  * Desktop Icon         - desktop/app-screen icon (v16)
  * User.default_workspace
  * The Dock is served by this app's runtime from `published_dock_json`.
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
MANAGED_DOCTYPES = ("Workspace", "Workspace Sidebar", "Desktop Icon")
# v16: Workspace.module is mandatory. Frappe triages pages created without one into these.
PRIVATE_MODULE = "Private"
CUSTOM_MODULE = "Custom Workspaces"


def resolve_module(chosen, for_user):
    """Module for a published workspace.

    Private (personal) pages always live in v16's `Private` module, which is what the desk draws
    each user's own shell from. Shared pages use the studio's module, or `Custom Workspaces`
    when none is chosen (a shared page may not use `Private`).
    """
    if for_user:
        target = PRIVATE_MODULE
    elif chosen and chosen != PRIVATE_MODULE:
        return chosen
    else:
        target = CUSTOM_MODULE
    try:
        from frappe.desk.doctype.workspace.workspace import triage_module

        return triage_module(for_user)
    except ImportError:
        pass
    if not frappe.db.exists("Module Def", target):
        frappe.get_doc({"doctype": "Module Def", "module_name": target, "custom": 1}).insert(
            ignore_permissions=True
        )
    return target


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
        self.owned = {(d.get("doctype"), d.get("name")) for d in schema.loads(studio.published_index, [])}
        self.title = (studio.workspace_title or studio.title).strip()

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

    def record(self, doctype, name, action, route=None):
        self.documents.append({"doctype": doctype, "name": name, "action": action, "route": route})

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

    # ------------------------------------------------------------------ audience
    def target_roles(self):
        return [t.role for t in self.doc.targets if t.target_type == "Role" and t.role]

    def target_users(self):
        return [t.user for t in self.doc.targets if t.target_type == "User" and t.user]

    def users_for_roles(self, roles):
        if not roles:
            return []
        parents = frappe.get_all(
            "Has Role", filters={"role": ["in", roles], "parenttype": "User"}, pluck="parent", distinct=True
        )
        if not parents:
            return []
        users = frappe.get_all(
            "User",
            filters={"name": ["in", parents], "enabled": 1, "user_type": "System User"},
            pluck="name",
        )
        return [u for u in users if u not in ("Administrator", "Guest")]

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
            "title": self.title,
            "public": 1 if public else 0,
            "for_user": for_user or "",
            "icon": self.doc.icon or None,
            "indicator_color": self.doc.indicator_color or None,
            "parent_page": (self.doc.parent_page or "") if public else "",
            "module": resolve_module(self.doc.module, None if public else for_user),
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

        route = ["private", slug(self.title)] if not public else [slug(self.title)]
        self.record("Workspace", ws.name, action, "/app/" + "/".join(route))
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
    def publish_sidebar(self, name):
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
            "module": resolve_module(self.doc.module, None),
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
            "link": "/app/" + slug(self.title),
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

    # ------------------------------------------------------------------ run
    def run(self):
        mode = self.doc.publish_mode or "Shared (Role-based)"
        roles = self.target_roles()
        users = self.target_users()
        default_map = {}
        published = []

        if not self.layout["blocks"]:
            frappe.throw(_("The layout is empty. Add at least one block before publishing."))

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
            shared_name = self.upsert_workspace(self.title, True, None, roles, payload)
            published.append(shared_name)
            for user in self.users_for_roles(roles):
                default_map[user] = shared_name
            for user in users:
                personal = self.publish_personal(user)
                published.append(personal)
                default_map[user] = personal
        else:
            audience = self.resolve_users()
            if not audience:
                frappe.throw(_("Personal mode needs at least one role or user in the audience."))
            if len(audience) > 500:
                frappe.throw(_("Personal mode would create {0} workspaces. Narrow the audience or use Shared mode.").format(len(audience)))
            for user in audience:
                name = self.publish_personal(user)
                published.append(name)
                default_map[user] = name

        sidebar_ok = False
        if cint(self.doc.publish_sidebar):
            before = len(self.documents)
            self.publish_sidebar(self.title)
            sidebar_ok = len(self.documents) > before
        if cint(self.doc.create_desktop_icon):
            self.publish_desktop_icon(self.title, sidebar_ok)
        if cint(self.doc.set_as_default):
            self.set_default_workspace(default_map)

        # Remove workspaces this studio created earlier that are no longer part of the audience.
        current = {(d["doctype"], d["name"]) for d in self.documents}
        for doctype, name in sorted(self.owned):
            if doctype in MANAGED_DOCTYPES and (doctype, name) not in current and frappe.db.exists(doctype, name):
                self.snapshot(doctype, name)
                frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
                self.record(doctype, name, "removed")

    def publish_personal(self, user):
        user_roles = frappe.get_roles(user)
        payload, warns = schema.build_workspace_payload(self.layout, user_roles=user_roles)
        for w in warns:
            self.warn(w)
        return self.upsert_workspace(f"{self.title}-{user}", False, user, [], payload)

    def index(self):
        return [
            {"doctype": d["doctype"], "name": d["name"]}
            for d in self.documents
            if d["doctype"] in MANAGED_DOCTYPES and d["action"] != "removed"
        ]


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
        frappe.db.rollback()
        message = str(e) if isinstance(e, frappe.ValidationError) else _("Publishing failed: {0}").format(e)
        if not isinstance(e, frappe.ValidationError):
            frappe.log_error(title="Workspace Studio: publish failed")
        _log(name, "Publish", "Failed", [], [message] + publisher.warnings, [], actor)
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
    studio.published_dock_json = json.dumps(publisher.dock) if cint(studio.enable_dock) else ""
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
            if doctype not in MANAGED_DOCTYPES or not frappe.db.exists(doctype, docname):
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
