import type { AskResponse, UploadResponse } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
export const MAX_UPLOAD_MB = 10; // keep in sync with MAX_UPLOAD_MB on the backend

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/** Turn any failed response into a sentence a user can act on. */
export async function toApiError(res: Response): Promise<ApiError> {
  let detail = "";
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
    else if (Array.isArray(body?.detail)) detail = body.detail[0]?.msg ?? ""; // FastAPI 422 shape
  } catch {
    /* not JSON */
  }
  const fallback: Record<number, string> = {
    404: "That document no longer exists. Please upload it again.",
    413: `File is too large (max ${MAX_UPLOAD_MB} MB).`,
    415: "Only PDF files are supported.",
    502: "The AI service is busy. Please try again in a moment.",
    503: "The database is unavailable. Please try again in a moment.",
  };
  return new ApiError(res.status, detail || fallback[res.status] || `Request failed (${res.status}).`);
}

async function request<T>(path: string, init: RequestInit, fetchImpl: typeof fetch): Promise<T> {
  let res: Response;
  try {
    res = await fetchImpl(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(0, `Can't reach the server at ${API_URL}. Is the backend running?`);
  }
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as T;
}

export function uploadPdf(file: File, fetchImpl: typeof fetch = fetch): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/upload", { method: "POST", body: form }, fetchImpl);
}

export function askQuestion(docId: string, question: string, fetchImpl: typeof fetch = fetch): Promise<AskResponse> {
  return request<AskResponse>(
    "/ask",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: docId, question }),
    },
    fetchImpl,
  );
}

/** Delete the document's chunks. Uses sendBeacon so it still fires while the tab closes. */
export function releaseDocument(docId: string): void {
  const url = `${API_URL}/documents/${encodeURIComponent(docId)}/delete`;
  if (typeof navigator !== "undefined" && navigator.sendBeacon?.(url)) return;
  fetch(url, { method: "POST", keepalive: true }).catch(() => {});
}
