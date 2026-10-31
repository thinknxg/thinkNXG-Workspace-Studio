// thinkNXG Workspace Studio — desk runtime (Dock)
(function () {
	if (window.wss_runtime_loaded) return;
	window.wss_runtime_loaded = true;

	frappe.provide("wss.dock");

	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));

	wss.dock.initials = function (label) {
		const words = String(label || "?").trim().split(/\s+/);
		return esc(((words[0] || "")[0] || "?") + ((words[1] || "")[0] || "")).toUpperCase();
	};

	wss.dock.icon_html = function (item) {
		if (item.icon && frappe.utils.icon) {
			try {
				return frappe.utils.icon(item.icon, "md");
			} catch (e) {
				/* fall through */
			}
		}
		return `<span class="wss-dock-initials">${wss.dock.initials(item.label)}</span>`;
	};

	wss.dock.item_html = function (item, extra_attrs) {
		if (item.type === "separator") return `<span class="wss-dock-sep" ${extra_attrs || ""}></span>`;
		return `<button type="button" class="wss-dock-item" style="--wss-c:${esc(item.color || "#4f46e5")}"
			title="${esc(item.label)}" aria-label="${esc(item.label)}" ${extra_attrs || ""}>
			<span class="wss-dock-icon">${wss.dock.icon_html(item)}</span>
			<span class="wss-dock-label">${esc(item.label)}</span>
		</button>`;
	};

	wss.dock.classes = function (d) {
		return [
			"wss-dock",
			`wss-dock--${d.position || "bottom"}`,
			`wss-dock--${d.style || "glass"}`,
			`wss-dock--${d.size || "medium"}`,
			d.show_labels ? "wss-dock--labels" : "",
		].join(" ");
	};

	wss.dock.bind_magnify = function ($dock, position) {
		if (!$dock || !$dock.length) return;
		const vertical = position === "left" || position === "right";
		const dock = $dock[0];
		dock.addEventListener("mousemove", (e) => {
			dock.querySelectorAll(".wss-dock-item").forEach((el) => {
				const r = el.getBoundingClientRect();
				const center = vertical ? r.top + r.height / 2 : r.left + r.width / 2;
				const dist = Math.abs((vertical ? e.clientY : e.clientX) - center);
				const scale = 1 + Math.max(0, 1 - dist / 110) * 0.42;
				el.style.transform = `scale(${scale.toFixed(3)})`;
				el.style.margin = vertical
					? `${((scale - 1) * 12).toFixed(1)}px 0`
					: `0 ${((scale - 1) * 12).toFixed(1)}px`;
			});
		});
		dock.addEventListener("mouseleave", () => {
			dock.querySelectorAll(".wss-dock-item").forEach((el) => {
				el.style.transform = "";
				el.style.margin = "";
			});
		});
	};

	const runtime = { config: null, $dock: null, loading: false };

	function go(item) {
		const a = item.action || {};
		if (a.kind === "new") return frappe.new_doc(a.doctype);
		if (a.kind === "url") return window.open(a.url, a.new_tab ? "_blank" : "_self");
		if (a.kind === "route" && a.route) return frappe.set_route(...a.route);
	}

	function hidden_here() {
		const route = (frappe.get_route && frappe.get_route()) || [];
		return route[0] === "workspace-studio" || route[0] === "print" || route[0] === "printview";
	}

	function remove() {
		if (runtime.$dock) runtime.$dock.remove();
		runtime.$dock = null;
		$("body").removeClass("wss-has-dock wss-has-dock-bottom wss-has-dock-left wss-has-dock-right");
	}

	function render() {
		remove();
		const cfg = runtime.config || {};
		const d = cfg.dock;
		if (!d || !d.items || !d.items.length || hidden_here()) return;
		if (cfg.hide_on_mobile && window.innerWidth < 768) return;

		const $dock = $(`<nav class="${wss.dock.classes(d)} wss-dock--fixed" aria-label="${__("Dock")}"></nav>`);
		$dock.css("--wss-offset", (cfg.offset || 14) + "px");
		d.items.forEach((item) => {
			const $el = $(wss.dock.item_html(item));
			if (item.type !== "separator") $el.on("click", () => go(item));
			$dock.append($el);
		});
		if (d.magnify) wss.dock.bind_magnify($dock, d.position);
		$("body").append($dock).addClass(`wss-has-dock wss-has-dock-${d.position}`);
		runtime.$dock = $dock;
	}

	function load() {
		if (runtime.loading || !frappe.session || frappe.session.user === "Guest") return;
		runtime.loading = true;
		frappe
			.xcall("thinknxg_workspace_studio.runtime.get_runtime_config")
			.then((cfg) => {
				runtime.config = cfg || {};
				render();
			})
			.catch(() => {})
			.finally(() => (runtime.loading = false));
	}

	wss.dock.reload = load;

	let started = false;
	function start() {
		if (started || !window.frappe || !frappe.boot || !frappe.router) return;
		started = true;
		load();
		frappe.router.on("change", () => {
			if (!runtime.config) return;
			const shown = !!runtime.$dock;
			if (hidden_here() && shown) remove();
			else if (!hidden_here() && !shown) render();
		});
		let t;
		$(window).on("resize.wss", () => {
			clearTimeout(t);
			t = setTimeout(render, 200);
		});
	}

	$(document).on("app_ready", start);
	$(() => setTimeout(start, 1500));
})();
