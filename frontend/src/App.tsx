import { ThemeProvider } from "@/providers/ThemeProvider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { WorkspaceLayout } from "@/components/layout/WorkspaceLayout";
import { EditDialog } from "@/components/edit/EditDialog";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { ChatToggle } from "@/components/chat/ChatToggle";

export default function App() {
  return (
    <ThemeProvider>
      <TooltipProvider delayDuration={300}>
        <WorkspaceLayout />
        <EditDialog />
        <ChatPanel />
        <ChatToggle />
      </TooltipProvider>
    </ThemeProvider>
  );
}
