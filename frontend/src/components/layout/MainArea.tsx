import { useTabsStore } from "@/stores/tabs-store";
import { useDocumentStore } from "@/stores/document-store";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { X, FileText } from "lucide-react";
import { DocumentViewer } from "@/components/document/DocumentViewer";

/**
 * MainArea — tabbed document viewer.
 * Renders open document tabs with DocumentViewer content.
 */
export function MainArea() {
  const tabs = useTabsStore((s) => s.tabs);
  const activeTabId = useTabsStore((s) => s.activeTabId);
  const setActive = useTabsStore((s) => s.setActive);
  const closeTab = useTabsStore((s) => s.closeTab);
  const closeDocument = useDocumentStore((s) => s.closeDocument);

  const handleCloseTab = (id: string) => {
    closeTab(id);
    closeDocument(id);
  };

  if (tabs.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
        <FileText className="h-12 w-12 opacity-30" />
        <p className="text-sm">No documents open</p>
        <p className="text-xs">
          Load a document to get started.
        </p>
      </div>
    );
  }

  return (
    <Tabs
      value={activeTabId ?? undefined}
      onValueChange={setActive}
      className="flex flex-1 flex-col overflow-hidden"
    >
      {/* Tab strip */}
      <TabsList className="h-9 shrink-0 justify-start rounded-none border-b bg-muted/50">
        {tabs.map((tab) => (
          <TabsTrigger
            key={tab.id}
            value={tab.id}
            className="group relative gap-1.5 pr-7 text-xs"
          >
            <span className="truncate max-w-[160px]">{tab.label}</span>
            <span className="rounded px-1 text-2xs text-muted-foreground">
              {tab.docType.toUpperCase()}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              className="absolute right-0.5 top-1/2 h-4 w-4 -translate-y-1/2 opacity-0 group-hover:opacity-100"
              onClick={(e) => {
                e.stopPropagation();
                handleCloseTab(tab.id);
              }}
              aria-label={`Close ${tab.label}`}
            >
              <X className="h-3 w-3" />
            </Button>
          </TabsTrigger>
        ))}
      </TabsList>

      {/* Tab content areas — each tab hosts a DocumentViewer */}
      {tabs.map((tab) => (
        <TabsContent
          key={tab.id}
          value={tab.id}
          className="flex-1 overflow-hidden p-0"
        >
          <DocumentViewer docId={tab.id} />
        </TabsContent>
      ))}
    </Tabs>
  );
}
