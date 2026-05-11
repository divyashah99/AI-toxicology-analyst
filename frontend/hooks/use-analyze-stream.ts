"use client";
import { useCallback, useState } from "react";
import { analyzeStream } from "@/lib/api";
import type { ToxicityReport, TraceEvent } from "@/lib/types";

interface State {
  events: TraceEvent[];
  report: ToxicityReport | null;
  running: boolean;
  error: string | null;
}

const initial: State = { events: [], report: null, running: false, error: null };

export function useAnalyzeStream() {
  const [state, setState] = useState<State>(initial);

  const run = useCallback(
    async (body: {
      query: { name?: string; smiles?: string; cid?: number };
      paper_ids?: string[];
    }) => {
      setState({ ...initial, running: true });
      try {
        for await (const { event, data } of analyzeStream(body)) {
          if (event === "end") break;
          if (event === "error") {
            setState((s) => ({ ...s, error: data?.text ?? "error", running: false }));
            break;
          }
          if (event === "done" && data?.output) {
            setState((s) => ({
              ...s,
              report: data.output as ToxicityReport,
            }));
            continue;
          }
          setState((s) => ({ ...s, events: [...s.events, data as TraceEvent] }));
        }
      } catch (e: any) {
        setState((s) => ({ ...s, error: String(e?.message ?? e) }));
      } finally {
        setState((s) => ({ ...s, running: false }));
      }
    },
    [],
  );

  return { ...state, run };
}
