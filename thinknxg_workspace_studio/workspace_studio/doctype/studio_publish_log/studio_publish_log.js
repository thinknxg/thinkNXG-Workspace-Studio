frappe.ui.form.on("Studio Publish Log", {
	refresh(frm) {
		if (frm.doc.action !== "Rollback" && !frm.doc.rolled_back && frm.doc.status !== "Failed") {
			frm.add_custom_button(__("Roll Back"), () => {
				frappe.confirm(__("Restore every document to the state it had before this action?"), () => {
					frappe.call({
						method: "thinknxg_workspace_studio.api.rollback",
						args: { log_name: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				});
			});
		}
	},
});
