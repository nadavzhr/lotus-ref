import { Terminal } from "lucide-react";

/**
 * TerminalPanel — placeholder for Phase 5 / Electron integration.
 *
 * When Electron IPC is wired up, this will spawn a PTY subprocess and
 * stream I/O through the preload bridge.
 */
export function TerminalPanel() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
      <Terminal className="h-8 w-8 opacity-30" />
      <p className="text-xs">Terminal coming in Phase 5 (Electron integration).</p>
    </div>
  );
}
