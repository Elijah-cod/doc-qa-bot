"use client";

import { useEffect, useState } from "react";
import { pingServer } from "./api";

export type ServerStatus = "checking" | "waking" | "ready" | "down";

/**
 * Checks the backend once on page load. If it doesn't answer quickly we assume it's
 * a sleeping free-tier server and keep trying for ~90s, showing "waking up" meanwhile.
 */
export function useServerStatus(): ServerStatus {
  const [status, setStatus] = useState<ServerStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (await pingServer(3000)) {
        if (!cancelled) setStatus("ready");
        return;
      }
      if (!cancelled) setStatus("waking");
      const deadline = Date.now() + 90_000;
      while (!cancelled && Date.now() < deadline) {
        if (await pingServer(15_000)) {
          if (!cancelled) setStatus("ready");
          return;
        }
        await new Promise((r) => setTimeout(r, 3000));
      }
      if (!cancelled) setStatus("down");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return status;
}
