import { useEffect, useState } from "react";
import { FileWarning, Layers, ShieldAlert } from "lucide-react";
import { api } from "../lib/api";
import type { DocumentDetail, DocumentSummary, RiskDetail } from "../lib/types";
import { StatusPill } from "./StatusPill";
import { PdfPreview } from "./PdfPreview";
import { RiskBreakdown } from "./RiskBreakdown";
import { SectionsView } from "./SectionsView";
import { ChatDrawer } from "./ChatDrawer";

type Tab = "risk" | "sections";

export function Workspace({ summary }: { summary: DocumentSummary }) {
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [risk, setRisk] = useState<RiskDetail | null>(null);
  const [tab, setTab] = useState<Tab>("risk");

  useEffect(() => {
    setDetail(null);
    setRisk(null);
    if (summary.status !== "ready") return;
    api.getDetail(summary.id).then(setDetail);
    api.getRisk(summary.id).then(setRisk);
  }, [summary.id, summary.status]);

  if (summary.status === "failed") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <FileWarning size={28} className="text-risk-high" />
        <div>
          <p className="text-sm font-medium text-ink">Extraction failed</p>
          <p className="mt-1 max-w-sm text-[13px] text-ink-muted">{summary.error_message}</p>
        </div>
      </div>
    );
  }

  if (summary.status !== "ready" || !detail || !risk) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        <div className="text-center">
          <p className="text-sm font-medium text-ink">{summary.progress_message ?? "Processing…"}</p>
          <p className="mt-1 text-[12px] text-ink-faint">{Math.round(summary.progress_pct)}% complete</p>
        </div>
        <div className="h-1.5 w-64 overflow-hidden rounded-full bg-canvas">
          <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${summary.progress_pct}%` }} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="min-w-0">
          <h1 className="truncate text-[15px] font-semibold text-ink">{detail.original_filename}</h1>
          <div className="mt-1 flex items-center gap-3 font-mono text-[11px] text-ink-faint">
            <span>{detail.page_count} pages</span>
            <span>·</span>
            <span>{detail.section_count} sections</span>
            {detail.scanned_page_count! > 0 && (
              <>
                <span>·</span>
                <span>{detail.scanned_page_count} OCR'd</span>
              </>
            )}
          </div>
        </div>
        <StatusPill status={detail.status} />
      </header>

      {detail.extraction_warnings.length > 0 && (
        <div className="mx-6 mt-4 flex items-start gap-2 rounded-lg border border-risk-medium/30 bg-risk-medium-soft px-3.5 py-2.5 text-[12px] text-risk-medium">
          <FileWarning size={14} className="mt-0.5 shrink-0" />
          <div className="space-y-0.5">
            {detail.extraction_warnings.map((w, i) => (
              <p key={i}>{w}</p>
            ))}
          </div>
        </div>
      )}

      <div className="grid flex-1 grid-cols-2 gap-5 overflow-hidden p-6">
        <PdfPreview fileUrl={api.fileUrl(detail.id)} />

        <div className="flex flex-col overflow-hidden">
          <div className="mb-4 flex gap-1 rounded-lg bg-canvas p-1">
            <TabButton active={tab === "risk"} onClick={() => setTab("risk")} icon={<ShieldAlert size={14} />} label="Risk" />
            <TabButton active={tab === "sections"} onClick={() => setTab("sections")} icon={<Layers size={14} />} label="Sections" />
          </div>
          <div className="flex-1 overflow-y-auto pr-1">
            {tab === "risk" ? <RiskBreakdown risk={risk} /> : <SectionsView sections={detail.sections} />}
          </div>
        </div>
      </div>

      <ChatDrawer documentId={detail.id} docName={detail.original_filename} />
    </div>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-[12.5px] font-medium transition-colors ${
        active ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
