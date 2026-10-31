"""Pure transforms between the Workspace Studio designer state and Frappe Workspace payloads.

Nothing in this module imports frappe, so it can be unit-tested outside a bench.

Designer state
--------------
layout  = {"blocks": [{"id", "type", "col", "roles": [..], "data": {..}}]}
sidebar = {"items": [section | link | spacer]}   (sections hold "children")
dock    = {"enabled", "position", "size", "style", "magnify", "show_labels", "items": [..]}
"""

import html
import json
import random
import re
import string

BLOCK_TYPES = (
    "header",
    "paragraph",
    "spacer",
    "shortcut",
    "card",
    "chart",
    "number_card",
    "quick_list",
    "custom_block",
)
DEFAULT_COL = {
    "header": 12,
    "paragraph": 12,
    "spacer": 12,
    "shortcut": 3,
    "card": 4,
    "chart": 6,
    "number_card": 3,
    "quick_list": 4,
    "custom_block": 6,
}
SHORTCUT_TYPES = ("DocType", "Report", "Page", "Dashboard", "URL")
SHORTCUT_COLORS = ("Grey", "Green", "Red", "Orange", "Pink", "Yellow", "Blue", "Cyan")
DOC_VIEWS = ("", "List", "Report Builder", "Dashboard", "Tree", "New", "Calendar", "Kanban")
CARD_LINK_TYPES = ("DocType", "Report", "Page")
SIDEBAR_LINK_TYPES = ("DocType", "Report", "Page", "Workspace", "Dashboard", "URL")
DOCK_LINK_TYPES = ("Workspace", "DocType", "New", "Report", "Page", "Dashboard", "URL")
DOCK_POSITIONS = ("bottom", "left", "right")
DOCK_STYLES = ("glass", "solid", "minimal")
DOCK_SIZES = ("small", "medium", "large")
HEADER_SIZES = {"Large": "h4", "Medium": "h5", "Small": "h6"}
FILTER_OPERATORS = (
    "=", "!=", ">", "<", ">=", "<=", "like", "not like", "in", "not in",
    "is", "between", "timespan", "descendants of", "ancestors of",
)


# --------------------------------------------------------------------------- helpers
def new_id(length=10):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def loads(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _s(value, maxlen=140):
    if value is None:
        return ""
    return str(value).strip()[:maxlen]


def _int(value, default, lo, hi):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, value))


