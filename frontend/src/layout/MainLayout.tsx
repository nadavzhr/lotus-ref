import { TopToolbar } from "@/components/TopToolbar"
import { DocumentViewer } from "@/components/DocumentViewer"
import { BottomPanel } from "@/components/BottomPanel"
import { StatusBar } from "@/components/StatusBar"
import { EditDialog } from "@/components/EditDialog"
import type { DocumentLine } from "@/types/api"

interface MainLayoutProps {
  lines: DocumentLine[]
}

export function MainLayout({ lines }: MainLayoutProps) {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopToolbar />

      <DocumentViewer lines={lines} />

      <BottomPanel />

      <StatusBar />

      <EditDialog lines={lines} />
    </div>
  )
}
