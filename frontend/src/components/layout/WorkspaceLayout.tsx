import { TopToolbar } from "./TopToolbar";
import { Sidebar } from "./Sidebar";
import { MainArea } from "./MainArea";
import { BottomPanel } from "./BottomPanel";
import { StatusBar } from "./StatusBar";

/**
 * WorkspaceLayout — the root layout shell.
 *
 * ┌──────────────────────────────────────────────┐
 * │ TopToolbar                                   │
 * ├──────────┬───────────────────────────────────┤
 * │ Sidebar  │ MainArea (tabbed documents)       │
 * │ (opt.)   │                                   │
 * ├──────────┴───────────────────────────────────┤
 * │ BottomPanel (collapsible)                    │
 * ├──────────────────────────────────────────────┤
 * │ StatusBar                                    │
 * └──────────────────────────────────────────────┘
 */
export function WorkspaceLayout() {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopToolbar />

      {/* Middle row: sidebar + main */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <MainArea />
      </div>

      <BottomPanel />
      <StatusBar />
    </div>
  );
}
