import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { SectionOut } from "../lib/types";
import { CATEGORY_LABELS } from "../lib/types";

const CATEGORY_ORDER = ["financials", "timeline", "scope", "clearances", "technical", "other"];
const CATEGORY_COLOR: Record<string, string> = {
  financials: "#1FA97E",
  timeline: "#4F5BD5",
  scope: "#8B5CF6",
  clearances: "#D6970B",
  technical: "#2AA9C2",
  other: "#8B8B93",
};

export function SectionsView({ sections }: { sections: SectionOut[] }) {
  const [openCategory, setOpenCategory] = useState<string | null>(null);
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const grouped = CATEGORY_ORDER.map((cat) => ({
    category: cat,
    items: sections
      .map((s, i) => ({ ...s, idx: i }))
      .filter((s) => s.category === cat),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-3">
      {grouped.map((group) => {
        const totalChars = group.items.reduce((sum, s) => sum + s.char_count, 0);
        const isOpen = openCategory === group.category;
        return (
          <div key={group.category} className="overflow-hidden rounded-card border border-border bg-surface shadow-panel">
            <button
              onClick={() => setOpenCategory(isOpen ? null : group.category)}
              className="flex w-full items-center justify-between px-4 py-3"
            >
              <div className="flex items-center gap-2.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: CATEGORY_COLOR[group.category] }} />
                <span className="text-[13px] font-medium text-ink">{CATEGORY_LABELS[group.category]}</span>
                <span className="rounded-full bg-canvas px-2 py-0.5 font-mono text-[11px] text-ink-faint">
                  {group.items.length}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-[11px] text-ink-faint">
                  {totalChars.toLocaleString()} chars
                </span>
                <ChevronDown size={14} className={`text-ink-faint transition-transform ${isOpen ? "rotate-180" : ""}`} />
              </div>
            </button>

            {isOpen && (
              <div className="border-t border-border">
                {group.items.map((s) => (
                  <div key={s.idx} className="border-b border-border last:border-b-0">
                    <button
                      onClick={() => setOpenIdx(openIdx === s.idx ? null : s.idx)}
                      className="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-canvas/60"
                    >
                      <span className="text-[12.5px] text-ink-muted">{s.heading_text || "(untitled)"}</span>
                      <span className="shrink-0 pl-3 font-mono text-[11px] text-ink-faint">
                        p{s.page_start + 1}–{s.page_end + 1}
                      </span>
                    </button>
                    {openIdx === s.idx && (
                      <div className="max-h-64 overflow-y-auto whitespace-pre-wrap bg-canvas/50 px-4 py-3 font-mono text-[11.5px] leading-relaxed text-ink-muted">
                        {s.text.slice(0, 4000) || "(no extracted text)"}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
