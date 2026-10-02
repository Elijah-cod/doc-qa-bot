"use client";

import { useState } from "react";
import { Icon } from "./Icon";

const SUGGESTIONS = [
  ["Summary", "Summarize the main points of this document."],
  ["Key dates", "What dates or deadlines are mentioned?"],
  ["Numbers", "What are the most important numbers or figures?"],
];
const MAX = 1000; // backend rejects longer questions

type Props = { filename: string; busy: boolean; showSuggestions: boolean; onSend: (text: string) => void };

export function Composer({ filename, busy, showSuggestions, onSend }: Props) {
  const [text, setText] = useState("");
  const canSend = text.trim().length > 0 && text.length <= MAX && !busy;

  const send = (value = text) => {
    if (!value.trim() || value.length > MAX || busy) return;
    onSend(value.trim());
    setText("");
  };

  return (
    <div className="pt-space-md">
      {showSuggestions && (
        <div className="mb-space-sm flex flex-wrap items-center gap-space-xs">
          <span className="mr-1 text-label-sm font-normal text-on-surface-variant">Suggested:</span>
          {SUGGESTIONS.map(([label, prompt]) => (
            <button
              key={label}
              type="button"
              disabled={busy}
              onClick={() => send(prompt)}
              className="rounded-full bg-surface-container-low px-space-sm py-1 text-label-sm text-on-surface shadow-sm transition-colors hover:bg-surface-container disabled:opacity-50"
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <div className="relative flex flex-col gap-space-sm rounded-2xl bg-surface-container-lowest p-space-sm shadow-md">
        <textarea
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            // Enter sends; Shift+Enter adds a new line.
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              send();
            }
          }}
          placeholder={`Ask anything about ${filename}…`}
          aria-label="Your question"
          className="w-full resize-none bg-transparent px-space-sm pt-space-xs placeholder:text-outline focus:outline-none"
        />
        <div className="flex items-center justify-between pt-space-xs">
          <span className={`px-space-sm text-label-sm font-normal ${text.length > MAX ? "text-error" : "text-outline"}`}>
            {text.length > MAX * 0.9 ? `${text.length} / ${MAX}` : ""}
          </span>
          <div className="flex items-center gap-space-sm">
            <span className="hidden text-label-sm font-normal text-outline sm:inline">Enter to send · Shift+Enter for new line</span>
            <button
              type="button"
              disabled={!canSend}
              onClick={() => send()}
              className="flex items-center gap-1.5 rounded-xl bg-primary px-space-md py-2 text-label-md text-on-primary shadow-sm transition-all hover:bg-primary-container active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span>{busy ? "Thinking…" : "Ask DocFlow"}</span>
              <Icon name="arrow_upward" size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
