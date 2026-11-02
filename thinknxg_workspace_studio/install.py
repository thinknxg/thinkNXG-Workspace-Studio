import frappe

STUDIO_ROLE = "Workspace Studio Manager"


def _ensure_role():
    if not frappe.db.exists("Role", STUDIO_ROLE):
        frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": STUDIO_ROLE,
                "desk_access": 1,
                "is_custom": 1,
            }
        ).insert(ignore_permissions=True)


def before_install():
    _ensure_role()


def after_install():
    _ensure_role()
    settings = frappe.get_single("Workspace Studio Settings")
    if settings.enable_dock is None:
        settings.enable_dock = 1
    settings.save(ignore_permissions=True)
    frappe.db.commit()


def after_migrate():
    _ensure_role()
    _fix_app_icon_link()


def _fix_app_icon_link():
    """The Workspaces desktop icon opens My Workspace (/desk/wss-home), which forwards each user
    to their own workspace. Older versions pointed it at the designer for everyone."""
    if not frappe.db.exists("DocType", "Desktop Icon"):
        return
    for name in frappe.get_all(
        "Desktop Icon", filters={"icon_type": "App", "app": "thinknxg_workspace_studio"}, pluck="name"
    ):
        frappe.db.set_value("Desktop Icon", name, {"link_type": "External", "link": "/desk/wss-home"})
