# Lotus v2 — MVP Skeleton

A proof-of-concept UI for the Lotus configuration editor, built with:

- **Frontend:** React + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui
- **Backend (stub):** FastAPI + Python

## Project Structure

```
lotus_v2/
├── src/                          # React frontend
│   ├── components/
│   │   ├── layout/               # App layout components
│   │   │   ├── TopMenuBar.tsx    # File/Edit/View/Help menu bar
│   │   │   ├── DocumentTabs.tsx  # AF / Mutex document tabs
│   │   │   ├── LeftPanel.tsx     # Line list with status indicators
│   │   │   ├── RightPanel.tsx    # Edit panel with netlist search
│   │   │   └── BottomPanel.tsx   # Problems & Log panels
│   │   └── ui/                   # shadcn/ui components (auto-generated)
│   ├── lib/
│   │   └── utils.ts              # Tailwind merge utility
│   ├── App.tsx                   # Main app layout
│   ├── main.tsx                  # Entry point
│   └── index.css                 # Tailwind + theme variables
├── backend/                      # FastAPI backend (stub)
│   ├── main.py                   # API endpoints
│   └── requirements.txt
├── package.json
├── vite.config.ts
├── tsconfig.json
└── components.json               # shadcn/ui config
```

## How to Run (Step-by-Step)

### 1. Start the Frontend

```bash
# Navigate to the project
cd lotus_v2

# Install dependencies (first time only)
npm install

# Start the development server
npx vite --host 0.0.0.0 --port 5173
```

The terminal will show:
```
VITE ready in ~800ms
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://<your-ip>:5173/
```

### 2. View in Browser

**If you're on the same machine:** Open http://localhost:5173 in your browser.

**If you're connecting via SSH (remote server):** You need an SSH tunnel:
```bash
# Run this on YOUR LOCAL machine (laptop/desktop)
ssh -L 5173:localhost:5173 <your-user>@<remote-host>
```
Then open http://localhost:5173 on your local browser.

### 3. (Optional) Start the Backend

```bash
cd lotus_v2/backend

# Create a virtual env (first time only)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --port 8000
```

API docs will be at http://localhost:8000/docs

## What's in the UI

| Area | Description |
|------|-------------|
| **Top Menu Bar** | File / Edit / View / Help menus with keyboard shortcuts. Shows ward & cell info. |
| **Document Tabs** | Switch between AF and Mutex configuration documents |
| **Left Panel** | Scrollable list of config lines with color-coded status dots (green=valid, yellow=warning, red=error, grey=comment, purple=conflict) |
| **Right Panel** | Structured edit form: template, net, AF value, flags (EM/SH), plus netlist search viewer with Nets/Templates tabs |
| **Bottom Panel** | Collapsible Problems panel (errors, warnings, conflicts) and Log output |
| **Status Bar** | App version, active doc, line count, netlist stats |

All panels are resizable via drag handles between them.

## Adding More shadcn Components

```bash
# Example: add a dialog component
npx shadcn@latest add dialog

# Example: add a dropdown menu
npx shadcn@latest add dropdown-menu
```

Browse all available components: https://ui.shadcn.com/docs/components
