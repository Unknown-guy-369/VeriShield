export type AnalysisType = "TEXT" | "URL" | "IMAGE" | "VIDEO";

export type TextAnalysisResult = {
  claims: Array<{ id: string; text: string; normalized_text?: string }>;
  evidence: Array<{
    id: string;
    claim_id: string;
    stance: "supported" | "contradicted" | "insufficient" | "unrelated";
    title: string;
    publisher?: string | null;
    url: string;
    passage: string;
    source_reliability?: number;
    retrieval_confidence?: number;
    provider_name?: string;
  }>;
  stances: Array<{
    claim_id: string;
    stance: "supported" | "contradicted" | "insufficient" | "unrelated";
    evidence_count: number;
    reasoning?: string;
  }>;
  scores: Array<{
    claim_id: string;
    score: number;
    reasoning?: string;
    formula?: string;
  }>;
};

export interface AnalysisRecord {
  id: string;
  type: AnalysisType;
  status: string;
  progress: number;
  preferredLanguage: string;
  text?: string;
  sourceUrl?: string;
  originalFileName?: string;
  mimeType?: string;
  fileSize?: number;
  storagePath?: string;
  result?: TextAnalysisResult | null;
  createdAt: string;
  updatedAt: string;
}

export type CreateAnalysisRequest = {
  input: string;
  file?: File | null;
  preferredLanguage: string;
};
