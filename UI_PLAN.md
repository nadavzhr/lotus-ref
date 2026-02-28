## Frontend Implementation Plan for React Migration

Please review the current frontend under `index.html`. It’s only a demo, and I want to migrate it into a proper React-based frontend that will eventually be wrapped with Electron as a desktop application.

Can you inspect the current structure conceptually and suggest how to migrate it into React using a modern component system (primarily shadcn), improved layout, and better UX?

Do not write code yet — just propose a layout and implementation plan.

Additional context:

* The desktop app operates inside a workspace.
* We assume environment variables such as:

  * `WARD` (working area root directory)
  * `CELL` (top-level cell currently being worked on)
* These should be displayed somewhere in the UI, but not in the main content area (maybe in a toolbar, header, right-aligned in subtle gray text, etc.).

Main requirements:

* The main view is a tabbed document viewer (multiple document types).
* Currently, `index.html` renders the document as one long view.
* Edit panels are embedded inline when editing is invoked.
* I’m unsure whether to:

  * Keep inline editing,
  * Use side-by-side panels,
  * Use a “sheet”-style panel,
  * Or a popup/modal approach.

Additional UX changes:

* Each line currently has ~7 buttons on the right.
* Most will be consolidated into a `[...]` overflow menu (insert line below, toggle comment, delete, etc.).
* Keyboard shortcuts will be added:

  * `Alt + Arrow` → swap lines
  * `Delete` → delete line
  * `Ctrl + /` → toggle comment

Messages currently displayed inline will be removed.
Instead, we’ll have a collapsible bottom panel (like VS Code) for:

* Problems
* Terminal
* Logs
* Other system messages

Other UI elements:

* A chatbot interface (either right-side panel or expandable bottom-right popup).
* A status bar at the bottom.
* Possibly a sidebar (undecided).

Please review everything and propose a comprehensive frontend implementation plan: layout, UX, UI, component structure, state architecture, and migration strategy.

---

# Frontend Implementation Plan

This will be structured in layers:

1. Overall Layout Architecture
2. Major UI Regions
3. Editing UX Strategy
4. Component Architecture (React + shadcn)
5. State & Data Architecture
6. Electron Integration Considerations
7. Chatbot Integration UX
8. Phased Execution Plan

---

# 1. Overall Layout Architecture

Since this is a desktop productivity app, the best reference models are:

* VS Code
* Notion (document-first UX)
* JetBrains IDEs

You are effectively building a document-centric IDE-like application.

### Recommended Layout (High-Level)

```
┌──────────────────────────────────────────────┐
│ Top Toolbar / Workspace Info                │
├───────────────┬──────────────────────────────┤
│ Optional      │                              │
│ Sidebar       │  Main Tabbed Document View   │
│               │                              │
│               │                              │
├───────────────┴──────────────────────────────┤
│ Collapsible Bottom Panel (Problems/Logs)    │
├──────────────────────────────────────────────┤
│ Status Bar                                   │
└──────────────────────────────────────────────┘
```

Chatbot:

* Either docked right panel (resizable)
* Or floating expandable panel (bottom-right)

I recommend starting with floating expandable, later allow docking.

---

# 2. Major UI Regions

## A. Top Toolbar (Persistent Header)

Purpose:

* Display `WARD`
* Display `CELL`
* Workspace context
* Possibly document breadcrumbs
* Global actions (open, save, edit actions (undo/redo), font size, theme switcher, etc.)

Layout:

Left:

* App name/logo
* Breadcrumb: `WARD > CELL > Document`

Right (subtle gray text):

* `WARD: /path/to/root`
* `CELL: cell_name`
* Possibly other workspace info

Use muted text styling.

UX principle:

* Informational but not intrusive.

---

## B. Sidebar (Optional / Future-Proof)

Initially collapsed by default.

Possible contents:

* File tree
* Cells list
* Search
* Outline of current document

If you’re unsure, architect for it but don’t fully design it yet.

---

## C. Main View – Tabbed Document Viewer

This is the core.

Each tab:

* Represents a document
* Could represent different document types

Use shadcn Tabs component.

Inside each tab:

Scrollable document container.

---

# 3. Document Editing UX Strategy

You’re deciding between:

1. Inline editing (current demo)
2. Side-by-side editing
3. Sheet/modal editing
4. Dedicated edit mode panel

### Recommended Approach (Hybrid Inline + Sheet)

Keep inline editing as primary.
But:

* Make edit UI cleaner and minimal.
* For complex edits, open a right-side sheet panel.
* For simple line edits, use inline minimal edit field.

Why?

