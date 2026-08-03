export type AnalysisType = "TEXT" | "URL" | "IMAGE" | "VIDEO";

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
  createdAt: string;
  updatedAt: string;
}

export type CreateAnalysisRequest = {
  input: string;
  file?: File | null;
  preferredLanguage: string;
};