def _bool(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _choice(value, options, default):
    return value if value in options else default


def _names(values, maxlen=140):
    out = []
    if isinstance(values, str):
        values = [v for v in re.split(r"[,\n]", values)]
    for v in values or []:
        if isinstance(v, dict):
            v = v.get("role") or v.get("value") or v.get("name")
        v = _s(v, maxlen)
        if v and v not in out:
            out.append(v)
    return out


def normalize_filters(filters):
    """Internal filter format: [[fieldname, operator, value], ...]."""
    out = []
    if isinstance(filters, dict):
        for field, cond in filters.items():
            if isinstance(cond, (list, tuple)) and len(cond) == 2:
                out.append([_s(field), cond[0], cond[1]])
            else:
                out.append([_s(field), "=", cond])
        filters = []
    for f in filters or []:
        if not isinstance(f, (list, tuple)):
            continue
        f = list(f)
        if len(f) >= 4:  # [doctype, field, op, value, (hidden)]
            f = f[1:4]
        if len(f) != 3 or not f[0]:
            continue
        op = f[1] if f[1] in FILTER_OPERATORS else "="
        value = f[2]
        if not isinstance(value, (str, int, float, list, bool)) and value is not None:
            value = str(value)
        out.append([_s(f[0]), op, value])
    return out


def visible_for(required_roles, user_roles):
    if not required_roles:
        return True
    if user_roles is None:
        return True
    return bool(set(required_roles) & set(user_roles))


def unique_id(item_id, used):
    item_id = _s(item_id, 24)
    if not item_id or item_id in used:
        item_id = new_id()
        while item_id in used:
            item_id = new_id()
    used.add(item_id)
    return item_id


# --------------------------------------------------------------------------- layout
def normalize_link(link):
    link = link or {}
    return {
        "id": _s(link.get("id"), 24) or new_id(),
        "label": _s(link.get("label")) or _s(link.get("link_to")),
        "link_type": _choice(link.get("link_type"), CARD_LINK_TYPES, "DocType"),
        "link_to": _s(link.get("link_to")),
        "onboard": 1 if _bool(link.get("onboard")) else 0,
        "dependencies": _names(link.get("dependencies")),
    }


def normalize_block(block, used_ids=None):
    if not isinstance(block, dict):
        return None
    btype = block.get("type")
    if btype not in BLOCK_TYPES:
        return None
    used_ids = used_ids if used_ids is not None else set()
    data = block.get("data") or {}
    d = {}
    if btype == "header":
        d = {"text": _s(data.get("text"), 200), "size": _choice(data.get("size"), HEADER_SIZES, "Large")}
    elif btype == "paragraph":
        d = {"text": _s(data.get("text"), 4000)}
    elif btype == "shortcut":
        stype = _choice(data.get("type"), SHORTCUT_TYPES, "DocType")
        d = {
            "label": _s(data.get("label")) or _s(data.get("link_to")),
            "type": stype,
            "link_to": _s(data.get("link_to")) if stype != "URL" else "",
            "url": _s(data.get("url"), 1000) if stype == "URL" else "",
            "doc_view": _choice(data.get("doc_view"), DOC_VIEWS, "") if stype == "DocType" else "",
            "color": _choice(data.get("color"), SHORTCUT_COLORS, "Grey"),
            "format": _s(data.get("format"), 60),
            "filters": normalize_filters(data.get("filters")) if stype == "DocType" else [],
        }
    elif btype == "card":
        d = {
            "label": _s(data.get("label")) or "Links",
            "links": [normalize_link(l) for l in (data.get("links") or []) if isinstance(l, dict)],
        }
    elif btype == "chart":
        d = {"chart_name": _s(data.get("chart_name")), "label": _s(data.get("label")) or _s(data.get("chart_name"))}
    elif btype == "number_card":
        d = {
            "number_card_name": _s(data.get("number_card_name")),
            "label": _s(data.get("label")) or _s(data.get("number_card_name")),
        }
    elif btype == "quick_list":
        d = {
            "document_type": _s(data.get("document_type")),
            "label": _s(data.get("label")) or _s(data.get("document_type")),
            "filters": normalize_filters(data.get("filters")),
        }
    elif btype == "custom_block":
        d = {
            "custom_block_name": _s(data.get("custom_block_name")),
            "label": _s(data.get("label")) or _s(data.get("custom_block_name")),
        }
    return {
        "id": unique_id(block.get("id"), used_ids),
        "type": btype,
        "col": _int(block.get("col"), DEFAULT_COL[btype], 1, 12),
        "roles": _names(block.get("roles")),
        "data": d,
    }


def normalize_layout(layout):
    layout = layout if isinstance(layout, dict) else {"blocks": layout if isinstance(layout, list) else []}
    used = set()
    blocks = [normalize_block(b, used) for b in layout.get("blocks") or []]
    return {"blocks": [b for b in blocks if b]}


def _esc(text):
    return html.escape(text or "", quote=False)


def block_has_target(block):
    t, d = block["type"], block["data"]
    if t == "shortcut":
        return bool(d.get("url") if d.get("type") == "URL" else d.get("link_to"))
    if t == "card":
        return any(l.get("link_to") for l in d.get("links") or [])
    if t == "chart":
        return bool(d.get("chart_name"))
    if t == "number_card":
        return bool(d.get("number_card_name"))
    if t == "quick_list":
        return bool(d.get("document_type"))
    if t == "custom_block":
        return bool(d.get("custom_block_name"))
    return True


def build_workspace_payload(layout, user_roles=None):
    """Turn designer layout into Workspace `content` + child tables.

    `user_roles=None` keeps every block (shared workspace); a list filters
    blocks by their role visibility (personal workspace).
    """
    layout = normalize_layout(layout)
    payload = {
        "content": [],
        "shortcuts": [],
        "links": [],
        "charts": [],
        "number_cards": [],
        "quick_lists": [],
        "custom_blocks": [],
    }
    warnings = []
    used = {k: set() for k in payload}

    def uniq(kind, label):
        base = label or kind.replace("_", " ").title()
        label, i = base, 2
        while label in used[kind]:
            label = f"{base} ({i})"
            i += 1
        used[kind].add(label)
        return label

    for b in layout["blocks"]:
        if user_roles is not None and not visible_for(b["roles"], user_roles):
            continue
        t, d, col = b["type"], b["data"], b["col"]
        if not block_has_target(b):
            warnings.append(f"Skipped {t.replace('_', ' ')} block '{d.get('label') or b['id']}' - it has no target set.")
            continue

        if t == "header":
            tag = HEADER_SIZES[d["size"]]
            text = f'<span class="{tag}"><b>{_esc(d["text"])}</b></span>'
            payload["content"].append({"id": b["id"], "type": "header", "data": {"text": text, "col": col}})
        elif t == "paragraph":
            text = "<p>" + _esc(d["text"]).replace("\n", "<br>") + "</p>"
            payload["content"].append({"id": b["id"], "type": "paragraph", "data": {"text": text, "col": col}})
        elif t == "spacer":
            payload["content"].append({"id": b["id"], "type": "spacer", "data": {"col": col}})
        elif t == "shortcut":
            label = uniq("shortcuts", d["label"])
            row = {
                "label": label,
                "type": d["type"],
                "link_to": d["link_to"] or None,
                "url": d["url"] or None,
                "doc_view": d["doc_view"] or "",
                "color": d["color"],
                "format": d["format"] or None,
            }
            if d.get("filters"):
                row["stats_filter"] = json.dumps({f[0]: [f[1], f[2]] for f in d["filters"]})
            payload["shortcuts"].append(row)
            payload["content"].append(
                {"id": b["id"], "type": "shortcut", "data": {"shortcut_name": label, "col": col}}
            )
        elif t == "card":
            label = uniq("links", d["label"])
            links = [l for l in d["links"] if l["link_to"]]
            payload["links"].append({"type": "Card Break", "label": label, "link_count": len(links)})
            for l in links:
                payload["links"].append(
                    {
                        "type": "Link",
                        "label": l["label"] or l["link_to"],
                        "link_type": l["link_type"],
                        "link_to": l["link_to"],
                        "onboard": l["onboard"],
                        "dependencies": ", ".join(l["dependencies"]) or None,
                        "is_query_report": 0,
                        "hidden": 0,
                        "link_count": 0,
                    }
                )
            payload["content"].append({"id": b["id"], "type": "card", "data": {"card_name": label, "col": col}})
        elif t == "chart":
            label = uniq("charts", d["label"])
            payload["charts"].append({"chart_name": d["chart_name"], "label": label})
            payload["content"].append({"id": b["id"], "type": "chart", "data": {"chart_name": label, "col": col}})
        elif t == "number_card":
            label = uniq("number_cards", d["label"])
            payload["number_cards"].append({"number_card_name": d["number_card_name"], "label": label})
            payload["content"].append(
                {"id": b["id"], "type": "number_card", "data": {"number_card_name": label, "col": col}}
            )
        elif t == "quick_list":
            label = uniq("quick_lists", d["label"])
            row = {"document_type": d["document_type"], "label": label}
            if d.get("filters"):
                row["quick_list_filter"] = json.dumps(
                    [[d["document_type"], f[0], f[1], f[2], False] for f in d["filters"]]
                )
            payload["quick_lists"].append(row)
            payload["content"].append(
                {"id": b["id"], "type": "quick_list", "data": {"quick_list_name": label, "col": col}}
            )
        elif t == "custom_block":
            label = uniq("custom_blocks", d["label"])
            payload["custom_blocks"].append({"custom_block_name": d["custom_block_name"], "label": label})
            payload["content"].append(
                {"id": b["id"], "type": "custom_block", "data": {"custom_block_name": label, "col": col}}
            )
    return payload, warnings


# --------------------------------------------------------------------------- import
_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text):
    text = re.sub(r"<br\s*/?>", "\n", text or "", flags=re.I)
    text = re.sub(r"</p>\s*<p>", "\n", text, flags=re.I)
    return html.unescape(_TAG_RE.sub("", text)).strip()


