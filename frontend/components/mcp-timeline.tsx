"use client";
import { Activity, Brain, CheckCircle2, GitBranch, Wrench, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TraceEvent } from "@/lib/types";

const ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  intent: Brain,
  plan: GitBranch,
  tool_call: Wrench,
  tool_result: CheckCircle2,
  llm_call: Brain,
  llm_chunk: Activity,
  done: CheckCircle2,
  error: XCircle,
};

export function McpTimeline({ events }: { events: TraceEvent[] }) {
  // Collapse llm_chunk floods.
  const condensed = events.filter((e) => e.kind !== "llm_chunk");
  const tokenCount = events.filter((e) => e.kind === "llm_chunk").length;

  return (
    <div className="rounded-lg border bg-card">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold">MCP activity</h3>
          <p className="text-xs text-muted-foreground">
            Live trace of every tool call and LLM step
          </p>
        </div>
        {tokenCount > 0 && (
          <span className="text-xs text-muted-foreground">
            {tokenCount} stream chunks
          </span>
        )}
      </div>
      <ol className="divide-y">
        {condensed.length === 0 && (
          <li className="px-4 py-6 text-center text-sm text-muted-foreground">
            Run an analysis to see the trace here.
          </li>
        )}
        {condensed.map((ev, i) => {
          const Icon = ICON[ev.kind] ?? Activity;
          const colour =
            ev.kind === "error"
              ? "text-destructive"
              : ev.kind === "done"
                ? "text-risk-low"
                : ev.kind === "tool_result"
                  ? "text-primary"
                  : "text-muted-foreground";
          return (
            <li key={i} className="animate-slide-up px-4 py-3 text-sm">
              <div className="flex items-start gap-3">
                <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", colour)} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate font-medium">{ev.label}</p>
                    {ev.duration_ms != null && (
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {ev.duration_ms}ms
                      </span>
                    )}
                  </div>
                  {ev.server && ev.tool && (
                    <p className="mono text-xs text-muted-foreground">
                      {ev.server}.{ev.tool}
                    </p>
                  )}
                  {ev.args && (
                    <pre className="mono mt-1 overflow-x-auto rounded bg-muted p-2 text-[11px] leading-snug">
                      {JSON.stringify(ev.args, null, 2)}
                    </pre>
                  )}
                  {ev.text && (
                    <p className="mt-1 text-xs text-muted-foreground">{ev.text}</p>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
