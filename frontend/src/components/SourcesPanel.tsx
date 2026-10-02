"use client";

import { useEffect, useRef, useState } from "react";
import type { ActiveCitation } from "@/lib/session";
import type { AskResponse, Source, UploadResponse } from "@/lib/types";
import { Icon } from "./Icon";

const MAX_TILES = 96; // page map stays readable for long documents

type Props = {
  doc: UploadResponse;
  response: AskResponse | undefined;
  activeCitation: ActiveCitation;
  open: boolean; // mobile only; always visible on large screens
};

export function SourcesPanel({ doc, response, activeCitation, open }: Props) {
  const cards = useRef(new Map<number, HTMLDivElement>());
  const sources = response ? [...response.sources].sort((a, b) => a.n - b.n) : [];

  const flash = (n: number) => {
    const el = cards.current.get(n);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    el.classList.remove("flash");
    void el.offsetWidth; // restart the CSS animation
    el.classList.add("flash");
  };

  // A [n] chip in the chat was clicked: bring its card into view.
  useEffect(() => {
    if (activeCitation) requestAnimationFrame(() => flash(activeCitation.n));
  }, [activeCitation?.nonce]); // eslint-disable-line react-hooks/exhaustive-deps

  const citedPages = new Set(sources.filter((s) => s.cited).map((s) => s.page));
  const retrievedPages = new Set(sources.map((s) => s.page));
  const best = sources.length ? Math.max(...sources.map((s) => s.score)) : null;

  return (
    <aside
      id="reference-panel"
      className={`${open ? "flex" : "hidden"} w-full shrink-0 flex-col overflow-hidden rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm lg:flex lg:w-[420px] xl:w-[460px]`}
    >
      <div className="flex items-center gap-space-sm pb-space-md">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-container text-primary">
          <Icon name="verified" />
        </div>
        <div>
          <h3 className="text-headline-sm">Verified Sources</h3>
          <p className="text-label-sm font-normal text-on-surface-variant">
            {!response
              ? "Ask a question to see the passages behind the answer"
              : response.grounded
                ? "Passages retrieved for the selected answer"
                : "Closest passages · below the relevance cutoff"}
          </p>
        </div>
      </div>

      <div className="mb-space-md flex items-center justify-between rounded-xl bg-surface-container-low p-space-sm">
        <div className="flex min-w-0 items-center gap-space-sm">
          <Icon name="picture_as_pdf" size={20} className="shrink-0 text-primary" />
          <div className="min-w-0">
            <div className="truncate text-label-md font-semibold">{doc.filename}</div>
            <div className="text-label-sm font-normal text-on-surface-variant">
              {doc.pages} pages · {doc.chunks} passages indexed
            </div>
          </div>
        </div>
        {best !== null && (
          <span
            title="Cosine similarity of the best passage (1.0 = identical meaning)"
            className="shrink-0 rounded-full bg-surface-container-highest px-2 py-0.5 font-mono text-label-sm"
          >
            best {best.toFixed(2)}
          </span>
        )}
      </div>

      <div className="flex-1 space-y-space-md overflow-y-auto pr-1">
        {sources.map((s) => (
          <SourceCard
            key={`${s.n}-${s.chunk_index}`}
            source={s}
            ref={(el) => {
              if (el) cards.current.set(s.n, el);
              else cards.current.delete(s.n);
            }}
          />
        ))}

        <div className="rounded-xl bg-surface-container-low p-space-md">
          <div className="mb-space-xs flex items-center justify-between">
            <span className="text-label-md font-semibold">Page Map</span>
            <span className="font-mono text-label-sm font-normal text-on-surface-variant">{doc.pages} pages</span>
          </div>
          <div className="grid grid-cols-8 gap-1.5 pt-space-xs">
            {Array.from({ length: Math.min(doc.pages, MAX_TILES) }, (_, i) => i + 1).map((p) => {
              const first = sources.find((s) => s.page === p);
              const style = citedPages.has(p)
                ? "bg-primary text-on-primary font-bold shadow-sm"
                : retrievedPages.has(p)
                  ? "bg-secondary-container text-on-secondary-container font-semibold"
                  : "bg-surface text-on-surface-variant";
              return (
                <button
                  key={p}
                  type="button"
                  disabled={!first}
                  onClick={() => first && flash(first.n)}
                  title={first ? `Show passage from page ${p}` : `Page ${p}`}
                  className={`flex h-8 items-center justify-center rounded font-mono text-[11px] transition-colors disabled:cursor-default ${style}`}
                >
                  {p}
                </button>
              );
            })}
          </div>
          {doc.pages > MAX_TILES && (
            <p className="mt-1 text-label-sm font-normal text-on-surface-variant">Showing first {MAX_TILES} pages.</p>
          )}
          <p className="mt-2 text-label-sm font-normal text-on-surface-variant">
            <span className="text-primary">■</span> cited · <span className="text-secondary-container">■</span> retrieved, not
            cited
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1 pt-space-md text-label-sm font-normal text-on-surface-variant">
        <Icon name="lock" size={15} className="text-primary" /> Deleted from the server when this session ends
      </div>
    </aside>
  );
}

function SourceCard({ source: s, ref }: { source: Source; ref: (el: HTMLDivElement | null) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const long = s.content.length > 420;

  return (
    <div
      ref={ref}
      className={`rounded-xl p-space-md shadow-sm transition-all duration-200 ${s.cited ? "bg-surface" : "bg-surface opacity-70"}`}
    >
      <div className="mb-space-xs flex items-center justify-between gap-space-sm">
        <span
          className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-label-sm ${
            s.cited ? "bg-primary-fixed text-primary" : "bg-surface-container text-on-surface-variant"
          }`}
        >
          <span>{s.cited ? `Citation [${s.n}]` : `[${s.n}] not cited`}</span>
          <span>·</span>
          <span className="font-mono">Page {s.page}</span>
        </span>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard?.writeText(s.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
          className="flex items-center gap-0.5 text-label-sm text-on-surface-variant hover:text-on-surface"
        >
          <Icon name={copied ? "done" : "copy_all"} size={13} />
          <span>{copied ? "Copied" : "Excerpt"}</span>
        </button>
      </div>

      <div className="mb-space-xs flex items-center gap-space-sm" title="Cosine similarity to your question">
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-surface-container">
          <div className={`h-full rounded-full ${s.cited ? "bg-primary" : "bg-outline"}`} style={{ width: `${Math.max(0, Math.min(1, s.score)) * 100}%` }} />
        </div>
        <span className="font-mono text-[10px] text-on-surface-variant">{s.score.toFixed(2)}</span>
      </div>

      <p
        className={`whitespace-pre-line rounded-lg bg-surface-container-lowest px-space-sm py-1 text-body-sm leading-relaxed ${
          !expanded && long ? "line-clamp-6" : ""
        }`}
      >
        {s.content}
      </p>
      {long && (
        <button type="button" onClick={() => setExpanded((v) => !v)} className="mt-1 text-label-sm text-primary hover:underline">
          {expanded ? "Show less" : "Show full passage"}
        </button>
      )}
    </div>
  );
}
