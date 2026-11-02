app_name = "thinknxg_workspace_studio"
app_title = "thinkNXG Workspace Studio"
app_publisher = "Kreatao"
app_description = "Visual drag-and-drop designer for workspaces, left sidebar menus and the Dock on thinkNXG ERP v16"
app_email = "kreataothinkcadd@gmail.com"
app_license = "MIT"
app_icon = "/assets/thinknxg_workspace_studio/images/logo.svg"
app_color = "#4f46e5"

required_apps = ["frappe"]

# Workspace Studio is also a v16 Dock app ("Workspaces"): studios can publish to its rail instead
# of thinkNXG ERP's. Managers see the Studio designer on it; audience users see their workspaces. The
# tile, rail and desktop icon open the first entry of the user's rail.
add_to_apps_screen = [
    {
        "name": "thinknxg_workspace_studio",
        "logo": "/assets/thinknxg_workspace_studio/images/logo.svg",
        "title": "Workspaces",
        "route": "/desk/wss-home",
        "has_permission": "thinknxg_workspace_studio.api.has_app_permission",
        "sequence_id": 5,
    }
]

# Adds the Home button settings to the boot, read by the Dock runtime.
boot_session = "thinknxg_workspace_studio.runtime.boot_session"

# Dock runtime is loaded on every desk page
app_include_js = ["/assets/thinknxg_workspace_studio/js/studio_runtime.js"]
app_include_css = ["/assets/thinknxg_workspace_studio/css/studio_runtime.css"]

before_install = "thinknxg_workspace_studio.install.before_install"
after_install = "thinknxg_workspace_studio.install.after_install"
after_migrate = "thinknxg_workspace_studio.install.after_migrate"

doc_events = {
    "Workspace Studio Settings": {
        "on_update": "thinknxg_workspace_studio.runtime.clear_runtime_cache",
    },
    # role audiences are materialised per user, so a role change republishes affected studios
    "User": {
        "on_update": "thinknxg_workspace_studio.runtime.on_user_update",
    },
}
