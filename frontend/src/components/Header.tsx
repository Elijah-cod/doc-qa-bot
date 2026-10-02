"use client";

import { useRef } from "react";
import type { UploadResponse } from "@/lib/types";
import { Icon } from "./Icon";

type Props = {
  doc: UploadResponse | null;
  uploading: boolean;
  onReplace: (file: File) => void;
  onNewChat: () => void;
};

export function Header({ doc, uploading, onReplace, onNewChat }: Props) {
  const fileInput = useRef<HTMLInputElement>(null);

  return (
    <header className="sticky top-0 z-50 w-full bg-surface-container-lowest/90 shadow-[0_1px_8px_rgba(0,0,0,0.04)] backdrop-blur-xl">
      <div className="flex h-16 w-full items-center justify-between gap-space-md px-margin">
        <div className="flex shrink-0 items-center gap-space-md">
          <div className="flex items-center gap-space-sm">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-on-primary shadow-sm">
              <Icon name="auto_read_play" size={19} />
            </div>
            <span className="text-headline-sm tracking-tight">DocFlow</span>
          </div>
          <span className="hidden items-center rounded-full bg-surface-container px-space-sm py-0.5 text-label-sm tracking-wide text-primary sm:inline-flex">
            Cited answers
          </span>
        </div>

        {doc && (
          <div className="mx-space-sm flex max-w-xl flex-1 items-center justify-center">
            <div className="flex max-w-full items-center gap-space-sm rounded-full bg-surface-container-low px-space-md py-1.5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
              <Icon name="description" className="shrink-0 text-primary" />
              <span className="max-w-[220px] truncate text-label-md md:max-w-xs" title={doc.filename}>
                {doc.filename} <span className="font-normal text-on-surface-variant">({doc.pages} pages)</span>
              </span>
              <button
                type="button"
                disabled={uploading}
                onClick={() => fileInput.current?.click()}
                className="inline-flex shrink-0 items-center gap-1 rounded-md px-space-sm py-1 text-label-sm text-primary transition-all duration-150 hover:bg-primary hover:text-on-primary disabled:opacity-50"
              >
                <Icon name={uploading ? "progress_activity" : "swap_horiz"} size={14} className={uploading ? "animate-spin" : ""} />
                <span>{uploading ? "Uploading…" : "Replace"}</span>
              </button>
              <input
                ref={fileInput}
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) onReplace(f);
                  e.target.value = ""; // allow picking the same file again
                }}
              />
            </div>
          </div>
        )}

        <div className="flex shrink-0 items-center gap-space-md">
          {doc && (
            <>
              <div className="hidden items-center gap-1.5 text-label-sm text-on-surface-variant xl:flex">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-secondary-container" />
                <span>Session only · deleted when you leave</span>
              </div>
              <button
                type="button"
                onClick={onNewChat}
                title="Delete this document and start over"
                className="flex items-center gap-1.5 rounded-lg px-space-sm py-1.5 text-label-md text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface"
              >
                <Icon name="restart_alt" />
                <span className="hidden lg:inline">New Chat</span>
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
