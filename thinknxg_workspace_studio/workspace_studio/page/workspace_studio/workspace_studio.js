// thinkNXG Workspace Studio — visual designer
// Layout canvas, left sidebar builder and Dock designer with structured property panels.

frappe.pages["workspace-studio"].on_page_load = function (wrapper) {
	wrapper.wss_app = new wss.StudioApp(wrapper);
};
frappe.pages["workspace-studio"].on_page_show = function (wrapper) {
	wrapper.wss_app && wrapper.wss_app.route();
};
frappe.pages["workspace-studio"].on_page_hide = function (wrapper) {
	wrapper.wss_app && wrapper.wss_app.on_hide();
};

frappe.provide("wss");

(function () {
	const API = "thinknxg_workspace_studio.api.";
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const uid = () => Math.random().toString(36).slice(2, 12);
	const clone = (o) => JSON.parse(JSON.stringify(o));
	const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

	// ------------------------------------------------------------------ icons
	const P = {
		heading: '<path d="M6 4v16M18 4v16M6 12h12"/>',
		text: '<path d="M4 6h16M4 12h16M4 18h10"/>',
		spacer: '<path d="M4 8h16M4 16h16" stroke-dasharray="2 3"/>',
		shortcut: '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M9 15l6-6M10 9h5v5"/>',
		card: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 9h10M7 13h10M7 17h6"/>',
		chart: '<path d="M4 20V11M10 20V5M16 20v-7M21 20H3"/>',
		number: '<path d="M5 9h14M5 15h14M10 4L8 20M16 4l-2 16"/>',
		quicklist: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
		code: '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4"/>',
		section: '<path d="M4 5h16M8 11h12M8 17h12M4 5v12"/>',
		link: '<path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1"/><path d="M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1"/>',
		workspace: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
		doctype: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
		plus: '<path d="M12 5v14M5 12h14"/>',
		minus: '<path d="M5 12h14"/>',
		report: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
		page: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h5"/>',
		dashboard: '<path d="M12 14l4-4"/><path d="M3.5 18a9 9 0 1 1 17 0"/>',
		globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
		trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
		copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/>',
		undo: '<path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
		redo: '<path d="M15 14l5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/>',
		grip: '<circle cx="9" cy="6" r="1.2"/><circle cx="15" cy="6" r="1.2"/><circle cx="9" cy="12" r="1.2"/><circle cx="15" cy="12" r="1.2"/><circle cx="9" cy="18" r="1.2"/><circle cx="15" cy="18" r="1.2"/>',
		desktop: '<rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
		tablet: '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M11 18h2"/>',
		mobile: '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
		users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M22 20a7 7 0 0 0-4-6.3"/>',
		dock: '<rect x="2" y="15" width="20" height="6" rx="2"/><path d="M6 18h.01M10 18h.01M14 18h.01M18 18h.01"/><path d="M6 4h12v7H6z"/>',
		sidebar: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M5.5 7h1.5M5.5 10h1.5M5.5 13h1.5"/>',
		sliders: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
		eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
		lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
		upload: '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>',
		history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 3"/>',
		wand: '<path d="M15 4V2M15 10V8M11 6H9M21 6h-2M3 21l12-12"/>',
		caret: '<path d="M9 6l6 6-6 6"/>',
		x: '<path d="M6 6l12 12M18 6L6 18"/>',
		edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
		filter: '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
		alert: '<path d="M12 3l10 18H2z"/><path d="M12 10v4M12 18h.01"/>',
		check: '<path d="M5 12l5 5L20 7"/>',
		info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
		layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
		separator: '<path d="M12 4v16"/>',
		external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
	};
	const ico = (name, size = 16) =>
		`<svg class="wss-ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[name] || ""}</svg>`;
	const ficon = (name, size = "sm") => {
		if (!name) return "";
		try {
			return frappe.utils.icon(name, size);
		} catch (e) {
			return "";
		}
	};

	// ------------------------------------------------------------------ catalog
	const BLOCKS = {
		header: { label: __("Header"), icon: "heading", col: 12, group: "structure", desc: __("Section title") },
		paragraph: { label: __("Text"), icon: "text", col: 12, group: "structure", desc: __("Notes or guidance") },
		spacer: { label: __("Spacer"), icon: "spacer", col: 12, group: "structure", desc: __("Vertical breathing room") },
		shortcut: { label: __("Shortcut"), icon: "shortcut", col: 3, group: "navigation", desc: __("Tile to a list, report or page") },
		card: { label: __("Link Card"), icon: "card", col: 4, group: "navigation", desc: __("Grouped list of links") },
		quick_list: { label: __("Quick List"), icon: "quicklist", col: 4, group: "navigation", desc: __("Latest records of a DocType") },
		number_card: { label: __("Number Card"), icon: "number", col: 3, group: "insights", desc: __("A single KPI") },
		chart: { label: __("Chart"), icon: "chart", col: 6, group: "insights", desc: __("Dashboard Chart") },
		custom_block: { label: __("Custom HTML"), icon: "code", col: 6, group: "insights", desc: __("Custom HTML Block") },
	};
	const GROUPS = { structure: __("Structure"), navigation: __("Navigation"), insights: __("Insights") };
	const PATTERNS = {
		shortcut_row: { label: __("Shortcut row"), icon: "shortcut", desc: __("4 shortcuts"), make: () => [1, 2, 3, 4].map(() => new_block("shortcut")) },
		kpi_strip: { label: __("KPI strip"), icon: "number", desc: __("4 number cards"), make: () => [1, 2, 3, 4].map(() => new_block("number_card")) },
		chart_pair: { label: __("Chart pair"), icon: "chart", desc: __("2 half-width charts"), make: () => [new_block("chart"), new_block("chart")] },
		card_section: {
			label: __("Card section"),
			icon: "card",
			desc: __("Header + 3 link cards"),
			make: () => {
				const h = new_block("header");
				h.data.text = __("Masters & Reports");
				h.data.size = "Medium";
				return [h, new_block("card"), new_block("card"), new_block("card")];
			},
		},
	};
	const SHORTCUT_COLORS = { Grey: "#94a3b8", Green: "#22c55e", Red: "#ef4444", Orange: "#f97316", Pink: "#ec4899", Yellow: "#eab308", Blue: "#3b82f6", Cyan: "#06b6d4" };
	// native: the v16 Dock can hold it. The rest go to the Studio Quick Launch bar.
	const DOCK_TYPES = {
		Sidebar: { label: __("Module"), icon: "sidebar", color: "#4f46e5", native: true },
		Workspace: { label: __("Workspace"), icon: "workspace", color: "#6366f1", native: true },
		DocType: { label: __("DocType List"), icon: "doctype", color: "#0ea5e9" },
		New: { label: __("New Document"), icon: "plus", color: "#10b981" },
		Report: { label: __("Report"), icon: "report", color: "#f59e0b" },
		Page: { label: __("Page"), icon: "page", color: "#8b5cf6" },
		Dashboard: { label: __("Dashboard"), icon: "dashboard", color: "#ef4444" },
		URL: { label: __("External URL"), icon: "globe", color: "#64748b", native: true },
	};
	const is_native_dock = (it) => it.type === "item" && !!(DOCK_TYPES[it.link_type] || {}).native;
	const SWATCHES = ["#4f46e5", "#0ea5e9", "#06b6d4", "#10b981", "#22c55e", "#eab308", "#f59e0b", "#f97316", "#ef4444", "#ec4899", "#8b5cf6", "#64748b", "#0f172a"];
	const SIDEBAR_TYPES = {
		section: { label: __("Section"), icon: "section", desc: __("Collapsible group") },
		link: { label: __("Link"), icon: "link", desc: __("DocType, report, page, URL...") },
		spacer: { label: __("Divider"), icon: "spacer", desc: __("Visual separator") },
	};
	const LINK_ICON = { DocType: "doctype", Report: "report", Page: "page", Workspace: "workspace", Dashboard: "dashboard", URL: "globe", New: "plus" };

	function new_block(type) {
		const data = {
			header: { text: __("New section"), size: "Large" },
			paragraph: { text: "" },
			spacer: {},
			shortcut: { label: "", type: "DocType", link_to: "", url: "", doc_view: "", color: "Grey", format: "", filters: [] },
			card: { label: __("Links"), links: [] },
			chart: { chart_name: "", label: "" },
			number_card: { number_card_name: "", label: "" },
			quick_list: { document_type: "", label: "", filters: [] },
			custom_block: { custom_block_name: "", label: "" },
		}[type];
		return { id: uid(), type, col: BLOCKS[type].col, roles: [], data: clone(data) };
	}

	function new_sidebar_item(type) {
		if (type === "section") return { id: uid(), type, label: __("New section"), icon: "", collapsible: 1, keep_closed: 0, roles: [], children: [] };
		if (type === "spacer") return { id: uid(), type };
		return { id: uid(), type: "link", label: __("New link"), icon: "", link_type: "DocType", link_to: "", url: "", roles: [] };
	}

	function new_dock_item(type) {
		if (type === "separator") return { id: uid(), type: "separator" };
		const t = DOCK_TYPES[type] || DOCK_TYPES.DocType;
		return { id: uid(), type: "item", label: t.label, icon: "", color: t.color, link_type: type, link_to: "", url: "", doc_view: "", new_tab: 0, roles: [] };
	}

	function has_target(b) {
		const d = b.data || {};
		switch (b.type) {
			case "shortcut":
				return d.type === "URL" ? !!d.url : !!d.link_to;
			case "card":
				return (d.links || []).some((l) => l.link_to);
			case "chart":
				return !!d.chart_name;
			case "number_card":
				return !!d.number_card_name;
			case "quick_list":
				return !!d.document_type;
			case "custom_block":
				return !!d.custom_block_name;
			default:
				return true;
		}
	}

	function block_title(b) {
		const d = b.data || {};
		return d.label || d.text || d.link_to || d.chart_name || d.number_card_name || d.document_type || BLOCKS[b.type].label;
	}

	function hash(s) {
		let h = 0;
		for (const c of String(s || "x")) h = (h * 31 + c.charCodeAt(0)) >>> 0;
		return h;
	}

	function call(method, args, freeze_message) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: API + method,
				args: args || {},
				freeze: !!freeze_message,
				freeze_message,
				callback: (r) => resolve(r.message),
				error: (e) => reject(e),
			});
		});
	}

	function filter_text(filters) {
		return (filters || []).map((f) => `${f[0]} ${f[1]} ${Array.isArray(f[2]) ? f[2].join(", ") : f[2] == null ? "" : f[2]}`);
	}

	function download_json(filename, data) {
		const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
		const a = document.createElement("a");
		a.href = URL.createObjectURL(blob);
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		setTimeout(() => {
			URL.revokeObjectURL(a.href);
			a.remove();
		}, 500);
	}

	// Structured form helper: a thinkNXG FieldGroup whose changes stream back into designer state.
	function make_form($parent, fields, values, on_change) {
		$parent.empty();
		let ready = false;
		const live = new Set();
		const fg = new frappe.ui.FieldGroup({
			fields: fields.map((df) => {
				if (["Data", "Small Text", "Text"].includes(df.fieldtype)) live.add(df.fieldname);
				return Object.assign({}, df, {
					onchange() {
						if (!ready || !df.fieldname) return;
						on_change(df.fieldname, fg.get_value(df.fieldname), fg);
					},
				});
			}),
			body: $parent[0],
		});
		fg.make();
		const vals = {};
		fields.forEach((df) => {
			if (df.fieldname && values && values[df.fieldname] !== undefined && values[df.fieldname] !== null) {
				vals[df.fieldname] = values[df.fieldname];
			}
		});
		Promise.resolve(fg.set_values(vals)).finally(() => setTimeout(() => (ready = true), 80));
		$parent.on("input", "input, textarea", (e) => {
			const name = $(e.target).attr("data-fieldname");
			if (ready && name && live.has(name)) on_change(name, e.target.value, fg, true);
		});
		return fg;
	}

	const roles_df = (label) => ({
		fieldtype: "MultiSelectPills",
		fieldname: "roles",
		label: label || __("Only show to roles"),
		description: __("Leave empty to show to everyone in the audience."),
		get_data: (txt) => frappe.db.get_link_options("Role", txt),
	});

	// ================================================================== App shell
	wss.StudioApp = class StudioApp {
		constructor(wrapper) {
			this.wrapper = wrapper;
			this.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Workspace Studio"), single_column: true });
			this.$main = $(wrapper).find(".layout-main-section");
			$(wrapper).addClass("wss-page");
			this.designer = null;
		}

		route() {
			const route = frappe.get_route();
			const name = route[1] ? decodeURIComponent(route[1]) : null;
			if (name) {
				if (this.designer && this.designer.name === name && this.designer.alive) return;
				this.open(name);
			} else {
				this.landing();
			}
		}

		on_hide() {
			if (this.designer && this.designer.dirty) {
				this.designer.save(true).then(() => frappe.show_alert({ message: __("Studio draft saved"), indicator: "blue" }));
			}
		}

		reset_page() {
			if (this.designer) this.designer.destroy();
			this.designer = null;
			this.page.clear_primary_action();
			this.page.clear_secondary_action();
			this.page.clear_menu();
			this.page.clear_indicator();
			this.$main.empty();
		}

		// -------------------------------------------------------------- landing
		landing() {
			this.reset_page();
			this.page.set_title(__("Workspace Studio"));
			this.page.set_primary_action(__("New Studio"), () => this.new_dialog());
			this.page.set_secondary_action(__("Import Workspace"), () => this.import_dialog());
			this.page.add_menu_item(__("Import Package (.json)"), () => this.import_package_dialog());
			this.page.add_menu_item(__("Dock Settings"), () => frappe.set_route("Form", "Workspace Studio Settings"));
			this.page.add_menu_item(__("Publish Logs"), () => frappe.set_route("List", "Studio Publish Log"));
			this.page.add_menu_item(__("Studio Records"), () => frappe.set_route("List", "Studio Workspace"));

			this.$main.html(`
				<div class="wss-landing">
					<div class="wss-hero">
						<div class="wss-hero-mark">${ico("layers", 26)}</div>
						<div>
							<div class="wss-hero-title">${__("thinkNXG Workspace Studio")}</div>
							<div class="wss-hero-sub">${__("Design workspaces, left sidebar menus and the Dock for specific roles or users — then publish them as real thinkNXG ERP workspaces.")}</div>
						</div>
					</div>
					<div class="wss-cards"><div class="wss-loading">${__("Loading studios...")}</div></div>
				</div>`);
			call("get_studios").then((rows) => this.render_cards(rows || []));
		}

		render_cards(rows) {
			const $cards = this.$main.find(".wss-cards").empty();
			const tile = $(`<button class="wss-card-new">
				<span class="wss-card-new-ico">${ico("plus", 22)}</span>
				<span class="wss-card-new-title">${__("New Studio")}</span>
				<span class="wss-card-new-sub">${__("Start from a starter layout or a blank canvas")}</span>
			</button>`).on("click", () => this.new_dialog());
			$cards.append(tile);
			const colors = { Draft: "gray", Published: "green", Modified: "orange" };
			rows.forEach((r) => {
				const thumb = Object.entries(r.block_types || {})
					.map(([t, n]) => `<span class="wss-thumb-chip">${ico(BLOCKS[t] ? BLOCKS[t].icon : "workspace", 12)} ${n}</span>`)
					.join("");
				const $c = $(`<div class="wss-studio-card" tabindex="0">
					<div class="wss-studio-top">
						<span class="wss-studio-ico">${ficon(r.icon, "md") || ico("workspace", 18)}</span>
						<span class="indicator-pill ${colors[r.status] || "gray"}">${__(r.status)}</span>
					</div>
					<div class="wss-studio-title">${esc(r.title)}</div>
					<div class="wss-studio-sub">${__("Label")}: ${esc(r.workspace_title || r.title)} · ${esc(__(r.publish_mode || ""))}</div>
					<div class="wss-thumb">${thumb || `<span class="text-muted small">${__("Empty layout")}</span>`}</div>
					<div class="wss-studio-foot">
						<span class="text-muted small">${__("Edited")} ${comment_when(r.modified)}</span>
						<span class="wss-studio-acts">
							<button class="btn btn-xs btn-default" data-act="dup" title="${__("Duplicate")}">${ico("copy", 13)}</button>
							<button class="btn btn-xs btn-default" data-act="export" title="${__("Export package")}">${ico("upload", 13)}</button>
							<button class="btn btn-xs btn-default" data-act="del" title="${__("Delete")}">${ico("trash", 13)}</button>
						</span>
					</div>
				</div>`);
				$c.on("click", (e) => {
					const act = $(e.target).closest("[data-act]").attr("data-act");
					if (act === "dup") return this.duplicate(r.name);
					if (act === "export") return this.export_package(r.name);
					if (act === "del") return this.delete_studio(r.name, r.status);
					frappe.set_route("workspace-studio", r.name);
				});
				$c.on("keydown", (e) => e.key === "Enter" && frappe.set_route("workspace-studio", r.name));
				$cards.append($c);
			});
		}

		new_dialog() {
			const d = new frappe.ui.Dialog({
				title: __("New Studio"),
				fields: [
					{ fieldtype: "Data", fieldname: "title", label: __("Studio Name"), reqd: 1, description: __("Internal name, e.g. 'Sales Team Home'") },
					{ fieldtype: "Data", fieldname: "workspace_title", label: __("Workspace Label"), description: __("What users see in the desk. Defaults to the studio name.") },
					{
						fieldtype: "Select",
						fieldname: "template",
						label: __("Start from"),
						options: [
							{ value: "starter", label: __("Starter layout (sample shortcuts, card and list)") },
							{ value: "blank", label: __("Blank canvas") },
						],
						default: "starter",
					},
				],
				primary_action_label: __("Create & Design"),
				primary_action: (v) => {
					call("create_studio", v, __("Creating...")).then((name) => {
						d.hide();
						frappe.set_route("workspace-studio", name);
					});
				},
			});
			d.show();
		}

		import_dialog(on_pick) {
			const d = new frappe.ui.Dialog({
				title: on_pick ? __("Replace layout from a Workspace") : __("Import an existing Workspace"),
				fields: [
					{ fieldtype: "Link", fieldname: "workspace", label: __("Workspace"), options: "Workspace", reqd: 1, get_query: () => ({ filters: { public: 1 } }) },
					on_pick ? null : { fieldtype: "Data", fieldname: "title", label: __("New Studio Name"), reqd: 1 },
				].filter(Boolean),
				primary_action_label: on_pick ? __("Replace") : __("Import"),
				primary_action: (v) => {
					if (on_pick) {
						call("read_workspace", { workspace: v.workspace }, __("Reading workspace...")).then((data) => {
							d.hide();
							on_pick(data);
						});
						return;
					}
					call("import_from_workspace", v, __("Importing...")).then((r) => {
						d.hide();
						if (r.warnings && r.warnings.length) frappe.msgprint({ title: __("Imported with notes"), message: r.warnings.map(esc).join("<br>"), indicator: "orange" });
						frappe.set_route("workspace-studio", r.name);
					});
				},
			});
			d.fields_dict.workspace.df.onchange = () => {
				const ws = d.get_value("workspace");
				if (ws && d.fields_dict.title && !d.get_value("title")) d.set_value("title", ws + " " + __("Studio"));
			};
			d.show();
		}

		import_package_dialog() {
			let pkg = null;
			const d = new frappe.ui.Dialog({
				title: __("Import Studio Package"),
				fields: [
					{ fieldtype: "HTML", fieldname: "file_html" },
					{ fieldtype: "Data", fieldname: "title", label: __("Studio Name (optional)") },
				],
				primary_action_label: __("Import"),
				primary_action: (v) => {
					if (!pkg) return frappe.msgprint(__("Choose a .json package first."));
					call("import_package", { package: pkg, title: v.title }, __("Importing...")).then((name) => {
						d.hide();
						frappe.set_route("workspace-studio", name);
					});
				},
			});
			const $f = $(`<div class="wss-file-pick"><input type="file" accept=".json,application/json"><div class="text-muted small">${__("A file exported with 'Export package'.")}</div></div>`);
			$f.find("input").on("change", (e) => {
				const file = e.target.files[0];
				if (!file) return;
				const reader = new FileReader();
				reader.onload = () => {
					pkg = reader.result;
					try {
						const t = JSON.parse(pkg).title;
						if (t && !d.get_value("title")) d.set_value("title", t);
					} catch (err) {
						pkg = null;
						frappe.msgprint(__("That file is not valid JSON."));
					}
				};
				reader.readAsText(file);
			});
			d.fields_dict.file_html.$wrapper.append($f);
			d.show();
		}

		duplicate(name) {
			frappe.prompt({ fieldtype: "Data", fieldname: "title", label: __("New Studio Name"), reqd: 1, default: name + " " + __("Copy") }, (v) => {
				call("duplicate_studio", { name, title: v.title }, __("Duplicating...")).then((n) => frappe.set_route("workspace-studio", n));
			}, __("Duplicate Studio"));
		}

		export_package(name) {
			call("export_package", { name }).then((data) => download_json(frappe.scrub(name) + ".workspace-studio.json", data));
		}

		delete_studio(name, status) {
			const msg = ["Published", "Modified"].includes(status)
				? __("Delete {0}? Its published workspaces, sidebar and icon will be removed first.", [esc(name)])
				: __("Delete {0}?", [esc(name)]);
			frappe.confirm(msg, () => call("delete_studio", { name }, __("Deleting...")).then(() => this.landing()));
		}

		// -------------------------------------------------------------- designer
		open(name) {
			this.reset_page();
			this.$main.html(`<div class="wss-loading">${__("Opening designer...")}</div>`);
			Promise.all([call("get_studio", { name }), this.hints ? Promise.resolve(this.hints) : call("get_meta_hints")])
				.then(([data, hints]) => {
					this.hints = hints || {};
					this.designer = new wss.Designer(this, data);
				})
				.catch(() => {
					this.$main.html(`<div class="wss-loading">${__("Could not open {0}.", [esc(name)])}</div>`);
				});
		}
	};

	// ================================================================== Designer
	wss.Designer = class Designer {
		constructor(app, data) {
			this.app = app;
			this.page = app.page;
			this.$main = app.$main;
			this.hints = app.hints || {};
			this.name = data.name;
			this.data = data;
			this.alive = true;
			this.state = { layout: data.layout, sidebar: data.sidebar, dock: data.dock };
			this.props = Object.assign({}, data.props);
			this.targets = data.targets || [];
			this.modified = data.modified;
			this.status = data.status;
			this.tab = "layout";
			this.device = "desktop";
			this.sel = { layout: null, sidebar: null, dock: null };
			this.sb_collapsed = new Set();
			this.history = [];
			this.future = [];
			this.drag = null;
			this.last = this.serialize();
			this.saved = this.last;
			this.make();
		}

		// -------------------------------------------------------------- state
		serialize() {
			return JSON.stringify({ layout: this.state.layout, sidebar: this.state.sidebar, dock: this.state.dock, props: this.props, targets: this.targets });
		}

		get dirty() {
			this.flush_pending(true);
			return this.last !== this.saved;
		}

		commit() {
			clearTimeout(this._commit_t);
			this._commit_t = null;
			const now = this.serialize();
			if (now === this.last) return;
			this.history.push(this.last);
			if (this.history.length > 100) this.history.shift();
			this.future = [];
			this.last = now;
			this.update_chrome();
		}

		commit_soon() {
			clearTimeout(this._commit_t);
			this._commit_t = setTimeout(() => this.commit(), 350);
			this.mark_unsaved();
		}

		flush_pending(silent) {
			if (this._commit_t) {
				if (silent) {
					clearTimeout(this._commit_t);
					this._commit_t = null;
					const now = this.serialize();
					if (now !== this.last) {
						this.history.push(this.last);
						this.future = [];
						this.last = now;
					}
				} else this.commit();
			}
		}

		restore(snapshot) {
			const s = JSON.parse(snapshot);
			this.state = { layout: s.layout, sidebar: s.sidebar, dock: s.dock };
			this.props = s.props;
			this.targets = s.targets;
			this.last = snapshot;
			this.render();
		}

		undo() {
			this.flush_pending();
			if (!this.history.length) return;
			this.future.push(this.last);
			this.restore(this.history.pop());
		}

		redo() {
			if (!this.future.length) return;
			this.history.push(this.last);
			this.restore(this.future.pop());
		}

		get blocks() {
			return this.state.layout.blocks;
		}

		// -------------------------------------------------------------- shell
		make() {
			this.page.set_title(this.data.title);
			this.page.set_primary_action(__("Publish"), () => this.publish());
			this.page.set_secondary_action(__("Save"), () => this.save());
			this.page.add_menu_item(__("All Studios"), () => frappe.set_route("workspace-studio"));
			this.page.add_menu_item(__("Open Studio Record"), () => frappe.set_route("Form", "Studio Workspace", this.name));
			this.page.add_menu_item(__("Replace layout from Workspace..."), () =>
				this.app.import_dialog((data) => {
					frappe.confirm(__("Replace the current layout and sidebar with the imported ones? You can undo this."), () => {
						this.state.layout = data.layout;
						this.state.sidebar = data.sidebar;
						this.sel.layout = null;
						this.commit();
						this.render();
						if (data.warnings && data.warnings.length) frappe.msgprint(data.warnings.map(esc).join("<br>"));
					});
				})
			);
			this.page.add_menu_item(__("Export Package"), () => this.app.export_package(this.name));
			this.page.add_menu_item(__("Duplicate Studio"), () => this.app.duplicate(this.name));
			this.page.add_menu_item(__("Unpublish"), () => this.unpublish());
			this.page.add_menu_item(__("Keyboard Shortcuts"), () => this.shortcuts_help());

			const tabs = [
				["layout", "workspace", __("Layout")],
				["sidebar", "sidebar", __("Sidebar Menu")],
				["dock", "dock", __("Dock")],
				["settings", "users", __("Audience & Settings")],
			];
			this.$main.html(`
				<div class="wss-designer">
					<div class="wss-toolbar">
						<div class="wss-tabs" role="tablist">
							${tabs.map(([k, i, l]) => `<button class="wss-tab" role="tab" data-tab="${k}">${ico(i, 15)}<span>${l}</span></button>`).join("")}
						</div>
						<div class="wss-toolbar-right">
							<div class="wss-devices" title="${__("Preview width")}">
								${["desktop", "tablet", "mobile"].map((d) => `<button data-device="${d}" title="${__(frappe.utils.to_title_case(d))}">${ico(d, 15)}</button>`).join("")}
							</div>
							<div class="wss-history-btns">
								<button data-cmd="undo" title="${__("Undo")} (Ctrl+Z)">${ico("undo", 15)}</button>
								<button data-cmd="redo" title="${__("Redo")} (Ctrl+Shift+Z)">${ico("redo", 15)}</button>
							</div>
							<span class="wss-save-state"></span>
						</div>
					</div>
					<div class="wss-body">
						<aside class="wss-palette"></aside>
						<main class="wss-stage"></main>
						<aside class="wss-inspector"></aside>
					</div>
				</div>`);
			this.$palette = this.$main.find(".wss-palette");
			this.$stage = this.$main.find(".wss-stage");
			this.$inspector = this.$main.find(".wss-inspector");

			this.$main.find(".wss-tab").on("click", (e) => this.set_tab(e.currentTarget.dataset.tab));
			this.$main.find("[data-device]").on("click", (e) => {
				this.device = e.currentTarget.dataset.device;
				this.render_stage();
				this.update_chrome();
			});
			this.$main.find("[data-cmd=undo]").on("click", () => this.undo());
			this.$main.find("[data-cmd=redo]").on("click", () => this.redo());

			this._keys = (e) => this.on_key(e);
			window.addEventListener("keydown", this._keys, true);
			this._unload = (e) => {
				if (this.dirty) {
					e.preventDefault();
					e.returnValue = "";
				}
			};
			window.addEventListener("beforeunload", this._unload);
			this.bind_palette();
			this.render();
		}

		destroy() {
			this.alive = false;
			window.removeEventListener("keydown", this._keys, true);
			window.removeEventListener("beforeunload", this._unload);
			clearTimeout(this._commit_t);
		}

		set_tab(tab) {
			this.flush_pending();
			this.tab = tab;
			this.render();
		}

		render() {
			this.$main.find(".wss-designer").attr("data-tab", this.tab);
			this.$main.find(".wss-tab").each((_, el) => el.classList.toggle("is-active", el.dataset.tab === this.tab));
			this.render_palette();
			this.render_stage();
			this.render_inspector();
			this.update_chrome();
		}

		render_stage() {
			({ layout: () => this.render_layout_stage(), sidebar: () => this.render_sidebar_stage(), dock: () => this.render_dock_stage(), settings: () => this.render_settings_stage() })[this.tab]();
		}

		render_inspector() {
			this.$inspector.empty();
			this.fg = null;
			({ layout: () => this.inspect_layout(), sidebar: () => this.inspect_sidebar(), dock: () => this.inspect_dock(), settings: () => this.inspect_settings() })[this.tab]();
		}

		update_chrome() {
			if (!this.alive) return;
			const dirty = this.last !== this.saved || !!this._commit_t;
			const colors = { Draft: "gray", Published: "green", Modified: "orange" };
			if (dirty) this.page.set_indicator(__("Not Saved"), "orange");
			else this.page.set_indicator(__(this.status), colors[this.status] || "gray");
			this.$main.find("[data-cmd=undo]").prop("disabled", !this.history.length && !this._commit_t);
			this.$main.find("[data-cmd=redo]").prop("disabled", !this.future.length);
			this.$main.find("[data-device]").each((_, el) => el.classList.toggle("is-active", el.dataset.device === this.device));
			const issues = this.issues();
			const errors = issues.filter((i) => i.level === "error").length;
			this.$main.find(".wss-save-state").html(
				errors
					? `<span class="wss-issue-pill is-error">${ico("alert", 13)} ${__("{0} to fix", [errors])}</span>`
					: issues.length
					? `<span class="wss-issue-pill">${ico("info", 13)} ${__("{0} notes", [issues.length])}</span>`
					: `<span class="wss-issue-pill is-ok">${ico("check", 13)} ${__("Ready")}</span>`
			);
		}

		mark_unsaved() {
			this.page.set_indicator(__("Not Saved"), "orange");
		}

		// -------------------------------------------------------------- keyboard
		on_key(e) {
			if (!this.alive || frappe.get_route()[0] !== "workspace-studio") return;
			if ($(".modal.show").length) return;
			const mod = e.ctrlKey || e.metaKey;
			const key = (e.key || "").toLowerCase();
			if (mod && key === "s") {
				e.preventDefault();
				e.stopPropagation();
				this.save();
				return;
			}
			const t = e.target;
			if (["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) || t.isContentEditable) return;
			if (mod && key === "z") {
				e.preventDefault();
				e.stopPropagation();
				e.shiftKey ? this.redo() : this.undo();
			} else if (mod && key === "y") {
				e.preventDefault();
				e.stopPropagation();
				this.redo();
			} else if (mod && key === "d") {
				e.preventDefault();
				e.stopPropagation();
				this.duplicate_selected();
			} else if (key === "delete" || key === "backspace") {
				if (this.sel[this.tab]) {
					e.preventDefault();
					this.delete_selected();
				}
			} else if (key === "escape") {
				this.select(this.tab, null);
			} else if (e.altKey && ["arrowup", "arrowleft", "arrowdown", "arrowright"].includes(key)) {
				e.preventDefault();
				this.nudge_selected(key === "arrowup" || key === "arrowleft" ? -1 : 1);
			}
		}

		shortcuts_help() {
			const rows = [
				["Ctrl/Cmd + S", __("Save")],
				["Ctrl/Cmd + Z", __("Undo")],
				["Ctrl/Cmd + Shift + Z / Y", __("Redo")],
				["Ctrl/Cmd + D", __("Duplicate selected")],
				["Delete", __("Remove selected")],
				["Alt + Arrow", __("Move selected earlier / later")],
				["Esc", __("Clear selection")],
			];
			frappe.msgprint({
				title: __("Keyboard Shortcuts"),
				message: `<table class="table table-sm">${rows.map(([k, v]) => `<tr><td><kbd>${k}</kbd></td><td>${v}</td></tr>`).join("")}</table>`,
			});
		}

		select(tab, id) {
			this.sel[tab] = id;
			if (tab !== this.tab) return;
			if (tab === "layout") this.$stage.find(".wss-block").each((_, el) => el.classList.toggle("is-selected", el.dataset.id === id));
			if (tab === "sidebar") this.$stage.find(".wss-sb-row").each((_, el) => el.classList.toggle("is-selected", el.dataset.id === id));
			if (tab === "dock") this.$stage.find(".wss-dock-item, .wss-dock-sep").each((_, el) => el.classList.toggle("is-selected", el.dataset.id === id));
			this.render_inspector();
		}

		duplicate_selected() {
			const id = this.sel[this.tab];
			if (!id) return;
			if (this.tab === "layout") this.duplicate_block(id);
			else if (this.tab === "dock") {
				const items = this.state.dock.items;
				const i = items.findIndex((x) => x.id === id);
				if (i < 0) return;
				const c = Object.assign(clone(items[i]), { id: uid() });
				items.splice(i + 1, 0, c);
				this.after_change("dock", c.id);
			} else if (this.tab === "sidebar") {
				const path = this.sb_find(id);
				if (!path) return;
				const c = clone(this.sb_get(path));
				const reid = (n) => {
					n.id = uid();
					(n.children || []).forEach(reid);
				};
				reid(c);
				this.sb_container(path).splice(path[path.length - 1] + 1, 0, c);
				this.after_change("sidebar", c.id);
			}
		}

		delete_selected() {
			const id = this.sel[this.tab];
			if (!id) return;
			if (this.tab === "layout") this.delete_block(id);
			else if (this.tab === "dock") {
				this.state.dock.items = this.state.dock.items.filter((x) => x.id !== id);
				this.after_change("dock", null);
			} else if (this.tab === "sidebar") {
				const path = this.sb_find(id);
				if (path) this.sb_container(path).splice(path[path.length - 1], 1);
				this.after_change("sidebar", null);
			}
		}

		nudge_selected(dir) {
			const id = this.sel[this.tab];
			if (!id) return;
			let arr;
			if (this.tab === "layout") arr = this.blocks;
			else if (this.tab === "dock") arr = this.state.dock.items;
			else if (this.tab === "sidebar") {
				const path = this.sb_find(id);
				arr = path && this.sb_container(path);
			}
			if (!arr) return;
			const i = arr.findIndex((x) => x.id === id);
			const j = i + dir;
			if (i < 0 || j < 0 || j >= arr.length) return;
			[arr[i], arr[j]] = [arr[j], arr[i]];
			this.after_change(this.tab, id);
		}

		after_change(tab, select_id) {
			this.sel[tab] = select_id;
			this.commit();
			this.render_stage();
			this.render_inspector();
		}

		// -------------------------------------------------------------- palette
		bind_palette() {
			this.$palette
				.on("dragstart", ".wss-pal-item", (e) => {
					const el = e.currentTarget;
					this.drag = { source: "palette", kind: el.dataset.kind, type: el.dataset.type };
					e.originalEvent.dataTransfer.effectAllowed = "copy";
					e.originalEvent.dataTransfer.setData("text/plain", el.dataset.type);
					this.$stage.addClass("is-receiving");
				})
				.on("dragend", ".wss-pal-item", () => this.end_drag())
				.on("click", ".wss-pal-item", (e) => this.palette_click(e.currentTarget.dataset))
				.on("click", "[data-pal-cmd]", (e) => this.palette_cmd(e.currentTarget.dataset.palCmd));
		}

		pal_item(kind, type, icon, label, desc) {
			return `<div class="wss-pal-item" draggable="true" data-kind="${kind}" data-type="${type}" title="${__("Drag onto the canvas, or click to add")}">
				<span class="wss-pal-ico">${ico(icon, 16)}</span>
				<span class="wss-pal-text"><span class="wss-pal-label">${label}</span><span class="wss-pal-desc">${desc || ""}</span></span>
			</div>`;
		}

		render_palette() {
			const $p = this.$palette.empty();
			if (this.tab === "layout") {
				Object.entries(GROUPS).forEach(([g, gl]) => {
					$p.append(`<div class="wss-pal-group">${gl}</div>`);
					Object.entries(BLOCKS)
						.filter(([, d]) => d.group === g)
						.forEach(([t, d]) => $p.append(this.pal_item("block", t, d.icon, d.label, d.desc)));
				});
				$p.append(`<div class="wss-pal-group">${__("Patterns")}</div>`);
				Object.entries(PATTERNS).forEach(([k, d]) => $p.append(this.pal_item("pattern", k, d.icon, d.label, d.desc)));
			} else if (this.tab === "sidebar") {
				$p.append(`<div class="wss-pal-group">${__("Menu items")}</div>`);
				Object.entries(SIDEBAR_TYPES).forEach(([t, d]) => $p.append(this.pal_item("sidebar", t, d.icon, d.label, d.desc)));
				$p.append(`<div class="wss-pal-group">${__("Quick build")}</div>
					<button class="wss-pal-btn" data-pal-cmd="sb-generate">${ico("wand", 15)} ${__("Generate from layout")}</button>
					<button class="wss-pal-btn" data-pal-cmd="sb-bulk">${ico("doctype", 15)} ${__("Add DocType links...")}</button>
					<button class="wss-pal-btn" data-pal-cmd="sb-clear">${ico("trash", 15)} ${__("Clear menu")}</button>`);
			} else if (this.tab === "dock") {
				const native = this.hints.native_navigation !== false;
				$p.append(`<div class="wss-pal-group">${native ? __("v16 Dock") : __("Dock")}</div>`);
				Object.entries(DOCK_TYPES)
					.filter(([, d]) => d.native)
					.forEach(([t, d]) => $p.append(this.pal_item("dock", t, d.icon, d.label, native ? __("Native Dock entry") : "")));
				$p.append(`<div class="wss-pal-group">${native ? __("Quick Launch bar") : __("More")}</div>`);
				Object.entries(DOCK_TYPES)
					.filter(([, d]) => !d.native)
					.forEach(([t, d]) => $p.append(this.pal_item("dock", t, d.icon, d.label, native ? __("Studio bar") : "")));
				$p.append(this.pal_item("dock", "separator", "separator", __("Separator"), native ? __("Studio bar") : ""));
				$p.append(`<div class="wss-pal-group">${__("Quick build")}</div>
					<button class="wss-pal-btn" data-pal-cmd="dock-from-layout">${ico("wand", 15)} ${__("Add layout shortcuts")}</button>
					<button class="wss-pal-btn" data-pal-cmd="dock-clear">${ico("trash", 15)} ${__("Clear dock")}</button>`);
			} else {
				const s = this.state;
				const links = s.sidebar.items.reduce((n, it) => n + (it.type === "section" ? it.children.length : it.type === "link" ? 1 : 0), 0);
				$p.append(`<div class="wss-pal-group">${__("Overview")}</div>
					<div class="wss-stat"><span>${ico("workspace", 15)} ${__("Layout blocks")}</span><b>${s.layout.blocks.length}</b></div>
					<div class="wss-stat"><span>${ico("sidebar", 15)} ${__("Sidebar links")}</span><b>${links}</b></div>
					<div class="wss-stat"><span>${ico("dock", 15)} ${__("Dock items")}</span><b>${s.dock.items.filter((i) => i.type === "item").length}</b></div>
					<div class="wss-stat"><span>${ico("users", 15)} ${__("Audience rules")}</span><b>${this.targets.length}</b></div>
					<div class="wss-pal-group">${__("Version")}</div>
					<div class="wss-stat"><span>${__("Published version")}</span><b>${this.data.version || 0}</b></div>`);
			}
		}

		palette_click(ds) {
			if (ds.kind === "block" || ds.kind === "pattern") {
				const sel = this.blocks.findIndex((b) => b.id === this.sel.layout);
				const at = sel >= 0 ? sel + 1 : this.blocks.length;
				const items = ds.kind === "block" ? [new_block(ds.type)] : PATTERNS[ds.type].make();
				this.blocks.splice(at, 0, ...items);
				this.after_change("layout", items[0].id);
				this.scroll_to(items[0].id);
			} else if (ds.kind === "sidebar") {
				const item = new_sidebar_item(ds.type);
				const path = this.sel.sidebar && this.sb_find(this.sel.sidebar);
				const target = path && this.sb_get(path);
				if (target && target.type === "section" && item.type !== "section") target.children.push(item);
				else if (path && !(path.length === 2 && item.type === "section")) this.sb_container(path).splice(path[path.length - 1] + 1, 0, item);
				else this.state.sidebar.items.push(item);
				this.after_change("sidebar", item.id);
			} else if (ds.kind === "dock") {
				const item = new_dock_item(ds.type);
				const i = this.state.dock.items.findIndex((x) => x.id === this.sel.dock);
				this.state.dock.items.splice(i >= 0 ? i + 1 : this.state.dock.items.length, 0, item);
				this.after_change("dock", item.id);
			}
		}

		palette_cmd(cmd) {
			if (cmd === "sb-generate") {
				const gen = this.sidebar_from_layout();
				if (!gen.length) return frappe.show_alert({ message: __("Add shortcuts or link cards to the layout first."), indicator: "orange" });
				const apply = () => {
					this.state.sidebar.items = gen;
					this.after_change("sidebar", null);
				};
				if (this.state.sidebar.items.length) frappe.confirm(__("Replace the current sidebar menu with one generated from the layout?"), apply);
				else apply();
			} else if (cmd === "sb-bulk") {
				this.bulk_doctypes((list) => {
					const sec = new_sidebar_item("section");
					sec.label = __("Lists");
					sec.children = list.map((dt) => Object.assign(new_sidebar_item("link"), { label: __(dt), link_to: dt }));
					this.state.sidebar.items.push(sec);
					this.after_change("sidebar", sec.id);
				});
			} else if (cmd === "sb-clear") {
				frappe.confirm(__("Remove every sidebar item?"), () => {
					this.state.sidebar.items = [];
					this.after_change("sidebar", null);
				});
			} else if (cmd === "dock-from-layout") {
				const added = [];
				this.blocks
					.filter((b) => b.type === "shortcut" && has_target(b))
					.forEach((b) => {
						const d = b.data;
						const type = d.type === "URL" ? "URL" : ["DocType", "Report", "Page", "Dashboard"].includes(d.type) ? d.type : "DocType";
						const item = new_dock_item(type);
						Object.assign(item, { label: d.label || d.link_to, link_to: d.link_to, url: d.url, doc_view: d.doc_view || "", color: SHORTCUT_COLORS[d.color] || item.color });
						added.push(item);
					});
				if (!added.length) return frappe.show_alert({ message: __("The layout has no shortcuts with a target."), indicator: "orange" });
				this.state.dock.items.push(...added);
				this.after_change("dock", added[0].id);
			} else if (cmd === "dock-clear") {
				frappe.confirm(__("Remove every Dock item?"), () => {
					this.state.dock.items = [];
					this.after_change("dock", null);
				});
			}
		}

		bulk_doctypes(cb) {
			const d = new frappe.ui.Dialog({
				title: __("Add DocType links"),
				fields: [{ fieldtype: "MultiSelectPills", fieldname: "doctypes", label: __("DocTypes"), reqd: 1, get_data: (txt) => frappe.db.get_link_options("DocType", txt, { istable: 0 }) }],
				primary_action_label: __("Add"),
				primary_action: (v) => {
					d.hide();
					if (v.doctypes && v.doctypes.length) cb(v.doctypes);
				},
			});
			d.show();
		}

		sidebar_from_layout() {
			const items = [];
			const sc = this.blocks.filter((b) => b.type === "shortcut" && has_target(b));
			if (sc.length) {
				const sec = new_sidebar_item("section");
				sec.label = __("Shortcuts");
				sec.children = sc.map((b) => {
					const d = b.data;
					return Object.assign(new_sidebar_item("link"), {
						label: d.label || d.link_to,
						link_type: ["DocType", "Report", "Page", "Dashboard", "URL"].includes(d.type) ? d.type : "DocType",
						link_to: d.link_to,
						url: d.url,
					});
				});
				items.push(sec);
			}
			this.blocks
				.filter((b) => b.type === "card")
				.forEach((b) => {
					const kids = (b.data.links || []).filter((l) => l.link_to).map((l) => Object.assign(new_sidebar_item("link"), { label: l.label || l.link_to, link_type: l.link_type, link_to: l.link_to }));
					if (kids.length) {
						const sec = new_sidebar_item("section");
						sec.label = b.data.label;
						sec.children = kids;
						items.push(sec);
					}
				});
			return items;
		}

		end_drag() {
			this.drag = null;
			this.drop_index = null;
			this.sb_target = null;
			this.$stage.removeClass("is-receiving");
			this.$stage.find(".is-dragging").removeClass("is-dragging");
			this.$stage.find(".wss-drop-indicator").removeClass("is-visible");
			this.$stage.find(".drop-before, .drop-after, .drop-inside, .drop-inside-start, .is-drop-end").removeClass("drop-before drop-after drop-inside drop-inside-start is-drop-end");
		}

		scroll_to(id) {
			const el = this.$stage.find(`[data-id="${id}"]`)[0];
			if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
		}

		// ============================================================== LAYOUT
		span_for(col) {
			if (this.device === "mobile") return 12;
			if (this.device === "tablet") return col > 6 ? 12 : 6;
			return col;
		}

		render_layout_stage() {
			const p = this.props;
			this.$stage.html(`
				<div class="wss-canvas-wrap">
					<div class="wss-device wss-device--${this.device}">
						<div class="wss-ws-head">
							<span class="wss-ws-icon">${ficon(p.icon, "md") || ico("workspace", 18)}</span>
							<span class="wss-ws-title">${esc(p.workspace_title || this.data.title)}</span>
							<span class="wss-ws-badge">${esc(__(p.publish_mode || ""))}</span>
						</div>
						<div class="wss-grid"></div>
						<div class="wss-drop-indicator"></div>
					</div>
				</div>`);
			this.$grid = this.$stage.find(".wss-grid");
			this.$device = this.$stage.find(".wss-device");
			if (!this.blocks.length) {
				this.$grid.append(`<div class="wss-empty">${ico("layers", 28)}<div>${__("Drag blocks here from the left panel")}</div><div class="text-muted small">${__("Shortcuts, link cards, charts, number cards, quick lists and more.")}</div></div>`);
			}
			this.blocks.forEach((b) => this.$grid.append(this.block_el(b)));
			this.bind_grid();
		}

		block_el(b) {
			const def = BLOCKS[b.type];
			const ok = has_target(b);
			const $el = $(`
				<div class="wss-block wss-block--${b.type} ${this.sel.layout === b.id ? "is-selected" : ""} ${ok ? "" : "is-incomplete"}"
					draggable="true" data-id="${b.id}" style="grid-column: span ${this.span_for(b.col)}" tabindex="0">
					<div class="wss-block-bar">
						<span class="wss-block-grip">${ico("grip", 14)}</span>
						<span class="wss-block-kind">${def.label}</span>
						${b.roles.length ? `<span class="wss-block-lock" title="${esc(b.roles.join(", "))}">${ico("lock", 12)} ${b.roles.length}</span>` : ""}
						${ok ? "" : `<span class="wss-block-warn" title="${__("No target set")}">${ico("alert", 12)}</span>`}
						<span class="wss-block-col">${b.col}/12</span>
						<span class="wss-block-actions">
							<button data-act="dup" title="${__("Duplicate")}">${ico("copy", 13)}</button>
							<button data-act="del" title="${__("Remove")}">${ico("trash", 13)}</button>
						</span>
					</div>
					<div class="wss-block-body">${this.block_preview(b)}</div>
					<div class="wss-resize" title="${__("Drag to resize")}"></div>
				</div>`);
			return $el;
		}

		block_preview(b) {
			const d = b.data;
			const ph = (t) => `<span class="wss-ph">${t}</span>`;
			switch (b.type) {
				case "header":
					return `<div class="wss-pv-header wss-pv-${(d.size || "Large").toLowerCase()}">${esc(d.text) || ph(__("Header text"))}</div>`;
				case "paragraph":
					return `<div class="wss-pv-para">${esc(d.text).replace(/\n/g, "<br>") || ph(__("Write some guidance for users..."))}</div>`;
				case "spacer":
					return `<div class="wss-pv-spacer"></div>`;
				case "shortcut": {
					const target = d.type === "URL" ? d.url : d.link_to;
					const view = d.doc_view ? ` · ${esc(__(d.doc_view))}` : "";
					return `<div class="wss-pv-shortcut">
						<span class="wss-pv-swatch" style="background:${SHORTCUT_COLORS[d.color] || SHORTCUT_COLORS.Grey}"></span>
						<div class="wss-pv-main">
							<div class="wss-pv-title">${esc(d.label || d.link_to) || ph(__("Shortcut"))}</div>
							<div class="wss-pv-sub">${esc(__(d.type))} · ${esc(target) || ph(__("no target"))}${view}</div>
						</div>
						${d.filters && d.filters.length ? `<span class="wss-pv-count">${esc(d.format ? d.format.replace("{}", "12") : "12")}</span>` : ""}
						<span class="wss-pv-arrow">${ico("external", 14)}</span>
					</div>`;
				}
				case "card": {
					const links = d.links || [];
					return `<div class="wss-pv-card">
						<div class="wss-pv-title">${esc(d.label)}</div>
						${links.length ? links.slice(0, 6).map((l) => `<div class="wss-pv-link">${ico(LINK_ICON[l.link_type] || "link", 13)}<span>${esc(l.label || l.link_to) || ph(__("link"))}</span>${l.onboard ? `<span class="wss-pv-tag">${__("onboard")}</span>` : ""}</div>`).join("") : `<div class="wss-pv-link">${ph(__("Add links in the panel on the right"))}</div>`}
						${links.length > 6 ? `<div class="wss-pv-more">+${links.length - 6} ${__("more")}</div>` : ""}
					</div>`;
				}
				case "chart": {
					const h = hash(d.chart_name || b.id);
					const bars = Array.from({ length: 12 }, (_, i) => 20 + ((h >> (i % 24)) % 60) + (i % 3) * 6);
					return `<div class="wss-pv-chart">
						<div class="wss-pv-title">${esc(d.label || d.chart_name) || ph(__("Dashboard Chart"))}</div>
						<div class="wss-pv-bars">${bars.map((v) => `<span style="height:${Math.min(v, 100)}%"></span>`).join("")}</div>
					</div>`;
				}
				case "number_card":
					return `<div class="wss-pv-number">
						<div class="wss-pv-sub">${esc(d.label || d.number_card_name) || ph(__("Number Card"))}</div>
						<div class="wss-pv-big">${d.number_card_name ? (hash(d.number_card_name) % 900) + 100 : "—"}</div>
						<div class="wss-pv-trend">${ico("chart", 12)} ${__("live value")}</div>
					</div>`;
				case "quick_list":
					return `<div class="wss-pv-ql">
						<div class="wss-pv-title">${esc(d.label || d.document_type) || ph(__("Quick List"))}</div>
						${[1, 2, 3].map(() => `<div class="wss-pv-row"><span></span><span></span></div>`).join("")}
						${d.filters && d.filters.length ? `<div class="wss-pv-sub">${ico("filter", 12)} ${esc(filter_text(d.filters).join(" · "))}</div>` : ""}
					</div>`;
				case "custom_block":
					return `<div class="wss-pv-custom">${ico("code", 18)}<div><div class="wss-pv-title">${esc(d.label || d.custom_block_name) || ph(__("Custom HTML Block"))}</div><div class="wss-pv-sub">${__("Rendered from Custom HTML Block")}</div></div></div>`;
			}
			return "";
		}

		refresh_block(id) {
			const b = this.blocks.find((x) => x.id === id);
			const $old = this.$stage.find(`.wss-block[data-id="${id}"]`);
			if (!b || !$old.length) return;
			$old.replaceWith(this.block_el(b));
			this.update_chrome();
		}

		bind_grid() {
			const $dev = this.$device;
			this.$grid
				.on("click", ".wss-block", (e) => {
					if ($(e.target).closest("[data-act], .wss-resize").length) return;
					this.select("layout", e.currentTarget.dataset.id);
				})
				.on("keydown", ".wss-block", (e) => {
					if (e.key === "Enter") this.select("layout", e.currentTarget.dataset.id);
				})
				.on("click", "[data-act]", (e) => {
					e.stopPropagation();
					const id = $(e.currentTarget).closest(".wss-block").attr("data-id");
					if (e.currentTarget.dataset.act === "dup") this.duplicate_block(id);
					else this.delete_block(id);
				})
				.on("dragstart", ".wss-block", (e) => {
					const el = e.currentTarget;
					this.drag = { source: "grid", id: el.dataset.id };
					e.originalEvent.dataTransfer.effectAllowed = "move";
					e.originalEvent.dataTransfer.setData("text/plain", el.dataset.id);
					setTimeout(() => el.classList.add("is-dragging"), 0);
				})
				.on("dragend", ".wss-block", () => this.end_drag())
				.on("mousedown", ".wss-resize", (e) => this.start_resize(e));
			$dev.on("dragover", (e) => this.grid_dragover(e))
				.on("drop", (e) => this.grid_drop(e))
				.on("dragleave", (e) => {
					if (!$dev[0].contains(e.originalEvent.relatedTarget)) $dev.find(".wss-drop-indicator").removeClass("is-visible");
				});
			$dev.on("click", (e) => {
				if (e.target === $dev[0] || e.target === this.$grid[0]) this.select("layout", null);
			});
		}

		grid_dragover(e) {
			const drag = this.drag;
			if (!drag || !(drag.source === "grid" || (drag.source === "palette" && (drag.kind === "block" || drag.kind === "pattern")))) return;
			e.preventDefault();
			const oe = e.originalEvent;
			oe.dataTransfer.dropEffect = drag.source === "grid" ? "move" : "copy";
			const devRect = this.$device[0].getBoundingClientRect();
			const gridRect = this.$grid[0].getBoundingClientRect();
			const $ind = this.$device.find(".wss-drop-indicator");
			const target = oe.target.closest && oe.target.closest(".wss-block");
			let index = this.blocks.length;
			let box;
			if (target && target.classList.contains("is-dragging")) return;
			if (target) {
				const i = this.blocks.findIndex((b) => b.id === target.dataset.id);
				const r = target.getBoundingClientRect();
				const full = r.width > gridRect.width * 0.85;
				const before = full ? oe.clientY < r.top + r.height / 2 : oe.clientX < r.left + r.width / 2;
				index = before ? i : i + 1;
				box = full
					? { left: r.left - devRect.left, top: (before ? r.top - 7 : r.bottom + 4) - devRect.top, width: r.width, height: 3 }
					: { left: (before ? r.left - 8 : r.right + 5) - devRect.left, top: r.top - devRect.top, width: 3, height: r.height };
			} else {
				const els = this.$grid.find(".wss-block:not(.is-dragging)");
				const last = els[els.length - 1];
				if (last) {
					const r = last.getBoundingClientRect();
					if (oe.clientY < r.top) {
						// above everything: insert at start
						const first = els[0].getBoundingClientRect();
						index = 0;
						box = { left: first.left - devRect.left, top: first.top - 7 - devRect.top, width: gridRect.width, height: 3 };
					} else {
						box = { left: gridRect.left - devRect.left, top: Math.max(r.bottom, gridRect.bottom - 6) + 6 - devRect.top, width: gridRect.width, height: 3 };
					}
				} else {
					box = { left: gridRect.left - devRect.left, top: gridRect.top - devRect.top, width: gridRect.width, height: Math.max(gridRect.height, 80) };
				}
			}
			this.drop_index = index;
			$ind.addClass("is-visible").css({ left: box.left, top: box.top, width: box.width, height: box.height });
		}

		grid_drop(e) {
			const drag = this.drag;
			if (!drag) return;
			e.preventDefault();
			let index = this.drop_index == null ? this.blocks.length : this.drop_index;
			let select_id = null;
			if (drag.source === "palette") {
				const items = drag.kind === "pattern" ? PATTERNS[drag.type].make() : [new_block(drag.type)];
				this.blocks.splice(index, 0, ...items);
				select_id = items[0].id;
			} else if (drag.source === "grid") {
				const from = this.blocks.findIndex((b) => b.id === drag.id);
				if (from < 0) return this.end_drag();
				if (from < index) index--;
				if (from !== index) {
					const [moved] = this.blocks.splice(from, 1);
					this.blocks.splice(index, 0, moved);
				}
				select_id = drag.id;
			}
			this.end_drag();
			this.after_change("layout", select_id);
		}

		start_resize(e) {
			e.preventDefault();
			e.stopPropagation();
			if (this.device !== "desktop") {
				frappe.show_alert({ message: __("Switch to the desktop preview to resize blocks."), indicator: "orange" });
				return;
			}
			const el = $(e.currentTarget).closest(".wss-block")[0];
			const b = this.blocks.find((x) => x.id === el.dataset.id);
			const grid = this.$grid[0];
			const gap = parseFloat(getComputedStyle(grid).columnGap) || 16;
			const col_w = (grid.getBoundingClientRect().width + gap) / 12;
			const left = el.getBoundingClientRect().left;
			el.draggable = false;
			document.body.classList.add("wss-resizing");
			this.select("layout", b.id);
			const move = (ev) => {
				const col = clamp(Math.round((ev.clientX - left + gap) / col_w), 1, 12);
				if (col !== b.col) {
					b.col = col;
					el.style.gridColumn = `span ${col}`;
					$(el).find(".wss-block-col").text(`${col}/12`);
					this.sync_width_control(b);
				}
			};
			const up = () => {
				document.removeEventListener("mousemove", move);
				document.removeEventListener("mouseup", up);
				document.body.classList.remove("wss-resizing");
				el.draggable = true;
				this.commit();
			};
			document.addEventListener("mousemove", move);
			document.addEventListener("mouseup", up);
		}

		duplicate_block(id) {
			const i = this.blocks.findIndex((b) => b.id === id);
			if (i < 0) return;
			const c = clone(this.blocks[i]);
			c.id = uid();
			(c.data.links || []).forEach((l) => (l.id = uid()));
			this.blocks.splice(i + 1, 0, c);
			this.after_change("layout", c.id);
		}

		delete_block(id) {
			this.state.layout.blocks = this.blocks.filter((b) => b.id !== id);
			this.after_change("layout", this.sel.layout === id ? null : this.sel.layout);
			frappe.show_alert({ message: __("Block removed — Ctrl+Z to undo"), indicator: "blue" }, 3);
		}

		// -------------------------------------------------------------- layout inspector
		inspect_layout() {
			const b = this.blocks.find((x) => x.id === this.sel.layout);
			const $i = this.$inspector;
			if (!b) {
				$i.html(`
					<div class="wss-ins-head">${ico("workspace", 18)}<div><div class="wss-ins-title">${__("Layout")}</div><div class="wss-ins-sub">${__("{0} blocks", [this.blocks.length])}</div></div></div>
					<div class="wss-ins-empty">
						<p>${__("Select a block to edit its properties.")}</p>
						<ul>
							<li>${__("Drag blocks from the left onto the canvas.")}</li>
							<li>${__("Drag a block to reorder it; drag its right edge to resize.")}</li>
							<li>${__("Each block can be limited to specific roles.")}</li>
						</ul>
					</div>
					<div class="wss-ins-issues"></div>`);
				this.render_issue_list($i.find(".wss-ins-issues"), this.issues().filter((x) => x.tab === "layout"));
				return;
			}
			const def = BLOCKS[b.type];
			$i.html(`
				<div class="wss-ins-head">${ico(def.icon, 18)}<div><div class="wss-ins-title">${def.label}</div><div class="wss-ins-sub">${esc(def.desc)}</div></div></div>
				<div class="wss-ins-section">
					<div class="wss-ins-label">${__("Width")}</div>
					<div class="wss-width">
						${[3, 4, 6, 8, 12].map((c) => `<button data-col="${c}">${c === 12 ? __("Full") : c === 6 ? "½" : c === 4 ? "⅓" : c === 3 ? "¼" : "⅔"}</button>`).join("")}
					</div>
					<div class="wss-width-step">
						<button data-step="-1">${ico("minus", 13)}</button>
						<div class="wss-width-bar"><span></span></div>
						<button data-step="1">${ico("plus", 13)}</button>
						<b class="wss-width-val"></b>
					</div>
				</div>
				<div class="wss-ins-section wss-ins-form"></div>
				<div class="wss-ins-extra"></div>
				<div class="wss-ins-section">
					<div class="wss-ins-label">${ico("eye", 13)} ${__("Visibility")}</div>
					<div class="wss-vis-form"></div>
					${this.props.publish_mode && this.props.publish_mode.startsWith("Shared") && b.roles.length ? `<div class="wss-note">${ico("info", 13)} ${__("Role visibility is enforced in Personal publish mode. In Shared mode the block is shown to everyone with access to the workspace.")}</div>` : ""}
				</div>
				<div class="wss-ins-foot">
					<button class="btn btn-sm btn-default" data-foot="dup">${ico("copy", 13)} ${__("Duplicate")}</button>
					<button class="btn btn-sm btn-default text-danger" data-foot="del">${ico("trash", 13)} ${__("Remove")}</button>
				</div>`);
			this.sync_width_control(b);
			$i.find("[data-col]").on("click", (e) => this.set_col(b, +e.currentTarget.dataset.col));
			$i.find("[data-step]").on("click", (e) => this.set_col(b, clamp(b.col + +e.currentTarget.dataset.step, 1, 12)));
			$i.find("[data-foot=dup]").on("click", () => this.duplicate_block(b.id));
			$i.find("[data-foot=del]").on("click", () => this.delete_block(b.id));

			const fields = this.block_fields(b);
			if (fields.length) {
				this.fg = make_form($i.find(".wss-ins-form"), fields, b.data, (field, value, fg, live) => this.on_block_change(b, field, value, fg, live));
			} else {
				$i.find(".wss-ins-form").html(`<div class="text-muted small">${__("A spacer has no settings — just width and visibility.")}</div>`);
			}
			make_form($i.find(".wss-vis-form"), [roles_df()], { roles: b.roles }, (f, v) => {
				b.roles = v || [];
				this.refresh_block(b.id);
				this.commit_soon();
			});
			this.render_block_extra(b);
		}

		set_col(b, col) {
			b.col = col;
			this.refresh_block(b.id);
			this.sync_width_control(b);
			this.commit();
		}

		sync_width_control(b) {
			const $i = this.$inspector;
			$i.find("[data-col]").each((_, el) => el.classList.toggle("is-active", +el.dataset.col === b.col));
			$i.find(".wss-width-bar span").css("width", (b.col / 12) * 100 + "%");
			$i.find(".wss-width-val").text(`${b.col}/12`);
		}

		block_fields(b) {
			const d = b.data;
			const color_opts = Object.keys(SHORTCUT_COLORS).map((c) => ({ value: c, label: __(c) }));
			switch (b.type) {
				case "header":
					return [
						{ fieldtype: "Data", fieldname: "text", label: __("Text"), reqd: 1 },
						{ fieldtype: "Select", fieldname: "size", label: __("Size"), options: [{ value: "Large", label: __("Large") }, { value: "Medium", label: __("Medium") }, { value: "Small", label: __("Small") }] },
					];
				case "paragraph":
					return [{ fieldtype: "Small Text", fieldname: "text", label: __("Text") }];
				case "shortcut": {
					const f = [
						{ fieldtype: "Select", fieldname: "type", label: __("Opens"), options: ["DocType", "Report", "Page", "Dashboard", "URL"].map((v) => ({ value: v, label: __(v) })) },
					];
					if (d.type === "URL") f.push({ fieldtype: "Data", fieldname: "url", label: __("URL"), options: "URL", reqd: 1 });
					else f.push({ fieldtype: "Link", fieldname: "link_to", label: __(d.type), options: d.type, reqd: 1, get_query: d.type === "DocType" ? () => ({ filters: { istable: 0 } }) : null });
					if (d.type === "DocType")
						f.push({ fieldtype: "Select", fieldname: "doc_view", label: __("View"), options: [{ value: "", label: __("Default") }].concat(["List", "Report Builder", "Dashboard", "Tree", "New", "Calendar", "Kanban"].map((v) => ({ value: v, label: __(v) }))) });
					f.push(
						{ fieldtype: "Data", fieldname: "label", label: __("Label") },
						{ fieldtype: "Select", fieldname: "color", label: __("Color"), options: color_opts }
					);
					if (d.type === "DocType") f.push({ fieldtype: "Data", fieldname: "format", label: __("Count format"), description: __("e.g. '{} Open'. Shown when a count filter is set.") });
					return f;
				}
				case "card":
					return [{ fieldtype: "Data", fieldname: "label", label: __("Card title"), reqd: 1 }];
				case "chart":
					return [
						{ fieldtype: "Link", fieldname: "chart_name", label: __("Dashboard Chart"), options: "Dashboard Chart", reqd: 1 },
						{ fieldtype: "Data", fieldname: "label", label: __("Label") },
					];
				case "number_card":
					return [
						{ fieldtype: "Link", fieldname: "number_card_name", label: __("Number Card"), options: "Number Card", reqd: 1 },
						{ fieldtype: "Data", fieldname: "label", label: __("Label") },
					];
				case "quick_list":
					return [
						{ fieldtype: "Link", fieldname: "document_type", label: __("DocType"), options: "DocType", reqd: 1, get_query: () => ({ filters: { istable: 0, issingle: 0 } }) },
						{ fieldtype: "Data", fieldname: "label", label: __("Label") },
					];
				case "custom_block":
					return [
						{ fieldtype: "Link", fieldname: "custom_block_name", label: __("Custom HTML Block"), options: "Custom HTML Block", reqd: 1 },
						{ fieldtype: "Data", fieldname: "label", label: __("Label") },
					];
			}
			return [];
		}

		on_block_change(b, field, value, fg, live) {
			const d = b.data;
			d[field] = value == null ? "" : value;
			const target_fields = ["link_to", "chart_name", "number_card_name", "document_type", "custom_block_name"];
			if (!live && target_fields.includes(field) && value && !d.label) {
				d.label = __(value);
				if (fg.fields_dict.label) fg.fields_dict.label.set_input(d.label);
			}
			if (field === "type") {
				d.link_to = "";
				d.url = "";
				d.doc_view = "";
				d.filters = [];
				this.refresh_block(b.id);
				this.commit();
				this.render_inspector();
				return;
			}
			if (field === "link_to" || field === "document_type") {
				if (d.filters && d.filters.length) d.filters = [];
				this.render_block_extra(b);
			}
			this.refresh_block(b.id);
			this.commit_soon();
		}

		render_block_extra(b) {
			const $x = this.$inspector.find(".wss-ins-extra").off().empty();
			const d = b.data;
			if (b.type === "card") return this.render_card_links(b, $x);
			const filter_doctype = b.type === "shortcut" && d.type === "DocType" ? d.link_to : b.type === "quick_list" ? d.document_type : null;
			if (b.type === "shortcut" && d.type !== "DocType") return;
			if (!["shortcut", "quick_list"].includes(b.type)) return;
			const chips = filter_text(d.filters);
			$x.html(`<div class="wss-ins-section">
				<div class="wss-ins-label">${ico("filter", 13)} ${b.type === "shortcut" ? __("Count filter") : __("List filter")}</div>
				<div class="wss-chips">${chips.length ? chips.map((c) => `<span class="wss-chip">${esc(c)}</span>`).join("") : `<span class="text-muted small">${b.type === "shortcut" ? __("No count shown") : __("All records")}</span>`}</div>
				<div class="wss-row-btns">
					<button class="btn btn-xs btn-default" data-x="edit" ${filter_doctype ? "" : "disabled"}>${ico("filter", 12)} ${__("Edit filters")}</button>
					${chips.length ? `<button class="btn btn-xs btn-default" data-x="clear">${__("Clear")}</button>` : ""}
				</div>
				${filter_doctype ? "" : `<div class="text-muted small">${__("Choose a DocType first.")}</div>`}
			</div>`);
			$x.find("[data-x=edit]").on("click", () =>
				this.filter_dialog(filter_doctype, d.filters || [], (filters) => {
					d.filters = filters;
					this.refresh_block(b.id);
					this.render_block_extra(b);
					this.commit();
				})
			);
			$x.find("[data-x=clear]").on("click", () => {
				d.filters = [];
				this.refresh_block(b.id);
				this.render_block_extra(b);
				this.commit();
			});
		}

		filter_dialog(doctype, current, cb) {
			const d = new frappe.ui.Dialog({
				title: __("Filters for {0}", [__(doctype)]),
				size: "large",
				fields: [{ fieldtype: "HTML", fieldname: "area" }],
				primary_action_label: __("Apply"),
				primary_action: () => {
					const filters = (group.get_filters() || []).map((f) => [f[1], f[2], f[3]]);
					d.hide();
					cb(filters);
				},
			});
			const $area = d.get_field("area").$wrapper.addClass("wss-filter-area");
			let group;
			frappe.model.with_doctype(doctype, () => {
				group = new frappe.ui.FilterGroup({ parent: $area, doctype, on_change: () => {} });
				group.add_filters_to_filter_group(current.map((f) => [doctype, f[0], f[1], f[2]]));
				if (!current.length && group.add_filter) setTimeout(() => $area.find(".add-filter").trigger("click"), 50);
			});
			d.show();
		}

		render_card_links(b, $x) {
			const links = b.data.links;
			$x.html(`<div class="wss-ins-section">
				<div class="wss-ins-label">${ico("link", 13)} ${__("Links")} <span class="wss-count">${links.length}</span></div>
				<div class="wss-links">${links
					.map(
						(l, i) => `<div class="wss-link-row" draggable="true" data-i="${i}">
							<span class="wss-block-grip">${ico("grip", 13)}</span>
							<span class="wss-link-type" title="${esc(__(l.link_type))}">${ico(LINK_ICON[l.link_type] || "link", 13)}</span>
							<span class="wss-link-text"><span>${esc(l.label || l.link_to) || `<i class="text-muted">${__("unset")}</i>`}</span><small>${esc(l.link_to)}</small></span>
							<button data-l="edit" title="${__("Edit")}">${ico("edit", 13)}</button>
							<button data-l="del" title="${__("Remove")}">${ico("x", 13)}</button>
						</div>`
					)
					.join("") || `<div class="text-muted small">${__("No links yet.")}</div>`}</div>
				<div class="wss-row-btns">
					<button class="btn btn-xs btn-default" data-l="add">${ico("plus", 12)} ${__("Link")}</button>
					<button class="btn btn-xs btn-default" data-l="bulk">${ico("doctype", 12)} ${__("DocTypes...")}</button>
				</div>
			</div>`);
			const changed = () => {
				this.refresh_block(b.id);
				this.render_block_extra(b);
				this.commit();
			};
			$x.find("[data-l=add]").on("click", () => this.link_dialog(null, (l) => { links.push(l); changed(); }));
			$x.find("[data-l=bulk]").on("click", () =>
				this.bulk_doctypes((list) => {
					list.forEach((dt) => links.push({ id: uid(), label: __(dt), link_type: "DocType", link_to: dt, onboard: 0, dependencies: [] }));
					changed();
				})
			);
			$x.on("click", "[data-l=edit]", (e) => {
				const i = +$(e.currentTarget).closest(".wss-link-row").attr("data-i");
				this.link_dialog(links[i], (l) => { links[i] = l; changed(); });
			});
			$x.on("click", "[data-l=del]", (e) => {
				links.splice(+$(e.currentTarget).closest(".wss-link-row").attr("data-i"), 1);
				changed();
			});
			// reorder links by drag
			let from = null;
			$x.on("dragstart", ".wss-link-row", (e) => {
				from = +e.currentTarget.dataset.i;
				e.originalEvent.dataTransfer.effectAllowed = "move";
				e.originalEvent.dataTransfer.setData("text/plain", String(from));
				e.stopPropagation();
			})
				.on("dragover", ".wss-link-row", (e) => {
					if (from == null) return;
					e.preventDefault();
					const r = e.currentTarget.getBoundingClientRect();
					$x.find(".wss-link-row").removeClass("drop-before drop-after");
					e.currentTarget.classList.add(e.originalEvent.clientY < r.top + r.height / 2 ? "drop-before" : "drop-after");
				})
				.on("drop", ".wss-link-row", (e) => {
					if (from == null) return;
					e.preventDefault();
					let to = +e.currentTarget.dataset.i + (e.currentTarget.classList.contains("drop-after") ? 1 : 0);
					if (from < to) to--;
					const [m] = links.splice(from, 1);
					links.splice(to, 0, m);
					from = null;
					changed();
				})
				.on("dragend", ".wss-link-row", () => {
					from = null;
					$x.find(".wss-link-row").removeClass("drop-before drop-after");
				});
		}

		link_dialog(link, cb) {
			const l = Object.assign({ id: uid(), label: "", link_type: "DocType", link_to: "", onboard: 0, dependencies: [] }, link ? clone(link) : {});
			const d = new frappe.ui.Dialog({
				title: link ? __("Edit Link") : __("Add Link"),
				fields: [
					{ fieldtype: "Select", fieldname: "link_type", label: __("Type"), options: ["DocType", "Report", "Page"].map((v) => ({ value: v, label: __(v) })), default: l.link_type },
					{ fieldtype: "Dynamic Link", fieldname: "link_to", label: __("Opens"), options: "link_type", reqd: 1, default: l.link_to, get_options: () => d.get_value("link_type") },
					{ fieldtype: "Data", fieldname: "label", label: __("Label"), default: l.label },
					{ fieldtype: "Check", fieldname: "onboard", label: __("Highlight for onboarding"), default: l.onboard },
					{ fieldtype: "MultiSelectPills", fieldname: "dependencies", label: __("Depends on DocTypes"), description: __("Shown as 'create these first' hints."), get_data: (txt) => frappe.db.get_link_options("DocType", txt) },
				],
				primary_action_label: link ? __("Update") : __("Add"),
				primary_action: (v) => {
					d.hide();
					cb(Object.assign(l, { link_type: v.link_type, link_to: v.link_to, label: v.label || __(v.link_to), onboard: v.onboard ? 1 : 0, dependencies: v.dependencies || [] }));
				},
			});
			d.fields_dict.link_type.df.onchange = () => d.set_value("link_to", "");
			d.show();
			if (l.dependencies && l.dependencies.length) d.set_value("dependencies", l.dependencies);
		}

		// ============================================================== SIDEBAR
		sb_get(path) {
			const items = this.state.sidebar.items;
			return path.length === 1 ? items[path[0]] : items[path[0]] && items[path[0]].children[path[1]];
		}

		sb_container(path) {
			return path.length === 1 ? this.state.sidebar.items : this.state.sidebar.items[path[0]].children;
		}

		sb_find(ref) {
			const id = typeof ref === "string" ? ref : ref && ref.id;
			const items = this.state.sidebar.items;
			for (let i = 0; i < items.length; i++) {
				if (items[i].id === id) return [i];
				const kids = items[i].children || [];
				for (let j = 0; j < kids.length; j++) if (kids[j].id === id) return [i, j];
			}
			return null;
		}

		render_sidebar_stage() {
			const p = this.props;
			const no_doctype = this.hints.has_sidebar_doctype === false;
			this.$stage.html(`
				<div class="wss-sb-stage">
					${no_doctype ? `<div class="wss-banner">${ico("info", 15)} ${__("This site has no Workspace Sidebar DocType (pre-v16). The menu is saved with the studio but is only published on v16.")}</div>` : ""}
					${this.hints.native_navigation !== false ? `<div class="wss-banner is-info">${ico("info", 15)} ${__("Published as the sidebar of this studio's module: site-wide in Shared mode, per user in Personal mode.")}</div>` : ""}
					<div class="wss-sb-frame">
						<div class="wss-sb-mock">
							<div class="wss-sb-head"><span class="wss-sb-head-ico">${ficon(p.icon, "md") || ico("workspace", 16)}</span><span>${esc(p.workspace_title || this.data.title)}</span></div>
							<div class="wss-sb-list"></div>
							<div class="wss-sb-end">${ico("plus", 13)} ${__("Drop here to add at the end")}</div>
						</div>
						<div class="wss-sb-ghost">
							<div class="wss-ghost-title"></div>
							<div class="wss-ghost-row"><span></span><span></span><span></span><span></span></div>
							<div class="wss-ghost-row wss-ghost-tall"><span></span><span></span></div>
							<div class="wss-sb-note">${__("Drag sections and links on the left. Drop a link onto the middle of a section to nest it.")}</div>
						</div>
					</div>
				</div>`);
			const $list = this.$stage.find(".wss-sb-list");
			const items = this.state.sidebar.items;
			if (this.hints.native_navigation !== false) {
				$list.append(`<div class="wss-sb-row wss-sb-link is-auto" title="${__("Added automatically so the module opens on this workspace")}"><span class="wss-sb-ico">${ficon(p.icon) || ico("workspace", 14)}</span><span class="wss-sb-label">${esc(p.workspace_title || this.data.title)}</span><span class="wss-sb-type">${__("Workspace · auto")}</span></div>`);
			}
			if (!items.length) $list.append(`<div class="wss-sb-blank">${__("Empty menu — drag a Section or Link here, or use 'Generate from layout'.")}</div>`);
			items.forEach((it, i) => {
				$list.append(this.sb_row(it, [i]));
				if (it.type === "section" && !this.sb_collapsed.has(it.id)) {
					it.children.forEach((c, j) => $list.append(this.sb_row(c, [i, j])));
					if (!it.children.length) $list.append(`<div class="wss-sb-empty" data-path="${i}">${__("Drop links into this section")}</div>`);
				}
			});
			this.bind_sidebar();
		}

		sb_row(it, path) {
			const sel = this.sel.sidebar === it.id ? "is-selected" : "";
			const depth = path.length - 1;
			const lock = it.roles && it.roles.length ? `<span class="wss-block-lock" title="${esc(it.roles.join(", "))}">${ico("lock", 11)}</span>` : "";
			const acts = `<span class="wss-sb-acts"><button data-sb="dup" title="${__("Duplicate")}">${ico("copy", 12)}</button><button data-sb="del" title="${__("Remove")}">${ico("trash", 12)}</button></span>`;
			if (it.type === "section") {
				const open = !this.sb_collapsed.has(it.id);
				return `<div class="wss-sb-row wss-sb-section ${sel}" draggable="true" data-path="${path.join(".")}" data-id="${it.id}">
					<span class="wss-block-grip">${ico("grip", 13)}</span>
					<button class="wss-sb-caret ${open ? "is-open" : ""}" data-sb="toggle">${ico("caret", 12)}</button>
					${it.icon ? `<span class="wss-sb-ico">${ficon(it.icon)}</span>` : ""}
					<span class="wss-sb-label">${esc(it.label)}</span>${lock}
					<span class="wss-sb-count">${it.children.length}</span>${acts}
				</div>`;
			}
			if (it.type === "spacer") {
				return `<div class="wss-sb-row wss-sb-spacer depth-${depth} ${sel}" draggable="true" data-path="${path.join(".")}" data-id="${it.id}">
					<span class="wss-block-grip">${ico("grip", 13)}</span><span class="wss-sb-line"></span>${acts}
				</div>`;
			}
			const ok = it.link_type === "URL" ? !!it.url : !!it.link_to;
			return `<div class="wss-sb-row wss-sb-link depth-${depth} ${sel} ${ok ? "" : "is-incomplete"}" draggable="true" data-path="${path.join(".")}" data-id="${it.id}">
				<span class="wss-block-grip">${ico("grip", 13)}</span>
				<span class="wss-sb-ico">${ficon(it.icon) || ico(LINK_ICON[it.link_type] || "link", 14)}</span>
				<span class="wss-sb-label">${esc(it.label)}</span>${lock}
				${ok ? "" : `<span class="wss-block-warn">${ico("alert", 11)}</span>`}
				<span class="wss-sb-type">${esc(__(it.link_type))}</span>${acts}
			</div>`;
		}

		bind_sidebar() {
			const $mock = this.$stage.find(".wss-sb-mock");
			$mock
				.on("click", ".wss-sb-row", (e) => {
					const act = $(e.target).closest("[data-sb]").attr("data-sb");
					const id = e.currentTarget.dataset.id;
					if (act === "toggle") {
						this.sb_collapsed.has(id) ? this.sb_collapsed.delete(id) : this.sb_collapsed.add(id);
						return this.render_sidebar_stage();
					}
					if (act === "dup") {
						this.sel.sidebar = id;
						return this.duplicate_selected();
					}
					if (act === "del") {
						this.sel.sidebar = id;
						return this.delete_selected();
					}
					this.select("sidebar", id);
				})
				.on("dragstart", ".wss-sb-row", (e) => {
					const el = e.currentTarget;
					this.drag = { source: "sidebar", id: el.dataset.id };
					e.originalEvent.dataTransfer.effectAllowed = "move";
					e.originalEvent.dataTransfer.setData("text/plain", el.dataset.id);
					setTimeout(() => el.classList.add("is-dragging"), 0);
				})
				.on("dragend", ".wss-sb-row", () => this.end_drag())
				.on("dragover", (e) => this.sb_dragover(e))
				.on("drop", (e) => this.sb_drop(e));
			this.$stage.find(".wss-sb-ghost").on("click", () => this.select("sidebar", null));
		}

		sb_drag_type() {
			if (!this.drag) return null;
			if (this.drag.source === "palette" && this.drag.kind === "sidebar") return this.drag.type;
			if (this.drag.source === "sidebar") {
				const p = this.sb_find(this.drag.id);
				return p && this.sb_get(p).type;
			}
			return null;
		}

		sb_dragover(e) {
			const dtype = this.sb_drag_type();
			if (!dtype) return;
			e.preventDefault();
			const oe = e.originalEvent;
			oe.dataTransfer.dropEffect = this.drag.source === "palette" ? "copy" : "move";
			const $mock = this.$stage.find(".wss-sb-mock");
			$mock.find(".drop-before, .drop-after, .drop-inside, .drop-inside-start, .is-drop-end").removeClass("drop-before drop-after drop-inside drop-inside-start is-drop-end");
			const row = oe.target.closest && oe.target.closest(".wss-sb-row, .wss-sb-empty");
			if (!row || row.classList.contains("is-dragging")) {
				this.sb_target = { zone: "end" };
				$mock.find(".wss-sb-end").addClass("is-drop-end");
				return;
			}
			let path = row.dataset.path.split(".").map(Number);
			let zone;
			let mark = row;
			if (row.classList.contains("wss-sb-empty")) {
				zone = dtype === "section" ? "after" : "inside";
				mark = $mock.find(`.wss-sb-row[data-path="${path[0]}"]`)[0] || row;
				if (zone === "inside") mark = row;
			} else {
				const item = this.sb_get(path);
				const r = row.getBoundingClientRect();
				const rel = (oe.clientY - r.top) / r.height;
				if (item.type === "section" && dtype !== "section" && rel > 0.3 && rel < 0.7) zone = "inside";
				else if (path.length === 2 && dtype === "section") {
					const parent_children = this.sb_get([path[0]]).children.length;
					zone = path[1] === 0 && rel < 0.5 ? "before" : "after";
					if (zone === "after" && path[1] < parent_children - 1) zone = "before-next";
					path = [path[0]];
					mark = $mock.find(`.wss-sb-row[data-path="${path[0]}"]`)[0];
					if (zone === "before-next") zone = "after";
				} else zone = rel < 0.5 ? "before" : "after";
				if (zone === "after" && item.type === "section" && dtype !== "section" && !this.sb_collapsed.has(item.id) && item.children.length) zone = "inside-start";
			}
			this.sb_target = { path, zone, ref: this.sb_get(path) };
			if (mark) mark.classList.add("drop-" + zone);
		}

		sb_drop(e) {
			const dtype = this.sb_drag_type();
			if (!dtype) return;
			e.preventDefault();
			const t = this.sb_target || { zone: "end" };
			const items = this.state.sidebar.items;
			let moving;
			if (this.drag.source === "palette") moving = new_sidebar_item(dtype);
			else {
				const from = this.sb_find(this.drag.id);
				moving = this.sb_get(from);
				if (t.ref === moving) return this.end_drag();
				if (moving.type === "section" && t.ref && (moving.children || []).includes(t.ref)) return this.end_drag();
				this.sb_container(from).splice(from[from.length - 1], 1);
			}
			const tp = t.ref ? this.sb_find(t.ref) : null;
			if (!tp || t.zone === "end") items.push(moving);
			else if (t.zone === "inside" && moving.type !== "section") t.ref.children.push(moving);
			else if (t.zone === "inside-start" && moving.type !== "section") t.ref.children.unshift(moving);
			else {
				const arr = this.sb_container(tp);
				arr.splice(tp[tp.length - 1] + (t.zone === "before" ? 0 : 1), 0, moving);
			}
			this.end_drag();
			this.after_change("sidebar", moving.id);
		}

		inspect_sidebar() {
			const $i = this.$inspector;
			const path = this.sel.sidebar && this.sb_find(this.sel.sidebar);
			const it = path && this.sb_get(path);
			if (!it) {
				$i.html(`
					<div class="wss-ins-head">${ico("sidebar", 18)}<div><div class="wss-ins-title">${__("Sidebar Menu")}</div><div class="wss-ins-sub">${__("The left-hand menu for this workspace")}</div></div></div>
					<div class="wss-ins-empty"><p>${__("Select an item to edit it.")}</p>
					<ul><li>${__("Sections group links and can be collapsible.")}</li><li>${__("Links open DocTypes, reports, pages, other workspaces, dashboards or URLs.")}</li><li>${__("Items limited to roles are hidden from other users in Personal mode.")}</li></ul></div>
					<div class="wss-ins-issues"></div>`);
				this.render_issue_list($i.find(".wss-ins-issues"), this.issues().filter((x) => x.tab === "sidebar"));
				return;
			}
			const meta = SIDEBAR_TYPES[it.type];
			$i.html(`
				<div class="wss-ins-head">${ico(meta.icon, 18)}<div><div class="wss-ins-title">${meta.label}</div><div class="wss-ins-sub">${path.length === 2 ? __("Inside a section") : __("Top level")}</div></div></div>
				<div class="wss-ins-section wss-ins-form"></div>
				<div class="wss-ins-foot">
					<button class="btn btn-sm btn-default" data-foot="dup">${ico("copy", 13)} ${__("Duplicate")}</button>
					<button class="btn btn-sm btn-default text-danger" data-foot="del">${ico("trash", 13)} ${__("Remove")}</button>
				</div>`);
			$i.find("[data-foot=dup]").on("click", () => this.duplicate_selected());
			$i.find("[data-foot=del]").on("click", () => this.delete_selected());
			let fields = [];
			if (it.type === "section") {
				fields = [
					{ fieldtype: "Data", fieldname: "label", label: __("Label"), reqd: 1 },
					{ fieldtype: "Icon", fieldname: "icon", label: __("Icon") },
					{ fieldtype: "Check", fieldname: "collapsible", label: __("Collapsible") },
					{ fieldtype: "Check", fieldname: "keep_closed", label: __("Start collapsed") },
					roles_df(),
				];
			} else if (it.type === "link") {
				fields = [
					{ fieldtype: "Select", fieldname: "link_type", label: __("Opens"), options: ["DocType", "Report", "Page", "Workspace", "Dashboard", "URL"].map((v) => ({ value: v, label: __(v) })) },
					it.link_type === "URL"
						? { fieldtype: "Data", fieldname: "url", label: __("URL"), options: "URL", reqd: 1 }
						: { fieldtype: "Link", fieldname: "link_to", label: __(it.link_type), options: it.link_type, reqd: 1, get_query: it.link_type === "DocType" ? () => ({ filters: { istable: 0 } }) : null },
					{ fieldtype: "Data", fieldname: "label", label: __("Label"), reqd: 1 },
					{ fieldtype: "Icon", fieldname: "icon", label: __("Icon") },
					roles_df(),
				];
			} else {
				$i.find(".wss-ins-form").html(`<div class="text-muted small">${__("A divider draws a thin line between items. It has no settings.")}</div>`);
				return;
			}
			this.fg = make_form($i.find(".wss-ins-form"), fields, it, (field, value, fg, live) => {
				if (field === "roles") it.roles = value || [];
				else it[field] = value == null ? "" : value;
				if (field === "link_type") {
					it.link_to = "";
					it.url = "";
					this.commit();
					this.render_sidebar_stage();
					return this.render_inspector();
				}
				if (field === "link_to" && value && !live && (!it.label || it.label === __("New link"))) {
					it.label = __(value);
					fg.fields_dict.label && fg.fields_dict.label.set_input(it.label);
				}
				const $row = this.$stage.find(`.wss-sb-row[data-id="${it.id}"]`);
				$row.replaceWith(this.sb_row(it, path));
				this.commit_soon();
			});
		}

		// ============================================================== DOCK
		render_dock_stage() {
			const d = this.state.dock;
			const classes = window.wss && wss.dock && wss.dock.classes ? wss.dock.classes(d) : "wss-dock";
			this.$stage.html(`
				<div class="wss-dock-stage">
					<div class="wss-desk wss-desk--${d.position} ${d.enabled ? "" : "is-off"}">
						<div class="wss-desk-chrome"><i></i><i></i><i></i><span>/desk/${esc(frappe.router ? frappe.router.slug(this.props.workspace_title || this.data.title) : "")}</span></div>
						<div class="wss-desk-body">
							<div class="wss-ghost-title"></div>
							<div class="wss-ghost-row"><span></span><span></span><span></span><span></span></div>
							<div class="wss-ghost-row wss-ghost-tall"><span></span><span></span></div>
						</div>
						<nav class="${classes} wss-dock--preview"></nav>
						${d.enabled ? "" : `<div class="wss-desk-off">${__("Dock is turned off for this studio")}</div>`}
					</div>
					<div class="wss-dock-help">${ico("info", 13)} ${
						this.hints.native_navigation !== false
							? ((this.props.publish_mode || "").startsWith("Personal")
									? __("Personal mode: every user in the audience gets their own Dock layer with a pin to their personal copy of this workspace.")
									: __("Shared mode: with no audience, one site-wide entry pins the shared workspace. With an audience, each audience user gets their own Dock layer pinned to it, so nobody else's Dock changes. Administrator and System Managers keep their native Dock unless added as individual users.")) +
								" " + __("A Home button on every rail opens the user's default workspace.") +
								" " + __("Module, Workspace and URL entries go to the native v16 Dock; entries with a dashed ring (lists, new documents, reports, pages, dashboards) appear in the Studio Quick Launch bar.")
							: __("Drag to reorder. Items the user has no permission for are hidden automatically.")
					}</div>
				</div>`);
			const $dock = this.$stage.find(".wss-dock--preview");
			const html = (it) =>
				window.wss && wss.dock && wss.dock.item_html
					? wss.dock.item_html(it, `draggable="true" data-id="${it.id}"`)
					: `<button class="wss-dock-item" draggable="true" data-id="${it.id}">${esc(it.label || "|")}</button>`;
			const native = this.hints.native_navigation !== false;
			if (native) {
				const home = { type: "item", label: this.props.workspace_title || this.data.title, icon: this.props.icon, color: "#4f46e5" };
				const $home = $(window.wss && wss.dock && wss.dock.item_html ? wss.dock.item_html(home) : `<button class="wss-dock-item">${esc(home.label)}</button>`);
				const personal = (this.props.publish_mode || "").startsWith("Personal");
				$home.addClass("is-auto").attr("title", personal ? __("Added automatically: each user's personal copy of this workspace") : __("Added automatically: the shared workspace"));
				$dock.append($home);
			}
			if (!d.items.length) $dock.append(`<div class="wss-dock-empty">${__("Drag items here")}</div>`);
			d.items.forEach((it) => {
				const $el = $(html(it));
				if (native && it.type === "separator") $el.addClass("is-ql");
				if (native && it.type === "item" && !is_native_dock(it)) $el.addClass("is-ql").attr("title", it.label + " · " + __("Quick Launch bar"));
				if (this.sel.dock === it.id) $el.addClass("is-selected");
				if (it.type === "item" && !(it.link_type === "URL" ? it.url : it.link_to)) $el.addClass("is-incomplete");
				$dock.append($el);
			});
			if (d.magnify && wss.dock && wss.dock.bind_magnify) wss.dock.bind_magnify($dock, d.position);
			this.bind_dock();
		}

		bind_dock() {
			const $desk = this.$stage.find(".wss-desk");
			const $dock = this.$stage.find(".wss-dock--preview");
			const vertical = ["left", "right"].includes(this.state.dock.position);
			$dock
				.on("click", "[data-id]", (e) => {
					e.stopPropagation();
					this.select("dock", e.currentTarget.dataset.id);
				})
				.on("dragstart", "[data-id]", (e) => {
					this.drag = { source: "dock", id: e.currentTarget.dataset.id };
					e.originalEvent.dataTransfer.effectAllowed = "move";
					e.originalEvent.dataTransfer.setData("text/plain", e.currentTarget.dataset.id);
					const el = e.currentTarget;
					setTimeout(() => el.classList.add("is-dragging"), 0);
				})
				.on("dragend", "[data-id]", () => this.end_drag());
			$desk
				.on("click", () => this.select("dock", null))
				.on("dragover", (e) => {
					if (!this.drag || !(this.drag.source === "dock" || (this.drag.source === "palette" && this.drag.kind === "dock"))) return;
					e.preventDefault();
					const oe = e.originalEvent;
					const els = $dock.find("[data-id]:not(.is-dragging)").toArray();
					$dock.find(".drop-before, .drop-after").removeClass("drop-before drop-after");
					$dock.removeClass("is-drop-end");
					let index = this.state.dock.items.length;
					for (const el of els) {
						const r = el.getBoundingClientRect();
						const mid = vertical ? r.top + r.height / 2 : r.left + r.width / 2;
						if ((vertical ? oe.clientY : oe.clientX) < mid) {
							index = this.state.dock.items.findIndex((x) => x.id === el.dataset.id);
							el.classList.add("drop-before");
							break;
						}
					}
					if (index === this.state.dock.items.length) $dock.addClass("is-drop-end");
					this.drop_index = index;
				})
				.on("drop", (e) => {
					if (!this.drag) return;
					e.preventDefault();
					const items = this.state.dock.items;
					let index = this.drop_index == null ? items.length : this.drop_index;
					let id;
					if (this.drag.source === "palette") {
						const it = new_dock_item(this.drag.type);
						items.splice(index, 0, it);
						id = it.id;
					} else {
						const from = items.findIndex((x) => x.id === this.drag.id);
						if (from < index) index--;
						const [m] = items.splice(from, 1);
						items.splice(index, 0, m);
						id = m.id;
					}
					this.end_drag();
					$dock.removeClass("is-drop-end");
					this.after_change("dock", id);
				});
		}

		inspect_dock() {
			const $i = this.$inspector;
			const d = this.state.dock;
			const it = d.items.find((x) => x.id === this.sel.dock);
			if (!it) {
				$i.html(`
					<div class="wss-ins-head">${ico("dock", 18)}<div><div class="wss-ins-title">${__("Dock")}</div><div class="wss-ins-sub">${__("Quick-launch bar shown on every desk page")}</div></div></div>
					<div class="wss-ins-section wss-ins-form"></div>
					${this.hints.dock_enabled === 0 ? `<div class="wss-note">${ico("alert", 13)} ${__("The Dock is switched off globally in Workspace Studio Settings.")}</div>` : ""}
					<div class="wss-ins-issues"></div>`);
				const opt = (arr) => arr.map(([v, l]) => ({ value: v, label: l }));
				if (this.hints.native_navigation !== false) {
					$i.find(".wss-ins-form").before(`<div class="wss-ins-section"><div class="wss-ins-label">${__("v16 Dock")}</div><div data-form="native"></div></div>`);
					const brand = { frappe: "thinkNXG", erpnext: "thinkNXG ERP", thinknxg_workspace_studio: __("Workspaces (custom Dock app)") };
					const apps = (this.hints.installed_apps || []).map((a) => ({ value: a, label: brand[a] || a }));
					make_form(
						$i.find("[data-form=native]"),
						[
							{ fieldtype: "Check", fieldname: "enable_dock", label: __("Publish to the Dock") },
							{
								fieldtype: "Select",
								fieldname: "dock_app",
								label: __("App rail"),
								options: [{ value: "", label: __("Default (thinkNXG ERP, else thinkNXG)") }].concat(apps),
								description: __("Pick 'Workspaces' to give studios their own app, tile and rail instead of sharing thinkNXG ERP's."),
							},
							{
								fieldtype: "Select",
								fieldname: "dock_mode",
								label: __("Mode"),
								options: [
									{ value: "Add to the app's Dock", label: __("Add to the existing rail") },
									{ value: "Replace the app's Dock", label: __("Replace the rail with these entries") },
								],
								description: __("Add keeps every native entry (studio entries go after thinkNXG ERP's, so the thinkNXG ERP tile still opens thinkNXG ERP). Replace applies to audience users only; everyone else keeps the native rail."),
							},
							{
								fieldtype: "Check",
								fieldname: "create_desktop_icon",
								label: __("Add a desktop icon for the Workspaces app"),
								depends_on: "eval:doc.dock_app=='thinknxg_workspace_studio'",
							},
						],
						this.props,
						(field, value) => {
							this.props[field] = value;
							this.commit_soon();
						}
					);
					const ql = d.items.filter((x) => x.type === "item" && !is_native_dock(x));
					const nat = d.items.filter((x) => is_native_dock(x));
					$i.find(".wss-ins-form").before(`<div class="wss-ins-label" style="padding:12px 16px 0">${__("Quick Launch bar")}</div>
						<div class="wss-note" style="margin:6px 16px 0">${ico(ql.length ? "info" : "alert", 13)} ${
							ql.length
								? __("{0} item(s) go to the Quick Launch bar; {1} to the native Dock.", [ql.length, nat.length])
								: __("The Quick Launch bar is empty, so it is not shown. Drag DocType List, New Document, Report, Page or Dashboard items onto the Dock to fill it; Module, Workspace and URL items go to the native v16 Dock.")
						}</div>`);
				}
				make_form(
					$i.find(".wss-ins-form"),
					[
						{ fieldtype: "Check", fieldname: "enabled", label: __("Show the Quick Launch bar") },
						{ fieldtype: "Select", fieldname: "position", label: __("Position"), options: opt([["bottom", __("Bottom")], ["left", __("Left")], ["right", __("Right")]]) },
						{ fieldtype: "Select", fieldname: "size", label: __("Icon size"), options: opt([["small", __("Small")], ["medium", __("Medium")], ["large", __("Large")]]) },
						{ fieldtype: "Select", fieldname: "style", label: __("Style"), options: opt([["glass", __("Frosted glass")], ["solid", __("Solid")], ["minimal", __("Minimal")]]) },
						{ fieldtype: "Check", fieldname: "magnify", label: __("Magnify on hover") },
						{ fieldtype: "Check", fieldname: "show_labels", label: __("Always show labels") },
					],
					d,
					(field, value) => {
						d[field] = ["enabled", "magnify", "show_labels"].includes(field) ? (value ? 1 : 0) : value;
						this.render_dock_stage();
						this.commit();
					}
				);
				this.render_issue_list($i.find(".wss-ins-issues"), this.issues().filter((x) => x.tab === "dock"));
				return;
			}
			if (it.type === "separator") {
				$i.html(`<div class="wss-ins-head">${ico("separator", 18)}<div><div class="wss-ins-title">${__("Separator")}</div></div></div>
					<div class="wss-ins-empty"><p>${__("Separates groups of Dock items.")}</p></div>
					<div class="wss-ins-foot"><button class="btn btn-sm btn-default text-danger" data-foot="del">${ico("trash", 13)} ${__("Remove")}</button></div>`);
				$i.find("[data-foot=del]").on("click", () => this.delete_selected());
				return;
			}
			const type_meta = DOCK_TYPES[it.link_type] || DOCK_TYPES.DocType;
			$i.html(`
				<div class="wss-ins-head"><span class="wss-ins-swatch" style="background:${esc(it.color)}">${ico(type_meta.icon, 15)}</span><div><div class="wss-ins-title">${esc(it.label)}</div><div class="wss-ins-sub">${type_meta.label} · ${this.hints.native_navigation === false ? __("Studio bar") : type_meta.native ? __("v16 Dock") : __("Quick Launch bar")}</div></div></div>
				<div class="wss-ins-section wss-ins-form"></div>
				<div class="wss-ins-section"><div class="wss-ins-label">${__("Quick colors")}</div><div class="wss-swatches">${SWATCHES.map((c) => `<button data-c="${c}" style="background:${c}" class="${c === it.color ? "is-active" : ""}" title="${c}"></button>`).join("")}</div></div>
				<div class="wss-ins-foot">
					<button class="btn btn-sm btn-default" data-foot="dup">${ico("copy", 13)} ${__("Duplicate")}</button>
					<button class="btn btn-sm btn-default text-danger" data-foot="del">${ico("trash", 13)} ${__("Remove")}</button>
				</div>`);
			$i.find("[data-foot=dup]").on("click", () => this.duplicate_selected());
			$i.find("[data-foot=del]").on("click", () => this.delete_selected());
			const target_doctype = { Sidebar: "Module Def", Workspace: "Workspace", DocType: "DocType", New: "DocType", Report: "Report", Page: "Page", Dashboard: "Dashboard" }[it.link_type];
			const fields = [
				{ fieldtype: "Select", fieldname: "link_type", label: __("Opens"), options: Object.entries(DOCK_TYPES).map(([v, m]) => ({ value: v, label: m.label })) },
				it.link_type === "URL"
					? { fieldtype: "Data", fieldname: "url", label: __("URL"), options: "URL", reqd: 1 }
					: { fieldtype: "Link", fieldname: "link_to", label: __(target_doctype), options: target_doctype, reqd: 1, get_query: target_doctype === "DocType" ? () => ({ filters: { istable: 0 } }) : null },
			];
			if (it.link_type === "DocType") fields.push({ fieldtype: "Select", fieldname: "doc_view", label: __("View"), options: [{ value: "", label: __("List") }].concat(["Report Builder", "Dashboard", "Tree", "Calendar", "Kanban"].map((v) => ({ value: v, label: __(v) }))) });
			if (it.link_type === "URL") fields.push({ fieldtype: "Check", fieldname: "new_tab", label: __("Open in new tab") });
			fields.push(
				{ fieldtype: "Data", fieldname: "label", label: __("Label"), reqd: 1 },
				{ fieldtype: "Icon", fieldname: "icon", label: __("Icon"), description: __("Leave empty to show initials (the v16 Dock uses a default icon).") },
				{ fieldtype: "Color", fieldname: "color", label: __("Tile color") },
				roles_df()
			);
			this.fg = make_form($i.find(".wss-ins-form"), fields, it, (field, value, fg, live) => {
				if (field === "roles") it.roles = value || [];
				else if (field === "new_tab") it.new_tab = value ? 1 : 0;
				else it[field] = value == null ? "" : value;
				if (field === "link_type") {
					it.link_to = "";
					it.url = "";
					it.doc_view = "";
					if (!it.color || Object.values(DOCK_TYPES).some((m) => m.color === it.color)) it.color = (DOCK_TYPES[value] || DOCK_TYPES.DocType).color;
					this.commit();
					this.render_dock_stage();
					return this.render_inspector();
				}
				if (field === "link_to" && value && !live && (!it.label || Object.values(DOCK_TYPES).some((m) => m.label === it.label))) {
					it.label = it.link_type === "New" ? __("New {0}", [__(value)]) : __(value);
					fg.fields_dict.label && fg.fields_dict.label.set_input(it.label);
				}
				this.render_dock_stage();
				$i.find(".wss-ins-title").text(it.label);
				$i.find(".wss-ins-swatch").css("background", it.color);
				this.commit_soon();
			});
			$i.find("[data-c]").on("click", (e) => {
				it.color = e.currentTarget.dataset.c;
				this.fg && this.fg.fields_dict.color && this.fg.fields_dict.color.set_input(it.color);
				$i.find("[data-c]").removeClass("is-active");
				e.currentTarget.classList.add("is-active");
				$i.find(".wss-ins-swatch").css("background", it.color);
				this.render_dock_stage();
				this.commit();
			});
		}

		// ============================================================== SETTINGS
		render_settings_stage() {
			const p = this.props;
			this.$stage.html(`
				<div class="wss-settings">
					<section class="wss-panel"><div class="wss-panel-head">${ico("workspace", 16)} ${__("Workspace")}</div><div class="wss-panel-body" data-form="ws"></div></section>
					<section class="wss-panel"><div class="wss-panel-head">${ico("users", 16)} ${__("Audience")}</div>
						<div class="wss-panel-body">
							<div data-form="aud"></div>
							<div class="wss-aud-preview"><button class="btn btn-sm btn-default" data-x="preview">${ico("eye", 13)} ${__("Preview who gets this")}</button>
								<button class="btn btn-sm btn-default" data-x="check">${ico("check", 13)} ${__("Check a user")}</button><div class="wss-aud-result"></div></div>
						</div>
					</section>
					<section class="wss-panel"><div class="wss-panel-head">${ico("upload", 16)} ${__("Publishing")}</div><div class="wss-panel-body" data-form="pub"></div></section>
					<section class="wss-panel"><div class="wss-panel-head">${ico("history", 16)} ${__("Publish history")}</div><div class="wss-panel-body wss-history"></div></section>
				</div>`);
			const on_prop = (field, value) => {
				this.props[field] = value;
				this.commit_soon();
			};
			make_form(
				this.$stage.find("[data-form=ws]"),
				[
					{ fieldtype: "Data", fieldname: "workspace_title", label: __("Workspace Label"), reqd: 1, description: __("Name users see in the desk and sidebar.") },
					{ fieldtype: "Icon", fieldname: "icon", label: __("Icon") },
					{ fieldtype: "Select", fieldname: "indicator_color", label: __("Indicator Color"), options: ["", "Green", "Cyan", "Blue", "Orange", "Yellow", "Gray", "Red", "Pink", "Purple"] },
					{ fieldtype: "Column Break" },
					{ fieldtype: "Link", fieldname: "parent_page", label: __("Parent Workspace"), options: "Workspace" },
					{ fieldtype: "Link", fieldname: "module", label: __("Module"), options: "Module Def", description: __("Leave empty to use 'Custom Workspaces'. Personal copies always go to 'Private'.") },
					{ fieldtype: "Float", fieldname: "sequence_id", label: __("Sequence") },
				],
				p,
				on_prop
			);
			const roles = this.targets.filter((t) => t.target_type === "Role").map((t) => t.role);
			const users = this.targets.filter((t) => t.target_type === "User").map((t) => t.user);
			const aud_fg = make_form(
				this.$stage.find("[data-form=aud]"),
				[
					{ fieldtype: "MultiSelectPills", fieldname: "roles", label: __("Roles"), get_data: (txt) => frappe.db.get_link_options("Role", txt) },
					{ fieldtype: "MultiSelectPills", fieldname: "users", label: __("Individual users"), get_data: (txt) => frappe.db.get_link_options("User", txt, { enabled: 1 }) },
				],
				{ roles, users },
				() => {
					const r = aud_fg.get_value("roles") || [];
					const u = aud_fg.get_value("users") || [];
					this.targets = r.map((role) => ({ target_type: "Role", role })).concat(u.map((user) => ({ target_type: "User", user })));
					this.$stage.find(".wss-aud-result").empty();
					this.commit_soon();
				}
			);
			make_form(
				this.$stage.find("[data-form=pub]"),
				[
					{
						fieldtype: "Select",
						fieldname: "publish_mode",
						label: __("Publish Mode"),
						options: [
							{ value: "Shared (Role-based)", label: __("Shared — one workspace, restricted to the audience roles") },
							{ value: "Personal (Per User)", label: __("Personal — a private copy for every user, with block-level visibility") },
						],
					},
					{ fieldtype: "Int", fieldname: "priority", label: __("Priority"), description: __("Higher wins when several studios match a user (Dock, default workspace).") },
					{ fieldtype: "Check", fieldname: "set_as_default", label: __("Set as the audience's default workspace") },
					{ fieldtype: "Column Break" },
					{ fieldtype: "Check", fieldname: "publish_sidebar", label: __("Publish left sidebar menu") },
					{ fieldtype: "Check", fieldname: "create_desktop_icon", label: __("Add desktop icon for the Workspaces app") },
					{ fieldtype: "Check", fieldname: "enable_dock", label: __("Provide the Dock for this audience") },
					{ fieldtype: "Check", fieldname: "take_over_existing", label: __("Allow replacing an existing workspace with the same label") },
				],
				p,
				(field, value) => {
					this.props[field] = value;
					this.commit_soon();
					this.render_inspector();
				}
			);
			this.$stage.find("[data-x=preview]").on("click", () => this.preview_audience());
			this.$stage.find("[data-x=check]").on("click", () => this.check_user_dialog());
			this.render_history();
		}

		preview_audience() {
			const $r = this.$stage.find(".wss-aud-result").html(`<span class="text-muted small">${__("Checking...")}</span>`);
			const run = () =>
				call("resolve_audience", { name: this.name }).then((res) => {
					if (res.everyone && this.props.publish_mode.startsWith("Shared")) {
						return $r.html(`<div class="wss-note">${ico("info", 13)} ${__("No audience set — a shared workspace is visible to every desk user.")}</div>`);
					}
					$r.html(`<div class="wss-aud-count">${__("{0} user(s)", [res.count])}</div>
						<div class="wss-avatars">${(res.users || []).slice(0, 40).map((u) => `<span class="wss-avatar" title="${esc(u.full_name || u.name)}">${frappe.avatar(u.name, "avatar-small")}</span>`).join("")}${res.count > 40 ? `<span class="text-muted small">+${res.count - 40}</span>` : ""}</div>`);
				});
			if (this.dirty) this.save(true).then(run);
			else run();
		}

		check_user_dialog() {
			const d = new frappe.ui.Dialog({
				title: __("Check what a user sees"),
				size: "large",
				fields: [
					{ fieldtype: "Link", fieldname: "user", label: __("User"), options: "User", reqd: 1, get_query: () => ({ filters: { enabled: 1, user_type: "System User" } }) },
					{ fieldtype: "HTML", fieldname: "result" },
				],
				primary_action_label: __("Check"),
				primary_action: (v) => {
					const $r = d.get_field("result").$wrapper.html(`<div class="text-muted small">${__("Replaying the desk boot as {0}...", [esc(v.user)])}</div>`);
					call("check_user", { name: this.name, user: v.user }).then((res) => {
						const rows = (res.rows || [])
							.map(
								(r, i) => `<div class="wss-diag-row ${r.ok ? "is-ok" : "is-bad"}">
									<span class="wss-diag-ico">${ico(r.ok ? "check" : "alert", 15)}</span>
									<div class="wss-diag-text"><div class="wss-diag-check">${esc(r.check)}</div>${r.detail ? `<div class="wss-diag-detail">${esc(r.detail)}</div>` : ""}
									${r.trace ? `<details><summary>${__("Traceback")}</summary><pre>${esc(r.trace)}</pre></details>` : ""}</div>
								</div>`
							)
							.join("");
						const bad = (res.rows || []).filter((r) => !r.ok).length;
						$r.html(`<div class="wss-diag-head">${bad ? __("{0} check(s) failed", [bad]) : __("Everything this studio publishes reaches this user.")}
							<span class="text-muted small">${esc(res.mode || "")} · ${__("workspace")} ${esc(res.workspace || "-")} · ${__("module")} ${esc(res.module || "-")} · ${__("Dock app")} ${esc(res.app || "-")}</span></div>${rows}`);
					});
				},
			});
			d.show();
		}

		render_history() {
			const logs = this.data.logs || [];
			const $h = this.$stage.find(".wss-history");
			if (!logs.length) return $h.html(`<div class="text-muted small">${__("Not published yet.")}</div>`);
			const colors = { Success: "green", Partial: "orange", Failed: "red" };
			$h.html(`<table class="wss-table"><thead><tr><th>${__("When")}</th><th>${__("Action")}</th><th>${__("Status")}</th><th>${__("By")}</th><th></th></tr></thead><tbody>
				${logs
					.map(
						(l) => `<tr data-log="${esc(l.name)}">
							<td>${comment_when(l.published_on)}</td>
							<td>${esc(__(l.action))}${l.rolled_back ? ` <span class="text-muted small">(${__("rolled back")})</span>` : ""}</td>
							<td><span class="indicator-pill ${colors[l.status] || "gray"}">${esc(__(l.status))}</span></td>
							<td>${esc(frappe.user.full_name(l.published_by))}</td>
							<td class="text-right">
								<button class="btn btn-xs btn-default" data-h="open">${__("View")}</button>
								${l.action !== "Rollback" && !l.rolled_back && l.status !== "Failed" ? `<button class="btn btn-xs btn-default" data-h="rollback">${ico("history", 12)} ${__("Roll back")}</button>` : ""}
							</td>
						</tr>`
					)
					.join("")}
			</tbody></table>`);
			$h.find("[data-h=open]").on("click", (e) => frappe.set_route("Form", "Studio Publish Log", $(e.currentTarget).closest("tr").attr("data-log")));
			$h.find("[data-h=rollback]").on("click", (e) => {
				const log = $(e.currentTarget).closest("tr").attr("data-log");
				frappe.confirm(__("Restore every workspace, sidebar, icon and default touched by {0} to its previous state?", [log]), () =>
					call("rollback", { log_name: log }, __("Rolling back...")).then(() => this.reload_meta(__("Rolled back")))
				);
			});
		}

		inspect_settings() {
			const $i = this.$inspector;
			const idx = this.data.published_index || [];
			$i.html(`
				<div class="wss-ins-head">${ico("check", 18)}<div><div class="wss-ins-title">${__("Pre-publish checklist")}</div><div class="wss-ins-sub">${__("Fix errors before publishing")}</div></div></div>
				<div class="wss-ins-issues"></div>
				<div class="wss-ins-section">
					<div class="wss-ins-label">${__("Currently published")}</div>
					${idx.length ? idx.map((d) => `<div class="wss-pub-doc">${ico(d.doctype === "Workspace" ? "workspace" : d.doctype === "Workspace Sidebar" ? "sidebar" : "desktop", 13)}<a href="/app/${frappe.router.slug(d.doctype)}/${encodeURIComponent(d.name)}">${esc(d.name)}</a><small>${esc(__(d.doctype))}</small></div>`).join("") : `<div class="text-muted small">${__("Nothing published yet.")}</div>`}
				</div>
				<div class="wss-ins-section">
					<div class="wss-ins-label">${__("How publishing works")}</div>
					<div class="wss-ins-empty"><ul>
						<li>${__("Shared: one Workspace restricted to the audience roles. Individual users get a private copy.")}</li>
						<li>${__("Personal: a private Workspace per user, filtered by block visibility.")}</li>
						<li>${__("Every publish is logged with a snapshot so it can be rolled back.")}</li>
					</ul></div>
				</div>`);
			this.render_issue_list($i.find(".wss-ins-issues"), this.issues(), true);
		}

		// -------------------------------------------------------------- issues
		issues() {
			const out = [];
			const s = this.state;
			if (!s.layout.blocks.length) out.push({ level: "error", tab: "layout", msg: __("The layout is empty.") });
			s.layout.blocks.forEach((b) => {
				if (!has_target(b)) out.push({ level: "error", tab: "layout", id: b.id, msg: __("{0} '{1}' has no target — it will be skipped.", [BLOCKS[b.type].label, block_title(b)]) });
				else if (b.type === "card" && b.data.links.some((l) => !l.link_to)) out.push({ level: "warn", tab: "layout", id: b.id, msg: __("Card '{0}' has links without a target.", [b.data.label]) });
			});
			const walk = (items) =>
				items.forEach((it) => {
					if (it.type === "link" && !(it.link_type === "URL" ? it.url : it.link_to)) out.push({ level: "warn", tab: "sidebar", id: it.id, msg: __("Sidebar link '{0}' has no target.", [it.label]) });
					if (it.type === "section") {
						if (!it.children.length) out.push({ level: "warn", tab: "sidebar", id: it.id, msg: __("Sidebar section '{0}' is empty.", [it.label]) });
						walk(it.children);
					}
				});
			walk(s.sidebar.items);
			if (this.props.publish_sidebar && !s.sidebar.items.length) out.push({ level: "warn", tab: "sidebar", msg: __("Publishing the sidebar is on, but the menu is empty.") });
			s.dock.items.forEach((it) => {
				if (it.type === "item" && !(it.link_type === "URL" ? it.url : it.link_to)) out.push({ level: "warn", tab: "dock", id: it.id, msg: __("Dock item '{0}' has no target.", [it.label]) });
			});
			if (!this.targets.length) {
				if ((this.props.publish_mode || "").startsWith("Personal")) out.push({ level: "error", tab: "settings", msg: __("Personal mode needs at least one role or user.") });
				else out.push({ level: "warn", tab: "settings", msg: __("No audience: the shared workspace will be visible to every desk user.") });
			}
			if (!(this.props.workspace_title || "").trim()) out.push({ level: "error", tab: "settings", msg: __("Workspace Label is required.") });
			return out;
		}

		render_issue_list($el, issues, show_ok) {
			if (!issues.length) {
				if (show_ok) $el.html(`<div class="wss-issue is-ok">${ico("check", 14)} ${__("Everything looks good.")}</div>`);
				return;
			}
			$el.html(
				issues
					.map((x, i) => `<button class="wss-issue is-${x.level}" data-i="${i}">${ico(x.level === "error" ? "alert" : "info", 14)}<span>${esc(x.msg)}</span></button>`)
					.join("")
			);
			$el.find("[data-i]").on("click", (e) => {
				const x = issues[+e.currentTarget.dataset.i];
				this.tab = x.tab;
				if (x.id) this.sel[x.tab] = x.id;
				this.render();
				if (x.id) this.scroll_to(x.id);
			});
		}

		// -------------------------------------------------------------- persistence
		save(silent) {
			this.flush_pending(true);
			const snapshot = this.serialize();
			const payload = JSON.stringify({ props: this.props, layout: this.state.layout, sidebar: this.state.sidebar, dock: this.state.dock, targets: this.targets });
			return call("save_studio", { name: this.name, payload, expected_modified: this.modified }, silent ? null : __("Saving...")).then((r) => {
				this.modified = r.modified;
				this.status = r.status;
				this.saved = snapshot;
				if (this.last !== snapshot) this.last = snapshot;
				this.update_chrome();
				if (!silent) frappe.show_alert({ message: __("Saved"), indicator: "green" }, 2);
				return r;
			});
		}

		publish() {
			this.flush_pending(true);
			const errors = this.issues().filter((x) => x.level === "error");
			const go = () => {
				const before = this.dirty ? this.save(true) : Promise.resolve();
				before
					.then(() => call("publish", { name: this.name }, __("Publishing workspace...")))
					.then((res) => {
						this.show_publish_result(res);
						this.reload_meta();
						if (wss.dock && wss.dock.reload) wss.dock.reload();
					})
					.catch(() => this.reload_meta());
			};
			if (errors.length) {
				frappe.confirm(
					`${__("These problems were found:")}<ul>${errors.map((e) => `<li>${esc(e.msg)}</li>`).join("")}</ul>${__("Blocks without a target are skipped. Publish anyway?")}`,
					go
				);
			} else go();
		}

		show_publish_result(res) {
			const colors = { Success: "green", Partial: "orange" };
			const docs = (res.documents || [])
				.map((d) => `<li>${ico(d.action === "removed" ? "trash" : "check", 13)} <b>${esc(__(d.action))}</b> ${esc(__(d.doctype))}: ${d.route ? `<a href="${esc(d.route)}">${esc(d.name)}</a>` : esc(d.name)}</li>`)
				.join("");
			const warns = (res.warnings || []).map((w) => `<li>${esc(w)}</li>`).join("");
			frappe.msgprint({
				title: __("Published version {0}", [res.version]),
				indicator: colors[res.status] || "blue",
				message: `<div class="wss-result"><ul class="wss-result-docs">${docs}</ul>${warns ? `<div class="wss-ins-label">${__("Notes")}</div><ul class="wss-result-warn">${warns}</ul>` : ""}</div>`,
			});
		}

		unpublish() {
			if (!["Published", "Modified"].includes(this.status)) return frappe.msgprint(__("This studio is not published."));
			frappe.confirm(__("Remove every workspace, sidebar and icon this studio published? This can be rolled back from the history."), () =>
				call("unpublish", { name: this.name }, __("Unpublishing...")).then(() => this.reload_meta(__("Unpublished")))
			);
		}

		reload_meta(alert) {
			return call("get_studio", { name: this.name }).then((data) => {
				this.data = Object.assign(this.data, { logs: data.logs, published_index: data.published_index, version: data.version });
				this.status = data.status;
				this.modified = data.modified;
				if (alert) frappe.show_alert({ message: alert, indicator: "green" });
				this.update_chrome();
				if (this.tab === "settings") {
					this.render_history();
					this.render_inspector();
				}
				this.render_palette();
			});
		}
	};
})();
