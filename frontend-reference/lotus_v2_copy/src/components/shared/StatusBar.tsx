import { cn } from "@/lib/utils"

interface StatusBarProps {
  className?: string
}

export function StatusBar({ className }: StatusBarProps) {
  return (
    <div className={cn(
      "flex items-center justify-between px-3 py-0.5 bg-primary text-primary-foreground text-[10px] shrink-0",
      className
    )}>
      <div className="flex items-center gap-3">
        <span>Lotus v2.0.0-dev</span>
        <span>|</span>
        <span>AF: my_block.af.dcfg</span>
      </div>
      <div className="flex items-center gap-3">
        <span>20 lines</span>
        <span>|</span>
        <span>Netlist: 523,841 nets</span>
      </div>
    </div>
  )
}
