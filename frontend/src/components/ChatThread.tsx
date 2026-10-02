"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { answerForClipboard, parseAnswer } from "@/lib/citations";
import type { AssistantMessage, Message } from "@/lib/session";
import type { UploadResponse } from "@/lib/types";
import { Icon } from "./Icon";

const NOT_FOUND = "I couldn't find that in the document."; // same sentence as backend/app/rag.py

type Props = {
  doc: UploadResponse;
  messages: Message[];
  selectedMessageId: string | null;
  onCite: (messageId: string, n: number) => void;
  onSelect: (messageId: string) => void;
  onRetry: (messageId: string) => void;
};

export function ChatThread({ doc, messages, selectedMessageId, onCite, onSelect, onRetry }: Props) {
  const bottom = useRef<HTMLDivElement>(null);
  const last = messages[messages.length - 1];
  const lastKey = last ? `${last.id}:${last.role === "assistant" ? last.status : ""}` : "";

  // Keep the newest message in view.
  // Braces matter: newer browsers make scrollIntoView() return a Promise, and an effect
  // may only return a cleanup function (or nothing).
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [lastKey]);

  return (
    <div className="flex-1 space-y-space-lg overflow-y-auto py-space-sm pr-space-xs">
      {messages.length === 0 && (
        <div className="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm">
          <div className="flex items-center gap-space-sm text-label-md text-tertiary">
            <Icon name="check_circle" size={16} />
            <span>Indexed {doc.chunks} passages from {doc.pages} pages</span>
          </div>
          <p className="mt-space-sm text-body-lg">
            Ask anything about <strong className="font-semibold">{doc.filename}</strong>. Every answer links to the passages it
            came from. Click a <span className="rounded-full bg-surface-container-high px-1.5 text-label-sm text-primary">[1]</span>{" "}
            chip to open its source.
          </p>
        </div>
      )}

      {messages.map((m) =>
        m.role === "user" ? (
          <div key={m.id} className="flex flex-col items-end">
            <Meta who="You" at={m.at} />
            <div className="max-w-xl whitespace-pre-line rounded-2xl rounded-tr-sm bg-surface-container px-space-lg py-space-md shadow-sm">
              {m.text}
            </div>
          </div>
        ) : (
          <AssistantBubble
            key={m.id}
            message={m}
            selected={m.id === selectedMessageId}
            onCite={(n) => onCite(m.id, n)}
            onSelect={() => onSelect(m.id)}
            onRetry={() => onRetry(m.id)}
          />
        ),
      )}
      <div ref={bottom} />
    </div>
  );
}

