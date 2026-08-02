import { describe, expect, it } from "vitest";
import { validateIntake, validateSourceUrl } from "./validation";

describe("intake validation", () => {
  it("accepts public HTTP URLs and rejects unsupported protocols", () => {
    expect(validateSourceUrl("https://example.com/post")).toBe(true);
    expect(validateSourceUrl("file:///tmp/post")).toBe(false);
  });

  it("requires enough text to provide verification context", () => {
    expect(
      validateIntake({ type: "TEXT", text: "short", sourceUrl: "", file: null }),
    ).toMatch(/at least 10/i);
    expect(
      validateIntake({
        type: "TEXT",
        text: "A complete claim to verify",
        sourceUrl: "",
        file: null,
      }),
    ).toBeNull();
  });

  it("requires media that matches the selected mode", () => {
    const textFile = new File(["hello"], "note.txt", { type: "text/plain" });
    expect(
      validateIntake({ type: "IMAGE", text: "", sourceUrl: "", file: textFile }),
    ).toMatch(/valid image/i);
  });
});
