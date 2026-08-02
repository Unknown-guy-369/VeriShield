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

export type TextAnalysisRequest = {
  type: "TEXT";
  text: string;
  preferredLanguage: string;
};

export type UrlAnalysisRequest = {
  type: "URL";
  sourceUrl: string;
  preferredLanguage: string;
};

export type MediaAnalysisRequest = {
  type: "IMAGE" | "VIDEO";
  file: File;
  preferredLanguage: string;
};

export type CreateAnalysisRequest =
  | TextAnalysisRequest
  | UrlAnalysisRequest
  | MediaAnalysisRequest;