* Inline feels natural for document-centric editing (for example, editing comment lines).
* Sheet feels powerful for structured edits (which we do have, for data lines).
* Side-by-side permanently wastes space.

Avoid modal popups for editing content. They interrupt flow.

---

# 4. Line-Level UX Redesign

Currently:
~7 buttons per line.

New approach:

Right side of line:

* Show minimal hover UI.
* Single `...` menu button.
* Maybe 1 high-priority action always visible (e.g., quick edit).

Overflow menu contains:

* Insert below
* Toggle comment
* Delete
* Duplicate

Keyboard shortcuts:

* Alt + Up/Down → swap
* Delete → delete
* Ctrl + / → comment
* Ctrl + D → duplicate

Important:
The line should be focusable.
Use a subtle left border highlight when selected.

This moves from “button-heavy” to “editor-like”.

---

# 5. Messages → Bottom Panel

We will move messages out of inline view.

Implement:

Collapsible bottom panel:

* Tabs: Problems | Logs | Terminal | AI | etc.
* Resizable vertically.
* Remembers last size.

Collapsed:

* Thin horizontal bar with toggle.

This keeps document clean.

---

# 6. Chatbot Integration

Two options:

### Option A: Docked Right Panel (IDE-style)

Pros:

* Feels powerful
* Good for heavy AI usage

Cons:

* Permanently reduces document width

### Option B (Recommended Start): Floating Expandable Panel

Bottom-right:

* Small circular AI button
* Expands upward into chat panel
* Resizable
* Draggable later

Later allow:

* Dock to right
* Open in bottom panel

Start simple.

---

# 7. Status Bar (Bottom)

Like VS Code.

Content ideas:

Left:

* Document type
* Line count
* Selection info

Right:

* WARD
* CELL
* Save status
* Sync status

* Subtly differentiate in dark vs light
* Use elevation tokens, not borders when possible

---

# 8. Component Architecture (React + shadcn)

High-level component tree:

App
├─ WorkspaceLayout
│   ├─ TopToolbar
│   ├─ Sidebar (optional)
│   ├─ MainArea
│   │   ├─ TabManager
│   │   │   ├─ DocumentTab
│   │   │   │   └─ DocumentViewer
│   │   │   │       ├─ LineComponent
│   │   │   │       └─ InlineEditor
│   ├─ BottomPanel
│   └─ StatusBar
└─ ChatbotOverlay

Key Design Rule:
Separate:

* Document rendering
* Editing state
* Workspace context

---

# 9. State Architecture

Since this is a desktop app:

Use:

* Zustand (simple global store) OR
* Redux Toolkit (if you expect complexity)

State domains:

* WorkspaceState (WARD, CELL, current path)
* TabsState
* DocumentState
* SelectionState
* PanelState (bottom open/closed, size)
* ChatState

Avoid putting everything in one store.

---

## 9.1 Theming Architecture (Dark / Light Mode)

### Goals

* Support Light / Dark mode
* Persist user preference
* Allow system-based theme (optional)
* Ensure compatibility with shadcn + Tailwind
* Work cleanly inside Electron

---

### Theme Strategy

**Use class-based theming (not media-only).**

Root element:

```html
<html class="dark">
```

or

```html
<html class="light">
```

Why:

* Works reliably in Electron
* Allows manual override
* Compatible with shadcn design tokens

---

### Implementation Structure

Add a new domain to global state:

**ThemeState**

* theme: `"light" | "dark" | "system"`
* setTheme()
* resolvedTheme (computed)

Persist:

* localStorage
* optionally workspace-level config later

---

### Theme Provider

Add:

`<ThemeProvider>` at the top of the app:

App
└─ ThemeProvider
└─ WorkspaceLayout

Responsibilities:

* Apply class to `<html>`
* Listen for system preference if theme === "system"
* Hydrate initial theme before first paint (avoid flash)

---

### Where Theme Controls Appear in UI

Add theme toggle in:

**TopToolbar → Right side**

* Small icon toggle (sun/moon)
* Or dropdown inside settings menu

Optional later:

* Add in Command Palette

---

### Design System Integration

Since you're using shadcn:

* Define theme tokens in `globals.css`
* Use semantic tokens (`--background`, `--foreground`, `--muted`, etc.)
* Avoid hardcoded colors anywhere in components

Rule:
No raw color classes like `bg-white`, `text-black`
Only use design tokens.

---

# 10. Electron Considerations

Since this is Electron-wrapped:

Plan for:

* IPC bridge for file operations
* Context isolation
* Secure preload API

Frontend should never directly touch filesystem.

Abstract API layer:

