import { describe, expect, it } from "vitest";
import { validatePdf } from "./files";

describe("validatePdf", () => {
  it("accepts a normal PDF", () => {
    expect(validatePdf({ name: "a.pdf", type: "application/pdf", size: 1000 })).toBeNull();
  });
  it("accepts .pdf even when the browser gives no MIME type", () => {
    expect(validatePdf({ name: "A.PDF", type: "", size: 1000 })).toBeNull();
  });
  it("rejects other types", () => {
    expect(validatePdf({ name: "a.docx", type: "application/msword", size: 1000 })).toMatch(/Only PDF/);
  });
  it("rejects empty and oversized files", () => {
    expect(validatePdf({ name: "a.pdf", type: "application/pdf", size: 0 })).toMatch(/empty/);
    expect(validatePdf({ name: "a.pdf", type: "application/pdf", size: 11 * 1024 * 1024 })).toMatch(/too large/);
  });
});
