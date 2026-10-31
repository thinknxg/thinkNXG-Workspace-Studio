frappe.ui.form.on("Studio Workspace", {
	refresh(frm) {
		const $html = frm.get_field("designer_html").$wrapper;
		$html.html(
			frm.is_new()
				? `<div class="text-muted small">${__("Save the studio, then open the visual designer.")}</div>`
				: `<div class="wss-form-banner">
					<div>
						<div class="wss-form-banner-title">${__("Design this workspace visually")}</div>
						<div class="text-muted small">${__("Layout, left sidebar and Dock are edited in the drag-and-drop designer.")}</div>
					</div>
					<button class="btn btn-primary btn-sm wss-open-designer">${__("Open Designer")}</button>
				</div>`
		);
		$html.find(".wss-open-designer").on("click", () => frappe.set_route("workspace-studio", frm.doc.name));

		if (frm.is_new()) return;

		frm.add_custom_button(__("Open Designer"), () => frappe.set_route("workspace-studio", frm.doc.name));
		frm.add_custom_button(
			__("Publish"),
			() => {
				frappe.call({
					method: "thinknxg_workspace_studio.api.publish",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Publishing..."),
					callback: (r) => {
						const res = r.message || {};
						frappe.show_alert({
							message: __("Published with status {0}", [res.status]),
							indicator: res.status === "Success" ? "green" : "orange",
						});
						frm.reload_doc();
					},
				});
			},
			__("Actions")
		);
		if (["Published", "Modified"].includes(frm.doc.status)) {
			frm.add_custom_button(
				__("Unpublish"),
				() => {
					frappe.confirm(__("Remove every workspace, sidebar and icon this studio published?"), () => {
						frappe.call({
							method: "thinknxg_workspace_studio.api.unpublish",
							args: { name: frm.doc.name },
							freeze: true,
							callback: () => frm.reload_doc(),
						});
					});
				},
				__("Actions")
			);
		}
	},
});
