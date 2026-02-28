import {
  Menubar,
  MenubarContent,
  MenubarItem,
  MenubarMenu,
  MenubarSeparator,
  MenubarShortcut,
  MenubarTrigger,
} from "@/components/ui/menubar"
import { Flower2, Sun, Moon, MessageSquare } from "lucide-react"
import { useTheme } from "@/hooks/useTheme"

interface TopMenuBarProps {
  showChat: boolean
  onToggleChat: () => void
}

export function TopMenuBar({ showChat, onToggleChat }: TopMenuBarProps) {
  const { theme, toggleTheme } = useTheme()
  return (
    <div className="flex items-center border-b bg-background px-2 h-10 shrink-0">
      <div className="flex items-center gap-2 mr-3 pl-1">
        <Flower2 className="h-5 w-5 text-primary" />
        <span className="font-semibold text-sm tracking-tight">Lotus v2</span>
      </div>

      <Menubar className="border-none bg-transparent shadow-none h-8 p-0">
        <MenubarMenu>
          <MenubarTrigger className="text-xs font-medium px-2.5 py-1 h-7">File</MenubarTrigger>
          <MenubarContent>
            <MenubarItem>
              Open <MenubarShortcut>Ctrl+O</MenubarShortcut>
            </MenubarItem>
            <MenubarItem>
              Save <MenubarShortcut>Ctrl+S</MenubarShortcut>
            </MenubarItem>
            <MenubarItem>
              Save As… <MenubarShortcut>Ctrl+Shift+S</MenubarShortcut>
            </MenubarItem>
            <MenubarSeparator />
            <MenubarItem>
              Quit <MenubarShortcut>Ctrl+Q</MenubarShortcut>
            </MenubarItem>
          </MenubarContent>
        </MenubarMenu>

        <MenubarMenu>
          <MenubarTrigger className="text-xs font-medium px-2.5 py-1 h-7">Edit</MenubarTrigger>
          <MenubarContent>
            <MenubarItem>
              Undo <MenubarShortcut>Ctrl+Z</MenubarShortcut>
            </MenubarItem>
            <MenubarItem>
              Redo <MenubarShortcut>Ctrl+Y</MenubarShortcut>
            </MenubarItem>
            <MenubarSeparator />
            <MenubarItem>Insert Line</MenubarItem>
            <MenubarItem>Delete Line</MenubarItem>
          </MenubarContent>
        </MenubarMenu>

        <MenubarMenu>
          <MenubarTrigger className="text-xs font-medium px-2.5 py-1 h-7">View</MenubarTrigger>
          <MenubarContent>
            <MenubarItem>Toggle Problems Panel</MenubarItem>
            <MenubarItem>Toggle Log Panel</MenubarItem>
            <MenubarSeparator />
            <MenubarItem>Zoom In</MenubarItem>
            <MenubarItem>Zoom Out</MenubarItem>
            <MenubarItem>Reset Zoom</MenubarItem>
          </MenubarContent>
        </MenubarMenu>

        <MenubarMenu>
          <MenubarTrigger className="text-xs font-medium px-2.5 py-1 h-7">Help</MenubarTrigger>
          <MenubarContent>
            <MenubarItem>Keyboard Shortcuts</MenubarItem>
            <MenubarItem>About Lotus</MenubarItem>
          </MenubarContent>
        </MenubarMenu>
      </Menubar>

      {/* Right-side status area */}
      <div className="ml-auto flex items-center gap-3 pr-2">
        <span className="text-xs text-muted-foreground font-mono">
          ward: /path/to/ward
        </span>
        <span className="text-xs text-muted-foreground">|</span>
        <span className="text-xs text-muted-foreground font-mono">
          cell: my_block
        </span>
        <span className="text-xs text-muted-foreground">|</span>
        <button
          onClick={toggleTheme}
          className="p-1 rounded-md hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </button>
        <button
          onClick={onToggleChat}
          className={`p-1 rounded-md transition-colors ${
            showChat
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          }`}
          title={showChat ? "Hide AI Chat" : "Show AI Chat"}
        >
          <MessageSquare className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
