"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ChatThread } from "@/components/ChatThread";
import { Composer } from "@/components/Composer";
import { Header } from "@/components/Header";
import { Icon } from "@/components/Icon";
import { SourcesPanel } from "@/components/SourcesPanel";
import { UploadScreen } from "@/components/UploadScreen";
import { ApiError, askQuestion, releaseDocument, uploadPdf } from "@/lib/api";
import { validatePdf } from "@/lib/files";
import { citedCount, initialState, reducer, selectedResponse } from "@/lib/session";

export default function Home() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [panelOpen, setPanelOpen] = useState(false); // mobile only
  const docId = useRef<string | null>(null);
  docId.current = state.doc?.doc_id ?? null;

  // Session-only storage: delete the document's chunks when the tab closes.
  useEffect(() => {
    const onHide = () => docId.current && releaseDocument(docId.current);
    window.addEventListener("pagehide", onHide);
    return () => window.removeEventListener("pagehide", onHide);
  }, []);

  const handleFile = useCallback(async (file: File) => {
    const problem = validatePdf(file);
    if (problem) return dispatch({ type: "upload_failed", error: problem });
    const previous = docId.current;
    dispatch({ type: "upload_started" });
    try {
      const doc = await uploadPdf(file);
      dispatch({ type: "upload_succeeded", doc });
      if (previous) releaseDocument(previous); // replaced: drop the old one
    } catch (e) {
      dispatch({ type: "upload_failed", error: e instanceof Error ? e.message : "Upload failed." });
    }
  }, []);

  const runAsk = useCallback(async (assistantId: string, question: string) => {
    if (!docId.current) return;
    try {
      const response = await askQuestion(docId.current, question);
      dispatch({ type: "answer_received", assistantId, response });
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 404
        ? "This document has expired on the server. Click Replace to upload it again."
        : e instanceof Error ? e.message : "Something went wrong.";
      dispatch({ type: "answer_failed", assistantId, error: msg });
    }
  }, []);

  const handleAsk = (text: string) => {
    const assistantId = crypto.randomUUID();
    dispatch({ type: "question_asked", userId: crypto.randomUUID(), assistantId, text, at: Date.now() });
    runAsk(assistantId, text);
  };

  const handleRetry = (assistantId: string) => {
    const m = state.messages.find((x) => x.id === assistantId);
    if (m?.role !== "assistant") return;
    dispatch({ type: "retry", assistantId });
    runAsk(assistantId, m.question);
  };

  const handleNewChat = () => {
    if (docId.current) releaseDocument(docId.current);
    setPanelOpen(false);
    dispatch({ type: "reset" });
  };

  const busy = state.messages.some((m) => m.role === "assistant" && m.status === "loading");
  const response = selectedResponse(state);
  const cited = citedCount(response);

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      <Header doc={state.doc} uploading={state.uploading} onReplace={handleFile} onNewChat={handleNewChat} />

      {!state.doc ? (
        <main className="flex flex-1 flex-col">
          <UploadScreen uploading={state.uploading} error={state.uploadError} onFile={handleFile} />
        </main>
      ) : (
        <main className="flex min-h-0 flex-1 flex-col">
          <div className="w-full bg-surface-container-low px-margin py-space-xs">
            <div className="mx-auto flex max-w-7xl items-center justify-between gap-space-md">
              <div className="flex items-center gap-space-sm text-label-md text-on-surface-variant">
                <span className="h-2 w-2 shrink-0 rounded-full bg-secondary-container" />
                <span>
                  Session active: this PDF is stored only while the chat is open, and deleted when you start a new chat, replace
                  the file or close the tab.
                </span>
              </div>
              <div className="hidden shrink-0 items-center gap-space-md text-label-sm text-on-surface-variant sm:flex">
                <span className="flex items-center gap-1 font-mono">
                  <Icon name="memory" size={14} className="text-tertiary" /> RAG · pgvector
                </span>
                <span className="flex items-center gap-1 font-mono">
                  <Icon name="verified_user" size={14} className="text-primary" /> Auto-delete on exit
                </span>
              </div>
            </div>
          </div>

          {state.uploadError && (
            <div role="alert" className="mx-auto mt-space-sm flex w-full max-w-7xl items-center gap-space-sm px-margin">
              <div className="flex flex-1 items-center gap-space-sm rounded-xl bg-error-container px-space-md py-space-sm text-on-error-container">
                <Icon name="error" />
                <span className="flex-1">Couldn&apos;t replace the file: {state.uploadError}</span>
              </div>
            </div>
          )}

          <div className="relative mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col gap-gutter px-margin py-space-md lg:flex-row">
            <div className="mx-auto flex min-h-[60dvh] w-full min-w-0 max-w-3xl flex-1 flex-col lg:mx-0 lg:min-h-0">
              <div className="flex items-center justify-between pb-space-sm">
                <div className="flex items-center gap-space-sm">
                  <Icon name="mark_chat_read" size={20} className="text-primary" />
                  <h2 className="text-headline-sm">Conversation</h2>
                  {cited > 0 && (
                    <span className="rounded-full bg-surface-container px-space-sm py-0.5 text-label-sm text-on-surface-variant">
                      {cited} citation{cited > 1 ? "s" : ""} in selected answer
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setPanelOpen((v) => !v)}
                  className="flex items-center gap-1 rounded-md bg-surface-container px-space-sm py-1 text-label-sm text-primary lg:hidden"
                >
                  <Icon name="menu_book" size={16} />
                  <span>{panelOpen ? "Hide sources" : "Sources"}</span>
                </button>
              </div>

              <ChatThread
                doc={state.doc}
                messages={state.messages}
                selectedMessageId={state.selectedMessageId}
                onSelect={(id) => {
                  dispatch({ type: "select_message", messageId: id });
                  setPanelOpen(true);
                }}
                onCite={(id, n) => {
                  dispatch({ type: "cite_clicked", messageId: id, n });
                  setPanelOpen(true);
                }}
                onRetry={handleRetry}
              />
              <Composer
                filename={state.doc.filename}
                busy={busy}
                showSuggestions={state.messages.length === 0}
                onSend={handleAsk}
              />
            </div>

            <SourcesPanel doc={state.doc} response={response} activeCitation={state.activeCitation} open={panelOpen} />
          </div>
        </main>
      )}

      <footer className="w-full shrink-0 bg-surface-container-low py-space-sm">
        <div className="flex w-full flex-col items-center justify-between gap-space-xs px-margin text-label-sm font-normal text-on-surface-variant sm:flex-row">
          <span>DocFlow · Answers grounded in your document, with sources</span>
          <span>Gemini · Supabase pgvector · FastAPI</span>
        </div>
      </footer>
    </div>
  );
}
