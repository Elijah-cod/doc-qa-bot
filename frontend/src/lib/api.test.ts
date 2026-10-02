import { describe, expect, it, vi } from "vitest";
import { ApiError, askQuestion, uploadPdf } from "./api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("api client", () => {
  it("posts the question as JSON and returns the answer", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(200, { answer: "A", grounded: true, sources: [] }));
    const r = await askQuestion("d1", "Q?", fetchMock);
    expect(r.answer).toBe("A");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/ask");
    expect(JSON.parse(init.body)).toEqual({ doc_id: "d1", question: "Q?" });
  });

  it("uploads as multipart form data", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(200, { doc_id: "d", filename: "f.pdf", pages: 1, chunks: 1 }));
    await uploadPdf(new File(["%PDF-"], "f.pdf", { type: "application/pdf" }), fetchMock);
    const init = fetchMock.mock.calls[0][1];
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
  });

  it("uses the backend's detail message", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(422, { detail: "No extractable text." }));
    await expect(askQuestion("d", "q", fetchMock)).rejects.toMatchObject({ status: 422, message: "No extractable text." });
  });

  it("reads FastAPI validation errors", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(422, { detail: [{ msg: "String should have at least 1 character" }] }));
    await expect(askQuestion("d", "", fetchMock)).rejects.toThrow("at least 1 character");
  });

  it("falls back to a friendly message when there is no detail", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("oops", { status: 502 }));
    await expect(askQuestion("d", "q", fetchMock)).rejects.toThrow("AI service is busy");
  });

  it("explains when the backend is unreachable", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const err = await askQuestion("d", "q", fetchMock).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(err.message).toContain("Is the backend running?");
  });
});
