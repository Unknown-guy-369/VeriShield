export const MAX_TEXT_LENGTH = 10_000;
export const MAX_IMAGE_BYTES = 15 * 1024 * 1024;
export const MAX_VIDEO_BYTES = 150 * 1024 * 1024;

export type IntakeDraft = {
  input: string;
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
  const length = draft.input.trim().length;
  if (!draft.file) {
    if (length < 10) {
      return "Enter a claim or public URL with at least 10 characters, or attach media.";
    }
    if (length > MAX_TEXT_LENGTH) {
      return `Keep the text under ${MAX_TEXT_LENGTH.toLocaleString()} characters.`;
    }
    return null;
  }

  if (length > MAX_TEXT_LENGTH) {
    return `Keep the prompt under ${MAX_TEXT_LENGTH.toLocaleString()} characters.`;
  }

  const isImage = draft.file.type.startsWith("image/");
  const isVideo = draft.file.type.startsWith("video/");
  if (!isImage && !isVideo) {
    return "Attach a valid image or video file.";
  }

  const limit = isImage ? MAX_IMAGE_BYTES : MAX_VIDEO_BYTES;
  if (draft.file.size > limit) {
    return `${isImage ? "Images" : "Videos"} must be smaller than ${
      limit / 1024 / 1024
    } MB.`;
  }

  return null;
}
