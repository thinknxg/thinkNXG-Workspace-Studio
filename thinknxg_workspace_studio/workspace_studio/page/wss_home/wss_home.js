// "My Workspace": where the Workspaces app tile and desktop icon land. It forwards each user to
// their own place instead of one fixed route for everyone:
//   1. their default workspace
//   2. otherwise the first workspace on their Workspaces Dock rail (highest-priority studio)
//   3. otherwise, for managers, the Workspace Studio designer
//   4. otherwise the desk
// The landing replaces itself in history, so Back does not bounce through it.
frappe.pages["wss-home"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("My Workspace"), single_column: true });
	$(wrapper).find(".layout-main-section").html(`<div class="text-muted" style="padding:40px;text-align:center">${__("Opening your workspace...")}</div>`);
};

frappe.pages["wss-home"].on_page_show = function () {
	const sidebar = frappe.app && frappe.app.sidebar;
	const pages = (frappe.boot.workspaces && frappe.boot.workspaces.pages) || [];
	const go = (route, module) => {
		if (!route) return false;
		if (route.startsWith("http")) {
			window.location.replace(route);
			return true;
		}
		if (module && sidebar && sidebar.select_shell) sidebar.select_shell(module);
		window.history.replaceState(null, "", route);
		frappe.router.route();
		return true;
	};
	const workspace_route = (name) => {
		const page = pages.find((p) => p.name === name);
		if (!page || !sidebar) return null;
		const module = (sidebar.module_for_workspace && sidebar.module_for_workspace(name)) || page.module;
		const route = sidebar.dock_entry_route({ link_type: "Workspace", link_to: name, url: null, module });
		return route ? { route, module } : null;
	};

	// 1. default workspace
	const dw = frappe.boot.user && frappe.boot.user.default_workspace;
	const target = dw && dw.name && workspace_route(dw.name);
	if (target && go(target.route, target.module)) return;

	// 2. first workspace on the Workspaces rail
	const app = (frappe.boot.app_data || []).find((a) => a.app_name === "thinknxg_workspace_studio");
	if (app && sidebar && sidebar.collect_dock_entries) {
		for (const entry of sidebar.collect_dock_entries(app)) {
			if (entry.link_type !== "Workspace") continue;
			const route = sidebar.dock_entry_route(entry);
			if (route && go(route, entry.module)) return;
		}
	}

	// 3. managers: the designer
	const roles = frappe.user_roles || [];
	if (roles.includes("System Manager") || roles.includes("Workspace Studio Manager")) {
		return go("/desk/workspace-studio");
	}

	// 4. the desk
	go("/desk");
};
