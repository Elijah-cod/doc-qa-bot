"use client";

import { useEffect, useRef, useState } from "react";
import { MAX_UPLOAD_MB } from "@/lib/api";
import { useServerStatus } from "@/lib/useServerStatus";
import { Icon } from "./Icon";

const STEPS = ["Reading pages…", "Splitting into passages…", "Creating embeddings…", "Saving to the index…"];

type Props = { uploading: boolean; error: string | null; onFile: (file: File) => void };

export function UploadScreen({ uploading, error, onFile }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [step, setStep] = useState(0);
  const server = useServerStatus();

  // The backend doesn't report progress, so cycle through the pipeline stages while we wait.
  useEffect(() => {
    if (!uploading) {
      setStep(0);
      return;
    }
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1500);
    return () => clearInterval(t);
  }, [uploading]);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center px-margin py-space-xl">
      <h1 className="text-headline-lg">Ask your PDF anything</h1>
      <p className="mt-space-xs text-body-lg text-on-surface-variant">
        Every answer links to the exact passages and pages it came from, so you can check it.
      </p>

      {server === "waking" && (
        <div role="status" className="mt-space-lg flex items-center gap-space-sm rounded-xl bg-surface-container px-space-md py-space-sm text-body-sm text-on-surface-variant">
          <Icon name="progress_activity" size={16} className="animate-spin text-primary" />
          <span>Waking up the server. The free hosting plan sleeps when idle; this can take up to a minute.</span>
        </div>
      )}
      {server === "down" && (
        <div role="alert" className="mt-space-lg flex items-center gap-space-sm rounded-xl bg-error-container px-space-md py-space-sm text-body-sm text-on-error-container">
          <Icon name="cloud_off" size={16} />
          <span>The server isn&apos;t responding right now. Please try again in a few minutes.</span>
        </div>
      )}

      <div
        role="button"
        tabIndex={0}
        aria-disabled={uploading}
        onClick={() => !uploading && input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !uploading && input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files?.[0];
          if (f && !uploading) onFile(f);
        }}
        className={`mt-space-xl flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-space-lg py-16 text-center transition-colors ${
          dragging ? "border-primary bg-surface-container" : "border-outline-variant bg-surface-container-lowest hover:border-primary"
        } ${uploading ? "cursor-wait" : ""}`}
      >
        {uploading ? (
          <>
            <Icon name="progress_activity" size={36} className="animate-spin text-primary" />
            <p className="mt-space-md text-headline-sm">{STEPS[step]}</p>
            <p className="mt-space-xs text-body-sm text-on-surface-variant">Usually takes a few seconds.</p>
          </>
        ) : (
          <>
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-container text-primary">
              <Icon name="upload_file" size={30} />
            </div>
            <p className="mt-space-md text-headline-sm">Drop a PDF here, or click to choose</p>
            <p className="mt-space-xs text-body-sm text-on-surface-variant">
              Text-based PDFs up to {MAX_UPLOAD_MB} MB · scanned documents aren&apos;t supported
            </p>
          </>
        )}
        <input
          ref={input}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFile(f);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div role="alert" className="mt-space-md flex items-start gap-space-sm rounded-xl bg-error-container px-space-md py-space-sm text-body-md text-on-error-container">
          <Icon name="error" className="mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="mt-space-xl grid gap-space-md sm:grid-cols-3">
        {[
          ["format_quote", "Cited answers", "Each claim is tagged [1], [2]… so you can open the source."],
          ["menu_book", "Page-accurate", "Sources show the page and the passage text."],
          ["search_off", "Says when it doesn't know", "Off-topic questions get a clear “not found”."],
        ].map(([icon, title, body]) => (
          <div key={title} className="rounded-xl bg-surface-container-low p-space-md">
            <Icon name={icon} className="text-primary" />
            <p className="mt-space-xs text-label-md font-semibold">{title}</p>
            <p className="mt-0.5 text-body-sm text-on-surface-variant">{body}</p>
          </div>
        ))}
      </div>
      <p className="mt-space-lg text-label-sm font-normal text-on-surface-variant">
        Your document is stored only for this session and deleted when you start a new chat or close the tab.
      </p>
    </div>
  );
}