def _parse_filter_json(value):
    data = loads(value, None)
    if data is None:
        return []
    return normalize_filters(data)


def workspace_to_layout(workspace):
    """Convert a Workspace (dict with content + child tables) to designer layout."""
    content = loads(workspace.get("content"), [])
    warnings = []
    shortcuts = {r.get("label"): r for r in workspace.get("shortcuts") or []}
    charts = {r.get("label"): r for r in workspace.get("charts") or []}
    numbers = {r.get("label"): r for r in workspace.get("number_cards") or []}
    quick = {r.get("label"): r for r in workspace.get("quick_lists") or []}
    custom = {r.get("label"): r for r in workspace.get("custom_blocks") or []}

    cards, current = {}, None
    for row in workspace.get("links") or []:
        if row.get("type") == "Card Break":
            current = row.get("label")
            cards[current] = []
        elif current is not None and row.get("link_to"):
            cards[current].append(
                {
                    "label": row.get("label"),
                    "link_type": row.get("link_type"),
                    "link_to": row.get("link_to"),
                    "onboard": row.get("onboard"),
                    "dependencies": row.get("dependencies"),
                }
            )

    blocks = []
    for item in content if isinstance(content, list) else []:
        t = item.get("type")
        data = item.get("data") or {}
        col = data.get("col") or DEFAULT_COL.get(t, 12)
        block = None
        if t == "header":
            raw = data.get("text") or ""
            size = "Large"
            for name, tag in HEADER_SIZES.items():
                if f'class="{tag}"' in raw:
                    size = name
            block = {"type": "header", "data": {"text": strip_html(raw), "size": size}}
        elif t == "paragraph":
            block = {"type": "paragraph", "data": {"text": strip_html(data.get("text"))}}
        elif t == "spacer":
            block = {"type": "spacer", "data": {}}
        elif t == "shortcut":
            r = shortcuts.get(data.get("shortcut_name"))
            if r:
                block = {
                    "type": "shortcut",
                    "data": {
                        "label": r.get("label"),
                        "type": r.get("type"),
                        "link_to": r.get("link_to"),
                        "url": r.get("url"),
                        "doc_view": r.get("doc_view"),
                        "color": r.get("color"),
                        "format": r.get("format"),
                        "filters": _parse_filter_json(r.get("stats_filter")),
                    },
                }
        elif t == "card":
            name = data.get("card_name")
            if name in cards:
                block = {"type": "card", "data": {"label": name, "links": cards[name]}}
        elif t == "chart":
            r = charts.get(data.get("chart_name"))
            if r:
                block = {"type": "chart", "data": {"chart_name": r.get("chart_name"), "label": r.get("label")}}
        elif t == "number_card":
            r = numbers.get(data.get("number_card_name"))
            if r:
                block = {
                    "type": "number_card",
                    "data": {"number_card_name": r.get("number_card_name"), "label": r.get("label")},
                }
        elif t == "quick_list":
            r = quick.get(data.get("quick_list_name"))
            if r:
                block = {
                    "type": "quick_list",
                    "data": {
                        "document_type": r.get("document_type"),
                        "label": r.get("label"),
                        "filters": _parse_filter_json(r.get("quick_list_filter")),
                    },
                }
        elif t == "custom_block":
            r = custom.get(data.get("custom_block_name"))
            if r:
                block = {
                    "type": "custom_block",
                    "data": {"custom_block_name": r.get("custom_block_name"), "label": r.get("label")},
                }
        else:
            warnings.append(f"Block type '{t}' is not supported by the designer and was skipped.")
            continue
        if block is None:
            warnings.append(f"A {t} block referenced a missing row and was skipped.")
            continue
        block["id"] = item.get("id")
        block["col"] = col
        blocks.append(block)
    return normalize_layout({"blocks": blocks}), warnings


