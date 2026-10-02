import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { DocumentStatus } from "../lib/types";

const STAGE_LABEL: Record<DocumentStatus, string> = {
  uploaded: "Queued",
  extracting: "Extracting",
  analyzing: "Analyzing risk",
  indexing: "Indexing",
  ready: "Ready",
  failed: "Failed",
};

export function StatusPill({ status }: { status: DocumentStatus }) {
  if (status === "ready") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-risk-low-soft px-2.5 py-1 text-xs font-medium text-risk-low">
        <CheckCircle2 size={13} strokeWidth={2.5} />
        Ready
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-risk-high-soft px-2.5 py-1 text-xs font-medium text-risk-high">
        <XCircle size={13} strokeWidth={2.5} />
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent">
      <Loader2 size={13} strokeWidth={2.5} className="animate-spin" />
      {STAGE_LABEL[status]}
    </span>
  );
}
