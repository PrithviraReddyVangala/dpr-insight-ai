import { FileSearch } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent">
        <FileSearch size={22} />
      </div>
      <div>
        <p className="text-sm font-medium text-ink">No document open</p>
        <p className="mt-1 max-w-xs text-[13px] text-ink-muted">
          Upload a DPR from the sidebar to see its risk breakdown, sections, and ask it questions directly.
        </p>
      </div>
    </div>
  );
}