# --------------------------------------------------------------------------- sidebar
def _norm_sidebar_link(item):
    lt = _choice(item.get("link_type"), SIDEBAR_LINK_TYPES, "DocType")
    return {
        "type": "link",
        "label": _s(item.get("label")) or _s(item.get("link_to")) or "Link",
        "icon": _s(item.get("icon"), 60),
        "link_type": lt,
        "link_to": _s(item.get("link_to")) if lt != "URL" else "",
        "url": _s(item.get("url"), 1000) if lt == "URL" else "",
        "roles": _names(item.get("roles")),
    }


def normalize_sidebar(sidebar):
    sidebar = sidebar if isinstance(sidebar, dict) else {"items": sidebar if isinstance(sidebar, list) else []}
    used = set()
    items = []

    def norm_child(c):
        if not isinstance(c, dict):
            return None
        if c.get("type") == "spacer":
            return {"id": unique_id(c.get("id"), used), "type": "spacer"}
        if c.get("type") == "link":
            out = _norm_sidebar_link(c)
            out["id"] = unique_id(c.get("id"), used)
            return out
        return None

    for it in sidebar.get("items") or []:
        if not isinstance(it, dict):
            continue
        if it.get("type") == "section":
            children = []
            for c in it.get("children") or []:
                if isinstance(c, dict) and c.get("type") == "section":
                    children.extend(filter(None, (norm_child(x) for x in c.get("children") or [])))
                else:
                    n = norm_child(c)
                    if n:
                        children.append(n)
            items.append(
                {
                    "id": unique_id(it.get("id"), used),
                    "type": "section",
                    "label": _s(it.get("label")) or "Section",
                    "icon": _s(it.get("icon"), 60),
                    "collapsible": 1 if _bool(it.get("collapsible", True)) else 0,
                    "keep_closed": 1 if _bool(it.get("keep_closed")) else 0,
                    "roles": _names(it.get("roles")),
                    "children": children,
                }
            )
        else:
            n = norm_child(it)
            if n:
                items.append(n)
    return {"items": items}


