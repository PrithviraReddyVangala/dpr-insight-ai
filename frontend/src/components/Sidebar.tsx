import { FileText, Moon, Sun, Trash2 } from "lucide-react";
import type { DocumentSummary } from "../lib/types";
import { StatusPill } from "./StatusPill";
import { RiskBadge } from "./RiskBadge";
import { UploadZone } from "./UploadZone";

interface Props {
  documents: DocumentSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onUpload: (file: File) => void;
  onDelete: (id: string) => void;
  dark: boolean;
  onToggleDark: () => void;
}

export function Sidebar({ documents, activeId, onSelect, onUpload, onDelete, dark, onToggleDark }: Props) {
  return (
    <aside className="flex h-full w-[300px] shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center justify-between px-5 py-4">
        <div>
          <p className="text-[13px] font-semibold tracking-tight text-ink">DPR Insight AI</p>
          <p className="text-[11px] text-ink-faint">Document workspace</p>
        </div>
        <button
          onClick={onToggleDark}
          className="flex h-7 w-7 items-center justify-center rounded-md text-ink-muted hover:bg-canvas hover:text-ink"
          aria-label="Toggle theme"
        >
          {dark ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>

      <div className="px-4 pb-4">
        <UploadZone onUpload={onUpload} />
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <p className="px-2 pb-2 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
          {documents.length === 0 ? "No documents yet" : `${documents.length} document${documents.length === 1 ? "" : "s"}`}
        </p>
        <div className="space-y-1">
          {documents.map((doc) => (
            <button
              key={doc.id}
              onClick={() => onSelect(doc.id)}
              className={`group flex w-full flex-col gap-1.5 rounded-lg px-3 py-2.5 text-left transition-colors ${
                activeId === doc.id ? "bg-accent-soft" : "hover:bg-canvas"
              }`}
            >
              <div className="flex items-start gap-2">
                <FileText size={14} className="mt-0.5 shrink-0 text-ink-faint" />
                <span className="line-clamp-2 flex-1 text-[13px] font-medium leading-snug text-ink">
                  {doc.original_filename}
                </span>
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(doc.id);
                  }}
                  className="shrink-0 rounded p-0.5 text-ink-faint opacity-0 hover:text-risk-high group-hover:opacity-100"
                >
                  <Trash2 size={13} />
                </span>
              </div>
              <div className="flex items-center gap-1.5 pl-[22px]">
                {doc.status === "ready" && doc.risk_bucket ? (
                  <RiskBadge bucket={doc.risk_bucket} size="sm" />
                ) : (
                  <StatusPill status={doc.status} />
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
