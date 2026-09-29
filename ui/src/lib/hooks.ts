import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const seq = useRef(0);

  const load = useCallback(
    async (quiet = false) => {
      if (!path) return;
      const n = ++seq.current;
      if (!quiet) setLoading(true);
      try {
        const d = await api.get<T>(path);
        if (n === seq.current) {
          setData(d);
          setError(null);
        }
      } catch (e) {
        if (n === seq.current) setError(e as ApiError);
      } finally {
        if (n === seq.current) setLoading(false);
      }
    },
    [path],
  );

  useEffect(() => {
    setData(null);
    load();
  }, [load]);

  return { data, error, loading, reload: () => load(true), setData };
}

/** Server-sent events with automatic reconnect (A12.5). */
export function useEventStream(url: string | null, onEvent: (ev: any) => void) {
  const handler = useRef(onEvent);
  handler.current = onEvent;
  useEffect(() => {
    if (!url) return;
    let es: EventSource | null = null;
    let closed = false;
    let retry: number | undefined;
    const open = () => {
      es = new EventSource(url);
      es.onmessage = (m) => {
        const ev = JSON.parse(m.data);
        handler.current(ev);
        if (ev.type === "assessment_completed") {
          closed = true;
          es?.close();
        }
      };
      es.onerror = () => {
        es?.close();
        if (!closed) retry = window.setTimeout(open, 1500);
      };
    };
    open();
    return () => {
      closed = true;
      es?.close();
      window.clearTimeout(retry);
    };
  }, [url]);
}

export function useKey(handler: (e: KeyboardEvent) => void, active = true) {
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    if (!active) return;
    const fn = (e: KeyboardEvent) => ref.current(e);
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [active]);
}
