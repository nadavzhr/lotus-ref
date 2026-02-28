import { useState } from "react";
import { ChevronRight, GitMerge } from "lucide-react";
import { useDocumentStore } from "@/stores/document-store";
import { useTabsStore } from "@/stores/tabs-store";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* Derived types                                                       */
/* ------------------------------------------------------------------ */

interface PeerEntry {
  position: number;
  rawText: string;
  sharedNets: string[];
}

interface ConflictGroup {
  docId: string;
  filePath: string;
  position: number;
  rawText: string;
  peers: PeerEntry[];
}

interface SelectedPair {
  rootKey: string; // `${docId}-${position}`
  peerPos: number;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function basename(p: string) {
  return p.split(/[\\/]/).pop() ?? p;
}

function truncate(s: string, n = 48) {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

const CONFLICT_COLOR = "hsl(280 80% 60%)";

/* ------------------------------------------------------------------ */
/* Left pane — tree                                                    */
/*                                                                     */
/* Each root = a conflicting line.                                     */
/* Its children = the peer lines it conflicts with.                   */
/* Clicking a peer populates the right pane.                          */
/* ------------------------------------------------------------------ */

interface TreeProps {
  groups: ConflictGroup[];
  expandedRoots: Set<string>;
  selectedPair: SelectedPair | null;
  onToggleRoot: (key: string) => void;
  onSelectPeer: (pair: SelectedPair) => void;
  onNavigate: (docId: string, position: number) => void;
}

function ConflictTree({
  groups,
  expandedRoots,
  selectedPair,
  onToggleRoot,
  onSelectPeer,
  onNavigate,
}: TreeProps) {
  return (
    <div className="flex h-full flex-col border-r">
      {/* header */}
      <div className="flex shrink-0 items-center gap-2 border-b px-3 py-1 text-[11px] text-muted-foreground">
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ background: CONFLICT_COLOR }}
          aria-hidden
        />
        {groups.length} conflicting line{groups.length !== 1 ? "s" : ""}
      </div>

      <div className="flex-1 overflow-y-auto">
        {groups.map((g) => {
          const rootKey = `${g.docId}-${g.position}`;
          const expanded = expandedRoots.has(rootKey);
          const file = basename(g.filePath);

          return (
            <div key={rootKey}>
              {/* ── Root row ── */}
              <button
                onClick={() => onToggleRoot(rootKey)}
                className={cn(
                  "flex w-full items-center gap-1.5 border-l-2 px-2 py-1.5 text-left transition-colors",
                  "focus-visible:outline-none focus-visible:bg-accent/40",
                  "hover:bg-accent/20",
                  expanded ? "border-l-[hsl(280_80%_60%)]" : "border-l-transparent",
                )}
              >
                <ChevronRight
                  className={cn(
                    "h-3 w-3 shrink-0 text-muted-foreground transition-transform",
                    expanded && "rotate-90",
                  )}
                />
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: CONFLICT_COLOR }}
                  aria-hidden
                />
                {/* jumpable line ref */}
                <span
                  className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground underline-offset-2 hover:underline"
                  onClick={(e) => {
                    e.stopPropagation();
                    onNavigate(g.docId, g.position);
                  }}
                  title={`Jump to line ${g.position + 1}`}
                >
                  {file}:{g.position + 1}
                </span>
                <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-foreground/70">
                  {truncate(g.rawText)}
                </span>
                <span className="shrink-0 text-[10px] text-muted-foreground">
                  {g.peers.length}×
                </span>
              </button>

              {/* ── Peer children ── */}
              {expanded &&
                g.peers.map((peer) => {
                  const isActive =
                    selectedPair?.rootKey === rootKey &&
                    selectedPair.peerPos === peer.position;
                  return (
                    <button
                      key={peer.position}
                      onClick={() =>
                        onSelectPeer({ rootKey, peerPos: peer.position })
                      }
                      className={cn(
                        "flex w-full items-center gap-1.5 border-l-2 py-1 pl-7 pr-2 text-left transition-colors",
                        "focus-visible:outline-none",
                        isActive
                          ? "bg-accent/40 border-l-[hsl(280_80%_60%)]"
                          : "border-l-transparent hover:bg-accent/20",
                      )}
                    >
                      <span className="shrink-0 text-[10px] text-muted-foreground">↔</span>
                      <span
                        className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground underline-offset-2 hover:underline"
                        onClick={(e) => {
                          e.stopPropagation();
                          onNavigate(g.docId, peer.position);
                        }}
                        title={`Jump to line ${peer.position + 1}`}
                      >
                        {file}:{peer.position + 1}
                      </span>
                      <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-foreground/60">
                        {truncate(peer.rawText, 30)}
                      </span>
                      <span className="shrink-0 text-[10px] text-muted-foreground">
                        {peer.sharedNets.length}
                      </span>
                    </button>
                  );
                })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Right pane — shared nets for the selected (root, peer) pair        */
/* ------------------------------------------------------------------ */

interface NetListProps {
  group: ConflictGroup;
  peer: PeerEntry;
  onNavigate: (docId: string, position: number) => void;
}

function NetList({ group, peer, onNavigate }: NetListProps) {
  const file = basename(group.filePath);

  return (
    <div className="flex h-full flex-col">
      {/* header */}
      <div className="flex shrink-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 border-b px-3 py-1 text-[11px] text-muted-foreground">
        <span>Shared nets:</span>
        <button
          className="font-mono tabular-nums underline-offset-2 hover:underline focus-visible:outline-none"
          onClick={() => onNavigate(group.docId, group.position)}
          title="Jump to this line"
        >
          {file}:{group.position + 1}
        </button>
        <span className="text-muted-foreground/50">↔</span>
        <button
          className="font-mono tabular-nums underline-offset-2 hover:underline focus-visible:outline-none"
          onClick={() => onNavigate(group.docId, peer.position)}
          title="Jump to peer line"
        >
          {file}:{peer.position + 1}
        </button>
        <span className="ml-auto shrink-0 tabular-nums">
          {peer.sharedNets.length} total
        </span>
      </div>

      {/* net list */}
      <div className="flex-1 overflow-y-auto px-3 py-1.5">
        {peer.sharedNets.length === 0 ? (
          <span className="text-[11px] text-muted-foreground">No net info available.</span>
        ) : (
          peer.sharedNets.map((net, i) => (
            <div
              key={i}
              className="py-px font-mono text-[11px] leading-5 text-foreground"
            >
              {net}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* ConflictsPanel                                                      */
/* ------------------------------------------------------------------ */

export function ConflictsPanel() {
  const documents = useDocumentStore((s) => s.documents);
  const selectLine = useDocumentStore((s) => s.selectLine);
  const setActive = useTabsStore((s) => s.setActive);

  // Build conflict groups
  const groups: ConflictGroup[] = [];
  for (const [docId, doc] of Object.entries(documents)) {
    const textByPos = new Map(doc.lines.map((l) => [l.position, l.raw_text]));
    for (const line of doc.lines) {
      if (!line.is_conflict || !line.conflict_info) continue;
      groups.push({
        docId,
        filePath: doc.filePath,
        position: line.position,
        rawText: line.raw_text,
        peers: line.conflict_info.peers.map((p) => ({
          position: p.position,
          rawText: textByPos.get(p.position) ?? "",
          sharedNets: p.shared_nets,
        })),
      });
    }
  }

  // Auto-expand the first root by default
  const firstKey =
    groups.length > 0 ? `${groups[0].docId}-${groups[0].position}` : null;

  const [expandedRoots, setExpandedRoots] = useState<Set<string>>(
    () => new Set(firstKey ? [firstKey] : []),
  );
  const [selectedPair, setSelectedPair] = useState<SelectedPair | null>(
    () =>
      groups[0]?.peers[0]
        ? { rootKey: firstKey!, peerPos: groups[0].peers[0].position }
        : null,
  );

  const handleToggleRoot = (key: string) => {
    setExpandedRoots((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const handleNavigate = (docId: string, position: number) => {
    setActive(docId);
    selectLine(docId, position);
  };

  if (groups.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-1.5 text-muted-foreground">
        <GitMerge className="h-7 w-7 opacity-25" />
        <span className="text-xs">No conflicts detected.</span>
      </div>
    );
  }

  // Resolve selected pair to actual data
  const activeGroup = selectedPair
    ? groups.find((g) => `${g.docId}-${g.position}` === selectedPair.rootKey) ?? null
    : null;
  const activePeer = activeGroup
    ? activeGroup.peers.find((p) => p.position === selectedPair!.peerPos) ?? null
    : null;

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left 40%: tree */}
      <div className="w-[40%] shrink-0">
        <ConflictTree
          groups={groups}
          expandedRoots={expandedRoots}
          selectedPair={selectedPair}
          onToggleRoot={handleToggleRoot}
          onSelectPeer={setSelectedPair}
          onNavigate={handleNavigate}
        />
      </div>

      {/* Right 60%: net list */}
      <div className="flex-1 overflow-hidden">
        {activeGroup && activePeer ? (
          <NetList group={activeGroup} peer={activePeer} onNavigate={handleNavigate} />
        ) : (
          <div className="flex h-full items-center justify-center text-[11px] text-muted-foreground">
            Select a peer to see shared nets.
          </div>
        )}
      </div>
    </div>
  );
}
