import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { Info } from "lucide-react";
import type { RiskDetail } from "../lib/types";
import { RiskBadge, riskColor } from "./RiskBadge";

const FEATURE_LABELS: Record<string, string> = {
  has_financials: "Financials section present",
  has_timeline: "Timeline section present",
  has_scope: "Scope section present",
  has_clearances: "Clearances section present",
  has_technical: "Technical section present",
  financial_numeric_density: "Costing figures quantified",
  clearance_keyword_density: "Clearance detail specificity",
  timeline_numeric_density: "Timeline detail specificity",
  scanned_page_ratio: "Scan quality (OCR reliance)",
  section_balance_std: "Section balance",
  page_count: "Document length",
  total_sections: "Section count",
  total_chars_log: "Content volume",
  avg_section_length_log: "Average section depth",
  financial_char_ratio: "Financials content share",
  timeline_char_ratio: "Timeline content share",
  scope_char_ratio: "Scope content share",
  clearances_char_ratio: "Clearances content share",
  technical_char_ratio: "Technical content share",
  other_char_ratio: "Unclassified content share",
  num_financial_sections: "Financial section count",
  num_clearance_sections: "Clearance section count",
};

export function RiskBreakdown({ risk }: { risk: RiskDetail }) {
  const chartData = [...risk.top_contributions]
    .sort((a, b) => a.shap_contribution - b.shap_contribution)
    .map((c) => ({
      name: FEATURE_LABELS[c.feature] ?? c.feature,
      value: Math.round(c.shap_contribution * 10) / 10,
    }));

  return (
    <div className="space-y-5">
      <div className="rounded-card border border-border bg-surface p-5 shadow-panel">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">Risk score</p>
            <div className="mt-1.5 flex items-baseline gap-2.5">
              <span className="font-mono text-4xl font-semibold tabular-nums" style={{ color: riskColor(risk.risk_bucket) }}>
                {risk.risk_score.toFixed(1)}
              </span>
              <span className="text-sm text-ink-faint">/ 100</span>
            </div>
          </div>
          <RiskBadge bucket={risk.risk_bucket} />
        </div>

        <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-canvas">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${risk.risk_score}%`, backgroundColor: riskColor(risk.risk_bucket) }}
          />
        </div>

        <div className="mt-3 flex gap-4 text-[11px] text-ink-faint">
          {(["low", "medium", "high"] as const).map((b) => (
            <span key={b} className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: riskColor(b) }} />
              {Math.round(risk.bucket_probabilities[b] * 100)}% {b}
            </span>
          ))}
        </div>
      </div>

      <div className="rounded-card border border-border bg-surface p-5 shadow-panel">
        <p className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">
          What's driving this score
        </p>
        <p className="mt-1 text-[12px] text-ink-muted">
          SHAP contributions computed for this document specifically — red pushes risk up, green pulls it down.
        </p>

        <div className="mt-3" style={{ height: Math.max(220, chartData.length * 34) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 16, top: 4, bottom: 4 }}>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="name"
                width={190}
                tick={{ fontSize: 11.5, fill: "var(--ink-muted)" }}
                axisLine={false}
                tickLine={false}
              />
              <Bar dataKey="value" radius={3} barSize={14}>
                {chartData.map((d, i) => (
                  <Cell key={i} fill={d.value >= 0 ? "#DB4C4C" : "#1FA97E"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="flex gap-2 rounded-card border border-border bg-canvas p-3.5 text-[12px] leading-relaxed text-ink-muted">
        <Info size={14} className="mt-0.5 shrink-0 text-ink-faint" />
        <p>{risk.methodology_note}</p>
      </div>
    </div>
  );
}