```
/api
  workspace.ts
  document.ts
  ai.ts
```

So React never cares whether backend is local, remote, or mocked.

---

# 11. UX Principles for This App

This should feel like:

* Document-first
* Clean
* Minimal chrome
* Keyboard-friendly
* Non-cluttered

Avoid:

* Button overload
* Persistent inline errors
* Modal-heavy UX
* Theme-specific hacks inside components

Embrace:

* Hover-revealed controls
* Subtle animations
* Clear focus states
* Strong semantic color system (theme-aware, no hardcoded colors)
* Command palette (future enhancement)

---

# 12. Phased Execution Plan

# 12. Phased Execution Plan

### Phase 1 – Core Layout Skeleton ✅ COMPLETED

* ✅ React app scaffold (Vite + React 18 + TypeScript)
* ✅ shadcn setup (new-york style + tailwindcss-animate)
* ✅ Layout regions (WorkspaceLayout with header, main, status bar)
* ✅ Tabs system (multi-document tabs with Zustand tab store)
* ✅ Theme system (provider + toggle, dark/light/system)
* ✅ Global design tokens (CSS variables for all colors including status-ok/warning/error)
* ✅ Dark/light verification across layout
* ✅ Status bar
* ✅ Workspace header (WARD + CELL display)

---

### Phase 2 – Document Viewer ✅ COMPLETED

* ✅ Render document lines (LineRow component with mono text)
* ✅ Selection state (click to select, highlight with accent)
* ✅ Hover controls (edit pencil icon on hover)
* ✅ Overflow menu (LineOverflowMenu: insert below, toggle comment, delete, swap up/down)
* ✅ Keyboard shortcuts (Enter/Space to edit)
* ✅ Status dots (colored circles with tooltip: ok/warning/error/comment/empty/conflict)
* ✅ Summary bar (live status counts: ok/warning/error/comment/conflict)
* ✅ Search & filter bar (text search + status filter dropdown with dot+label)
* ✅ Line numbers (tabular-nums, right-aligned)
* ✅ Left border color per status

---

### Phase 3 – Editing System ✅ COMPLETED

* ✅ Modal dialog for structured edits (replaced sheet approach)
* ✅ macOS-style zoom-from-origin dialog animation (scale 0.92→1.0, 280ms deceleration curve)
* ✅ Dialog retains content during close animation (ref-based last-value preservation)
* ✅ Inline comment editor (for comment lines)
* ✅ AF edit form:
  * ✅ NetlistSearchPanel first (template + net + regex toggles + tabbed NQS results)
  * ✅ AF value + EM/SH/SCH checkboxes in compact row below
  * ✅ Hydrate → update → commit pattern with debounced preview
  * ✅ Validation messages (errors + warnings)
* ✅ Mutex edit form:
  * ✅ Session info bar (template, regex mode, num_active, fev metadata)
  * ✅ NetlistSearchPanel first (with add-to-mutexed / add-to-active actions)
  * ✅ Rich entry data (template_name, regex_mode, match_count preserved per entry)
  * ✅ Two-column mutexed/active nets lists with remove/promote actions
  * ✅ Num Active control inline next to Active Nets title
  * ✅ FEV mode at bottom
  * ✅ Proper template:net parsing from NQS results
  * ✅ All mutation endpoints (add/remove mutexed/active, set-fev, set-num-active)
* ✅ Empty lines open edit dialog (empty session)
* ✅ Load document dialog (quick load + path input)
* ✅ Undo/redo support (backend)
* ✅ Live summary tracking (statusCounts recomputed after mutations)

---

### Phase 4 – Bottom Panel 🔲 NOT STARTED

* Problems tab
* Log stream (placeholder for now)
* Collapsible + resizable behavior
* Terminal (placeholder for now)

---

### Phase 5 – Chatbot 🔲 NOT STARTED

* Floating panel
* Message threading
* Document context injection

---

### Phase 6 – Sidebar (Optional) 🔲 NOT STARTED

* File tree
* Outline
* Search

---

# Final Recommendation on Layout Decisions

If I had to lock in one structure:

* Top toolbar with subtle workspace info
* No sidebar at first
* Main tabbed document view
* Collapsible bottom panel
* Floating AI chat button
* Status bar
* Inline editing primary, sheet secondary
* Aggregated line actions in overflow

This gives you:

Clean UI
Expandable architecture
Modern UX
IDE-level extensibility

---

If you'd like next, we can:

* Convert this into a concrete component spec (with props and responsibilities), or
* Define a visual wireframe structure in more detail (pixel-level layout reasoning), or
* Start executing Phase 1 architecture decisions.
