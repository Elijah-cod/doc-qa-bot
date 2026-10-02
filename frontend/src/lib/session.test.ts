import { describe, expect, it } from "vitest";
import { citedCount, initialState, reducer, selectedResponse, type State } from "./session";
import type { AskResponse } from "./types";

const doc = { doc_id: "d1", filename: "h.pdf", pages: 6, chunks: 6 };
const response: AskResponse = {
  answer: "24 days [1].",
  grounded: true,
  sources: [
    { n: 1, page: 2, chunk_index: 1, score: 0.7, content: "24 days", cited: true },
    { n: 2, page: 1, chunk_index: 0, score: 0.5, content: "other", cited: false },
  ],
};

function ask(state: State, id = "1"): State {
  return reducer(state, { type: "question_asked", userId: `u${id}`, assistantId: `a${id}`, text: "Q?", at: 0 });
}

describe("session reducer", () => {
  it("upload success starts a fresh conversation", () => {
    let s = reducer(initialState, { type: "upload_succeeded", doc });
    s = ask(s);
    s = reducer(s, { type: "upload_succeeded", doc: { ...doc, doc_id: "d2" } });
    expect(s.doc?.doc_id).toBe("d2");
    expect(s.messages).toEqual([]);
  });

  it("upload failure keeps the error and stops loading", () => {
    let s = reducer(initialState, { type: "upload_started" });
    expect(s.uploading).toBe(true);
    s = reducer(s, { type: "upload_failed", error: "too big" });
    expect(s.uploading).toBe(false);
    expect(s.uploadError).toBe("too big");
  });

  it("asking adds a user bubble and a loading assistant bubble", () => {
    const s = ask(reducer(initialState, { type: "upload_succeeded", doc }));
    expect(s.messages.map((m) => m.role)).toEqual(["user", "assistant"]);
    expect(s.messages[1]).toMatchObject({ status: "loading", question: "Q?" });
  });

  it("an answer fills the bubble and selects it for the source panel", () => {
    let s = ask(reducer(initialState, { type: "upload_succeeded", doc }));
    s = reducer(s, { type: "answer_received", assistantId: "a1", response });
    expect(s.messages[1]).toMatchObject({ status: "done", response });
    expect(selectedResponse(s)).toBe(response);
    expect(citedCount(selectedResponse(s))).toBe(1);
  });

  it("failure then retry goes back to loading and clears the error", () => {
    let s = ask(reducer(initialState, { type: "upload_succeeded", doc }));
    s = reducer(s, { type: "answer_failed", assistantId: "a1", error: "busy" });
    expect(s.messages[1]).toMatchObject({ status: "error", error: "busy" });
    s = reducer(s, { type: "retry", assistantId: "a1" });
    expect(s.messages[1]).toMatchObject({ status: "loading", error: undefined });
  });

  it("clicking a citation selects that message and bumps the nonce", () => {
    let s = ask(reducer(initialState, { type: "upload_succeeded", doc }));
    s = reducer(s, { type: "cite_clicked", messageId: "a1", n: 1 });
    s = reducer(s, { type: "cite_clicked", messageId: "a1", n: 1 });
    expect(s.selectedMessageId).toBe("a1");
    expect(s.activeCitation).toEqual({ messageId: "a1", n: 1, nonce: 2 });
  });

  it("reset clears everything", () => {
    const s = reducer(ask(reducer(initialState, { type: "upload_succeeded", doc })), { type: "reset" });
    expect(s).toEqual(initialState);
  });
});
