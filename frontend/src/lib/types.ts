export type RiskBucket = "low" | "medium" | "high";

export type DocumentStatus =
  | "uploaded"
  | "extracting"
  | "analyzing"
  | "indexing"
  | "ready"
  | "failed";

export interface DocumentSummary {
  id: string;
  original_filename: string;
  status: DocumentStatus;
  progress_stage: string | null;
  progress_pct: number;
  progress_message: string | null;
  error_message: string | null;
  page_count: number | null;
  scanned_page_count: number | null;
  section_count: number | null;
  risk_score: number | null;
  risk_bucket: RiskBucket | null;
  extraction_warnings: string[];
  created_at: number;
}

export interface SectionOut {
  heading_text: string;
  category: string;
  page_start: number;
  page_end: number;
  char_count: number;
  text: string;
}

export interface DocumentDetail extends DocumentSummary {
  sections: SectionOut[];
}

export interface FeatureContribution {
  feature: string;
  value: number;
  shap_contribution: number;
}

export interface RiskDetail {
  risk_score: number;
  risk_bucket: RiskBucket;
  bucket_probabilities: Record<RiskBucket, number>;
  top_contributions: FeatureContribution[];
  base_value: number;
  methodology_note: string;
}

export interface RetrievedChunk {
  text: string;
  source_file: string;
  heading_text: string;
  category: string;
  page_start: number;
  page_end: number;
  similarity: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  chunks?: RetrievedChunk[];
  error?: boolean;
}

export const CATEGORY_LABELS: Record<string, string> = {
  financials: "Financials",
  timeline: "Timeline",
  scope: "Scope",
  clearances: "Clearances",
  technical: "Technical",
  other: "Other",
};
