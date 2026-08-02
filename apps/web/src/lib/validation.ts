import type { AnalysisType } from "@/lib/analysis";

export const MAX_TEXT_LENGTH = 10_000;
export const MAX_IMAGE_BYTES = 15 * 1024 * 1024;
export const MAX_VIDEO_BYTES = 150 * 1024 * 1024;

export type IntakeDraft = {
  type: AnalysisType;
  text: string;
  sourceUrl: string;
  file: File | null;
};

export function validateSourceUrl(value: string) {
  try {
    const parsed = new URL(value.trim());
    return (
      (parsed.protocol === "https:" || parsed.protocol === "http:") &&
      Boolean(parsed.hostname)
    );
  } catch {
    return false;
  }
}

export function validateIntake(draft: IntakeDraft): string | null {
  if (draft.type === "TEXT") {
    const length = draft.text.trim().length;
    if (length < 10) {
      return "Enter at least 10 characters so there is enough context to analyze.";
    }
    if (length > MAX_TEXT_LENGTH) {
      return `Keep the text under ${MAX_TEXT_LENGTH.toLocaleString()} characters.`;
    }
    return null;
  }

  if (draft.type === "URL") {
    return validateSourceUrl(draft.sourceUrl)
      ? null
      : "Enter a complete public URL beginning with http:// or https://.";
  }

  if (!draft.file) {
    return `Choose ${draft.type === "IMAGE" ? "an image" : "a video"} to analyze.`;
  }

  const expectsImage = draft.type === "IMAGE";
  const expectedPrefix = expectsImage ? "image/" : "video/";
  if (!draft.file.type.startsWith(expectedPrefix)) {
    return `Choose a valid ${expectsImage ? "image" : "video"} file.`;
  }

  const limit = expectsImage ? MAX_IMAGE_BYTES : MAX_VIDEO_BYTES;
  if (draft.file.size > limit) {
    return `${expectsImage ? "Images" : "Videos"} must be smaller than ${
      limit / 1024 / 1024
    } MB.`;
  }

  return null;
}
