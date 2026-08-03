import { describe, expect, it } from "vitest";
import { validateIntake, validateSourceUrl } from "./validation";

describe("intake validation", () => {
  it("accepts public HTTP URLs and rejects unsupported protocols", () => {
    expect(validateSourceUrl("https://example.com/post")).toBe(true);
    expect(validateSourceUrl("file:///tmp/post")).toBe(false);
  });

  it("requires enough text to provide verification context", () => {
    expect(
      validateIntake({ input: "short", file: null }),
    ).toMatch(/claim or public URL/i);
    expect(
      validateIntake({ input: "A complete claim to verify", file: null }),
    ).toBeNull();
  });

  it("accepts an attachment with an optional prompt", () => {
    const image = new File(["image"], "evidence.png", { type: "image/png" });
    expect(validateIntake({ input: "", file: image })).toBeNull();
    expect(validateIntake({ input: "Check the date and location", file: image })).toBeNull();
  });

  it("rejects unsupported attachment types", () => {
    const textFile = new File(["hello"], "note.txt", { type: "text/plain" });
    expect(validateIntake({ input: "Check this", file: textFile })).toMatch(
      /valid image or video/i,
    );
  });
});
