import type {
  AnalysisRecord,
  AnalysisType,
  CreateAnalysisRequest,
} from "@/lib/analysis";

const DEFAULT_API_BASE_URL = "http://localhost:4000";
const REQUEST_TIMEOUT_MS = 30_000;

export type ApiErrorCode =
  | "NETWORK"
  | "TIMEOUT"
  | "HTTP"
  | "INVALID_RESPONSE";

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly code: ApiErrorCode,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(
    /\/$/,
    "",
  );
}

function isAnalysisType(value: unknown): value is AnalysisType {
  return ["TEXT", "URL", "IMAGE", "VIDEO"].includes(String(value));
}
function toAnalysisRecord(value: unknown): AnalysisRecord {
  if (!value || typeof value !== "object") {
    throw new ApiClientError(
      "The analysis service returned an unreadable response.",
      "INVALID_RESPONSE",
    );
  }

  const record = value as Record<string, unknown>;
  if (
    typeof record.id !== "string" ||
    !isAnalysisType(record.type) ||
    typeof record.status !== "string" ||
    typeof record.progress !== "number" ||
    typeof record.preferredLanguage !== "string" ||
    typeof record.createdAt !== "string" ||
    typeof record.updatedAt !== "string"
  ) {
    throw new ApiClientError(
      "The analysis service returned an incomplete response.",
      "INVALID_RESPONSE",
    );
  }

  return value as AnalysisRecord;
}

async function readPublicError(response: Response) {
  try {
    const body = (await response.json()) as { message?: string | string[] };
    const message = Array.isArray(body.message)
      ? body.message.join(" ")
      : body.message;
    return message || "The analysis service could not accept this request.";
  } catch {
    return "The analysis service could not accept this request.";
  }
}

async function requestRecord(path: string, init?: RequestInit) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    });

    if (!response.ok) {
      throw new ApiClientError(
        await readPublicError(response),
        "HTTP",
        response.status,
      );
    }

    return toAnalysisRecord(await response.json());
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiClientError(
        "The analysis service took too long to respond.",
        "TIMEOUT",
      );
    }
    throw new ApiClientError(
      "The analysis API is unavailable. Check that the backend is running and try again.",
      "NETWORK",
    );
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function createAnalysis(input: CreateAnalysisRequest) {
  if (input.type === "TEXT" || input.type === "URL") {
    return requestRecord("/api/v1/analyses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  }

  const formData = new FormData();
  formData.append("type", input.type);
  formData.append("preferredLanguage", input.preferredLanguage);
  formData.append("file", input.file);

  return requestRecord("/api/v1/analyses", {
    method: "POST",
    body: formData,
  });
}

export async function getAnalysis(id: string) {
  return requestRecord(`/api/v1/analyses/${encodeURIComponent(id)}`);
}
