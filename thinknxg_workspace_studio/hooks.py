app_name = "thinknxg_workspace_studio"
app_title = "thinkNXG Workspace Studio"
app_publisher = "Kreatao"
app_description = "Visual drag-and-drop designer for workspaces, left sidebar menus and the Dock on thinkNXG ERP / Frappe v16"
app_email = "kreataothinkcadd@gmail.com"
app_license = "MIT"
app_icon = "/assets/thinknxg_workspace_studio/images/logo.svg"
app_color = "#4f46e5"

required_apps = ["frappe"]

# Shown on the v16 apps screen / desktop
add_to_apps_screen = [
    {
        "name": "thinknxg_workspace_studio",
        "logo": "/assets/thinknxg_workspace_studio/images/logo.svg",
        "title": "Workspace Studio",
        "route": "/app/workspace-studio",
        "has_permission": "thinknxg_workspace_studio.api.has_app_permission",
    }
]

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
}
