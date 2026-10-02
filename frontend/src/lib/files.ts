import { MAX_UPLOAD_MB } from "./api";

/** Client-side checks so obvious mistakes fail instantly, without a round trip. */
export function validatePdf(file: { name: string; type: string; size: number }): string | null {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return "Only PDF files are supported.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `File is too large (max ${MAX_UPLOAD_MB} MB).`;
  return null;
}