def sidebar_from_layout(layout):
    """Generate a sensible left sidebar from the layout's shortcuts and link cards."""
    layout = normalize_layout(layout)
    items = []
    shortcuts = [b for b in layout["blocks"] if b["type"] == "shortcut" and block_has_target(b)]
    if shortcuts:
        children = []
        for b in shortcuts:
            d = b["data"]
            lt = d["type"] if d["type"] in SIDEBAR_LINK_TYPES else "DocType"
            children.append(
                {"type": "link", "label": d["label"], "link_type": lt, "link_to": d["link_to"], "url": d["url"]}
            )
        items.append({"type": "section", "label": "Shortcuts", "collapsible": 1, "children": children})
    for b in layout["blocks"]:
        if b["type"] != "card":
            continue
        children = [
            {"type": "link", "label": l["label"], "link_type": l["link_type"], "link_to": l["link_to"]}
            for l in b["data"]["links"]
            if l["link_to"]
        ]
        if children:
            items.append(
                {"type": "section", "label": b["data"]["label"], "collapsible": 1, "children": children}
            )
    return normalize_sidebar({"items": items})


def flatten_sidebar(sidebar, user_roles=None):
    """Logical flat rows (v16 Workspace Sidebar style): Section Break / Link / Spacer."""
    rows = []
    for it in normalize_sidebar(sidebar)["items"]:
        if it["type"] == "section":
            if not visible_for(it["roles"], user_roles):
                continue
            kids = [c for c in it["children"] if c["type"] == "spacer" or visible_for(c["roles"], user_roles)]
            rows.append(
                {
                    "kind": "section",
                    "label": it["label"],
                    "icon": it["icon"],
                    "collapsible": it["collapsible"],
                    "keep_closed": it["keep_closed"],
                    "child": 0,
                }
            )
            for c in kids:
                rows.append(_flat_child(c, child=1))
        elif it["type"] == "spacer" or visible_for(it.get("roles"), user_roles):
            rows.append(_flat_child(it, child=0))
    return rows


def _flat_child(c, child):
    if c["type"] == "spacer":
        return {"kind": "spacer", "label": "", "child": child}
    return {
        "kind": "link",
        "label": c["label"],
        "icon": c["icon"],
        "link_type": c["link_type"],
        "link_to": c["link_to"],
        "url": c["url"],
        "child": child,
        "indent": child,
    }


def sidebar_from_rows(rows):
    """Import v16 Workspace Sidebar rows (generic dicts) back into designer state."""
    items, current = [], None
    for r in rows or []:
        rtype = (r.get("type") or "").lower()
        if "section" in rtype or "break" in rtype:
            current = {
                "type": "section",
                "label": r.get("label"),
                "icon": r.get("icon"),
                "collapsible": r.get("collapsible", 1),
                "keep_closed": r.get("keep_closed", 0),
                "children": [],
            }
            items.append(current)
            continue
        if "spacer" in rtype or "divider" in rtype or "separator" in rtype:
            node = {"type": "spacer"}
        else:
            node = {
                "type": "link",
                "label": r.get("label"),
                "icon": r.get("icon"),
                "link_type": r.get("link_type"),
                "link_to": r.get("link_to"),
                "url": r.get("url"),
            }
        if current is not None and (r.get("child") or r.get("indent")):
            current["children"].append(node)
        else:
            current = None if not (r.get("child") or r.get("indent")) else current
            items.append(node)
    return normalize_sidebar({"items": items})


