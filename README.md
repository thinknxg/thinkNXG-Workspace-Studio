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
| **Dock** | macOS-style quick-launch bar (bottom / left / right, glass / solid / minimal, magnify, labels). Items open a Workspace, DocType list/view, New document, Report, Page, Dashboard or URL, with icon, colour and role visibility. |
| **Audience & Settings** | Roles and users, publish mode, priority, default workspace, sidebar / desktop icon / Dock switches, audience preview, pre-publish checklist, publish history with rollback. |
| **Housekeeping** | Undo/redo (Ctrl+Z / Ctrl+Shift+Z), Ctrl+S save, Ctrl+D duplicate, Delete, Alt+Arrows to move. Import from an existing Workspace, duplicate, export/import `.json` packages between sites. |

## How publishing works

* **Shared (Role-based)** — one public `Workspace` restricted to the audience roles. Users listed individually get a
  private copy. Block-level role visibility is *not* enforced in this mode (records stay permission-checked).
* **Personal (Per User)** — one private `Workspace` per resolved user (`<Label>-<user>`), filtered by block visibility.
  Capped at 500 users per studio.
* **Sidebar** — written to the v16 `Workspace Sidebar` DocType. **Desktop Icon** — written to the v16 `Desktop Icon`
  DocType. Both are introspected through DocType meta: fields or select options that don't exist on your build are
  skipped and reported as notes, so a schema change never blocks the workspace itself.
* **Default workspace** — sets `User.default_workspace` for the audience when enabled.
* **Dock** — served by this app's runtime (`app_include_js`). The highest-priority published studio that matches a
  user (direct user match beats role match beats "no audience") supplies their Dock. Items the user can't access are
  hidden server-side. Master switch: **Workspace Studio Settings**.
* **Safety** — the publisher refuses to overwrite a workspace it doesn't manage unless *Allow replacing an existing
  workspace* is ticked. Every Publish/Unpublish stores a snapshot in **Studio Publish Log** and can be rolled back.
  Workspaces published earlier that drop out of the audience are removed on the next publish.

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

* Developer mode: leave **Module** empty unless you intend the published workspace to be exported into that app's files.
* Publishing runs as Administrator after checking the caller has System Manager or Workspace Studio Manager, because
  Frappe only lets the *Workspace Manager* role save public workspaces.
* Designer state is kept in hidden fields on **Studio Workspace**; the form shows an *Open Designer* button instead.