function Meta({ who, at, bot = false }: { who: string; at: number; bot?: boolean }) {
  const time = new Date(at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  return (
    <div className="mb-1.5 flex items-center gap-space-sm">
      {bot && (
        <div className="flex h-5 w-5 items-center justify-center rounded-md bg-primary-container text-on-primary">
          <Icon name="auto_read_play" size={14} />
        </div>
      )}
      <span className={`text-label-sm ${bot ? "text-on-surface" : "font-normal text-on-surface-variant"}`}>{who}</span>
      <span className="text-label-sm font-normal text-outline">{time}</span>
    </div>
  );
}

function AssistantBubble({
  message,
  selected,
  onCite,
  onSelect,
  onRetry,
}: {
  message: AssistantMessage;
  selected: boolean;
  onCite: (n: number) => void;
  onSelect: () => void;
  onRetry: () => void;
}) {
  const [copied, setCopied] = useState(false);

  if (message.status === "loading") {
    return (
      <div className="flex flex-col items-start">
        <Meta who="DocFlow Assistant" at={message.at} bot />
        <div className="flex items-center gap-space-sm rounded-2xl bg-surface-container-lowest px-space-lg py-space-md text-on-surface-variant shadow-sm">
          <Icon name="progress_activity" size={16} className="animate-spin text-primary" />
          <span className="font-mono text-label-md">Searching the document…</span>
        </div>
      </div>
    );
  }

  if (message.status === "error") {
    return (
      <div className="flex flex-col items-start">
        <Meta who="DocFlow Assistant" at={message.at} bot />
        <div role="alert" className="w-full rounded-2xl bg-error-container p-space-lg text-on-error-container shadow-sm">
          <div className="flex items-start gap-space-sm">
            <Icon name="error" className="mt-0.5" />
            <p className="flex-1">{message.error}</p>
          </div>
          <button
            type="button"
            onClick={onRetry}
            className="mt-space-sm inline-flex items-center gap-1 rounded-md bg-surface-container-lowest px-space-sm py-1 text-label-sm text-error hover:opacity-90"
          >
            <Icon name="refresh" size={14} /> Try again
          </button>
        </div>
      </div>
    );
  }

  const r = message.response!;
  const byN = new Map(r.sources.map((s) => [s.n, s]));
  const valid = new Set(byN.keys());
  const notFound = !r.grounded || r.answer.trim() === NOT_FOUND;
  const cited = r.sources.filter((s) => s.cited).length;

  return (
    <div className="flex flex-col items-start">
      <Meta who="DocFlow Assistant" at={message.at} bot />
      <div
        onClick={onSelect}
        className={`w-full cursor-default rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm transition-shadow ${
          selected ? "ring-2 ring-primary-fixed" : ""
        }`}
      >
        {notFound && (
          <div className="mb-space-sm flex items-center gap-space-xs text-label-sm text-on-surface-variant">
            <Icon name="search_off" size={16} className="text-outline" />
            <span>
              Not found in this document
              {!r.grounded && r.sources[0] && ` · closest passage scored ${r.sources[0].score.toFixed(2)}`}
            </span>
          </div>
        )}

        <p className="whitespace-pre-line text-body-lg leading-relaxed">
          {parseAnswer(r.answer, valid).map((seg, i) =>
            seg.type === "text" ? (
              <Fragment key={i}>{renderBold(seg.text)}</Fragment>
            ) : (
              <button
                key={i}
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onCite(seg.n);
                }}
                title={`Open source [${seg.n}]`}
                className="mx-0.5 inline-flex cursor-pointer items-center gap-1 rounded-full bg-surface-container-high px-2 py-0.5 align-baseline text-label-sm text-primary shadow-sm transition-colors hover:bg-primary hover:text-on-primary"
              >
                <span>[{seg.n}]</span>
                <span className="font-mono text-[10px]">
                  p.{byN.get(seg.n)!.page} · {byN.get(seg.n)!.score.toFixed(2)}
                </span>
              </button>
            ),
          )}
        </p>

        <div className="mt-space-md flex flex-wrap items-center gap-space-md pt-space-xs text-label-sm text-on-surface-variant">
          {cited > 0 && (
            <span className="flex items-center gap-1">
              <Icon name="check_circle" size={14} className="text-tertiary" />
              Grounded in {cited} source{cited > 1 ? "s" : ""}
            </span>
          )}
          {!notFound && cited === 0 && (
            <span className="flex items-center gap-1">
              <Icon name="info" size={14} /> No citations in this answer; check the sources
            </span>
          )}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              navigator.clipboard?.writeText(answerForClipboard(r.answer, valid));
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
            className="flex items-center gap-1 transition-colors hover:text-primary"
          >
            <Icon name={copied ? "done" : "content_copy"} size={14} /> {copied ? "Copied" : "Copy"}
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onSelect();
            }}
            className="flex items-center gap-1 transition-colors hover:text-primary lg:hidden"
          >
            <Icon name="menu_book" size={14} /> {r.sources.length} sources
          </button>
        </div>
      </div>
    </div>
  );
}

/** Gemini sometimes uses **bold**; render it instead of showing asterisks. */
function renderBold(text: string) {
  return text.split(/\*\*(.+?)\*\*/g).map((part, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="font-semibold text-primary">
        {part}
      </strong>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  );
}