# --------------------------------------------------------------------------- dock
def default_dock():
    return {
        "enabled": 1,
        "position": "bottom",
        "size": "medium",
        "style": "glass",
        "magnify": 1,
        "show_labels": 0,
        "items": [],
    }


def normalize_dock(dock):
    dock = dock if isinstance(dock, dict) else {}
    base = default_dock()
    out = {
        "enabled": 1 if _bool(dock.get("enabled", base["enabled"])) else 0,
        "position": _choice(dock.get("position"), DOCK_POSITIONS, base["position"]),
        "size": _choice(dock.get("size"), DOCK_SIZES, base["size"]),
        "style": _choice(dock.get("style"), DOCK_STYLES, base["style"]),
        "magnify": 1 if _bool(dock.get("magnify", base["magnify"])) else 0,
        "show_labels": 1 if _bool(dock.get("show_labels")) else 0,
        "items": [],
    }
    used = set()
    for it in (dock.get("items") or [])[:40]:
        if not isinstance(it, dict):
            continue
        if it.get("type") == "separator":
            out["items"].append({"id": unique_id(it.get("id"), used), "type": "separator"})
            continue
        lt = _choice(it.get("link_type"), DOCK_LINK_TYPES, "DocType")
        color = _s(it.get("color"), 20)
        if color and not re.fullmatch(r"#[0-9a-fA-F]{3,8}|[a-zA-Z]+", color):
            color = ""
        out["items"].append(
            {
                "id": unique_id(it.get("id"), used),
                "type": "item",
                "label": _s(it.get("label")) or _s(it.get("link_to")) or "Item",
                "icon": _s(it.get("icon"), 60),
                "color": color or "#4f46e5",
                "link_type": lt,
                "link_to": _s(it.get("link_to")) if lt != "URL" else "",
                "url": _s(it.get("url"), 1000) if lt == "URL" else "",
                "doc_view": _choice(it.get("doc_view"), DOC_VIEWS, "") if lt == "DocType" else "",
                "new_tab": 1 if _bool(it.get("new_tab")) else 0,
                "roles": _names(it.get("roles")),
            }
        )
    return out


# --------------------------------------------------------------------------- templates
def starter_layout(title="Overview"):
    return normalize_layout(
        {
            "blocks": [
                {"type": "header", "data": {"text": title, "size": "Large"}},
                {"type": "shortcut", "col": 3, "data": {"label": "To Do", "type": "DocType", "link_to": "ToDo", "color": "Blue"}},
                {"type": "shortcut", "col": 3, "data": {"label": "Notes", "type": "DocType", "link_to": "Note", "color": "Yellow"}},
                {"type": "shortcut", "col": 3, "data": {"label": "Events", "type": "DocType", "link_to": "Event", "doc_view": "Calendar", "color": "Green"}},
                {"type": "shortcut", "col": 3, "data": {"label": "Files", "type": "DocType", "link_to": "File", "color": "Grey"}},
                {"type": "spacer"},
                {"type": "header", "data": {"text": "Collaboration", "size": "Medium"}},
                {
                    "type": "card",
                    "col": 4,
                    "data": {
                        "label": "Daily Work",
                        "links": [
                            {"label": "To Do", "link_type": "DocType", "link_to": "ToDo"},
                            {"label": "Event", "link_type": "DocType", "link_to": "Event"},
                            {"label": "Note", "link_type": "DocType", "link_to": "Note"},
                        ],
                    },
                },
                {"type": "quick_list", "col": 8, "data": {"label": "My Open To Dos", "document_type": "ToDo", "filters": [["status", "=", "Open"]]}},
            ]
        }
    )


def blank_layout(title="Overview"):
    return normalize_layout({"blocks": [{"type": "header", "data": {"text": title, "size": "Large"}}]})
