frappe.listview_settings["Studio Workspace"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = { Draft: "gray", Published: "green", Modified: "orange" };
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
	onload(listview) {
		listview.page.add_inner_button(__("Open Designer"), () => frappe.set_route("workspace-studio"));
	},
	button: {
		show: () => true,
		get_label: () => __("Design"),
		get_description: (doc) => __("Open {0} in the designer", [doc.name]),
		action: (doc) => frappe.set_route("workspace-studio", doc.name),
	},
};
