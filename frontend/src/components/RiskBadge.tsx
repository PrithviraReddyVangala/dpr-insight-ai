import type { RiskBucket } from "../lib/types";

const CONFIG: Record<RiskBucket, { label: string; text: string; bg: string; ring: string }> = {
  low: { label: "Low risk", text: "text-risk-low", bg: "bg-risk-low-soft", ring: "ring-risk-low/25" },
  medium: { label: "Medium risk", text: "text-risk-medium", bg: "bg-risk-medium-soft", ring: "ring-risk-medium/25" },
  high: { label: "High risk", text: "text-risk-high", bg: "bg-risk-high-soft", ring: "ring-risk-high/25" },
};

export function RiskBadge({ bucket, size = "md" }: { bucket: RiskBucket; size?: "sm" | "md" }) {
  const c = CONFIG[bucket];
  const pad = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";
  return (
    <span className={`inline-flex items-center rounded-full ring-1 font-semibold ${c.bg} ${c.text} ${c.ring} ${pad}`}>
      {c.label}
    </span>
  );
}

export function riskColor(bucket: RiskBucket): string {
  return { low: "#1FA97E", medium: "#D6970B", high: "#DB4C4C" }[bucket];
}
