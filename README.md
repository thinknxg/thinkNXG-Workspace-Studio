# thinkNXG Workspace Studio

A visual, drag-and-drop designer for **workspaces, left sidebar menus and the Dock** on thinkNXG ERP / Frappe v16.
Administrators design a personalised workspace for specific **roles or users**, then publish it as real Frappe
documents. Nobody edits Config, Navigation or Dock JSON — everything is edited in structured property panels.

Publisher: Kreatao · License: MIT · App name: `thinknxg_workspace_studio`

---

## Install

```bash
cd frappe-bench
bench get-app /path/to/thinknxg_workspace_studio      # or the git URL
bench --site yoursite install-app thinknxg_workspace_studio
bench build --app thinknxg_workspace_studio
bench --site yoursite migrate
```

Open **/app/workspace-studio** (also on the v16 apps screen). Access is for **System Manager** and the
**Workspace Studio Manager** role (created at install).

## What you get

| Area | What it does |
|---|---|
| **Layout canvas** | 12-column grid. Drag Header, Text, Spacer, Shortcut, Link Card, Quick List, Number Card, Chart and Custom HTML blocks (plus ready-made patterns) from the palette. Drag to reorder, drag the right edge to resize, desktop / tablet / mobile preview. |
| **Property panel** | Typed fields per block (Link pickers for DocType, Report, Page, Dashboard Chart, Number Card, Custom HTML Block), width presets, colour, view, count/list **filter builder** (Frappe FilterGroup), card link list with drag-reorder and bulk DocType add. |
| **Block visibility** | Each block can be limited to roles (enforced per user in Personal mode). |
| **Sidebar Menu** | Tree builder: sections, links and dividers. Drop a link onto the middle of a section to nest it. One-click *Generate from layout*. |
| **Dock** | Native v16 Dock entries (Module, Workspace, URL) published to an app rail, plus a Studio Quick Launch bar for DocType lists, New document, Report, Page and Dashboard (bottom / left / right, glass / solid / minimal, magnify, labels). Icon, colour and role visibility per item. |
| **Audience & Settings** | Roles and users, publish mode, priority, default workspace, sidebar / desktop icon / Dock switches, audience preview, pre-publish checklist, publish history with rollback. |
| **Housekeeping** | Undo/redo (Ctrl+Z / Ctrl+Shift+Z), Ctrl+S save, Ctrl+D duplicate, Delete, Alt+Arrows to move. Import from an existing Workspace, duplicate, export/import `.json` packages between sites. |

## How publishing works (v16)

v16 builds the desk from **modules**: a module's sidebar is the menu shown next to its pages, and the
**Dock** is a per-app rail of modules, workspaces and links, layered app → site → user.

* **Module** — each studio gets its own custom module named after the Workspace Label (if that
  name is taken by another app's module, `<Label> Workspace` is used). Pick a Module on the studio
  only to publish into an existing one. The module is created *unplaced*, so it appears only where
  the Dock puts it.
* **Workspace** — **Shared** mode publishes one public Workspace restricted to the audience roles
  (users listed individually get a private copy). **Personal** mode publishes a private copy per
  user, filtered by block visibility (max 500 users).
* **Sidebar menu** — published as a **Custom Sidebar** layer on the studio's module: the site layer
  in Shared mode and one layer per user in Personal mode. The studio's workspace is always the first
  item, so the module opens on it.
* **Dock** — published to the native **Dock** of the chosen app rail (default ERPNext, else Frappe):
  * no audience → the site layer (everyone); roles/users → each resolved user's own layer;
  * **Add** mode (default) keeps the rail's existing entries and puts the studio's entries first;
    **Replace** mode leaves only the studio's entries;
  * the studio's module is always the first entry; designer items of type Module, Workspace and
    URL go to the native Dock;
  * items the native Dock cannot hold (DocType list, New document, Report, Page, Dashboard) are
    shown in the Studio **Quick Launch bar** (`app_include_js`), styled in the Dock tab.
* **Default workspace** — sets `User.default_workspace` for the audience when enabled.
* **Safety** — the publisher refuses to overwrite a workspace it doesn't manage unless *Allow
  replacing an existing workspace* is ticked. Every Publish/Unpublish stores a snapshot in **Studio
  Publish Log** and can be rolled back. On re-publish, layers and workspaces for users who left the
  audience are removed; on a shared Dock layer only the studio's own entries are removed.
* **Older v16 builds** without `Custom Sidebar`/`Dock` fall back to `Workspace Sidebar`,
  `Desktop Icon` and the Quick Launch bar for all dock items.

## Module layout

```
thinknxg_workspace_studio/
  schema.py        pure transforms (designer state <-> Workspace payload), unit-tested without a bench
  publisher.py     Workspace / Workspace Sidebar / Desktop Icon / default workspace, snapshots, rollback
  api.py           whitelisted API for the designer
  runtime.py       per-user Dock resolution (cached)
  public/js/studio_runtime.js, public/css/studio_runtime.css   desk Dock
  workspace_studio/page/workspace_studio/                       the designer page
  workspace_studio/doctype/  Studio Workspace, Studio Target, Studio Publish Log, Workspace Studio Settings
  tests/test_schema.py
```

Run the pure tests: `python -m unittest thinknxg_workspace_studio.tests.test_schema`

## Notes for v16

* **Module**: v16 requires one on every Workspace. If the studio leaves it empty, shared workspaces go to
  `Custom Workspaces` and personal copies to `Private` (Frappe's own triage modules, created if missing).
  Published workspaces are saved with `standard = 0`, so developer mode never exports them into app files.
* Publishing runs as Administrator after checking the caller has System Manager or Workspace Studio Manager, because
  Frappe only lets the *Workspace Manager* role save public workspaces.
* Designer state is kept in hidden fields on **Studio Workspace**; the form shows an *Open Designer* button instead.
