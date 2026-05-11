"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FileText } from "lucide-react";
import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { McpTimeline } from "@/components/mcp-timeline";
import { CompoundCard } from "@/components/compound-card";
import { ReportViewer } from "@/components/report-viewer";
import { useAnalyzeStream } from "@/hooks/use-analyze-stream";
import { api } from "@/lib/api";
import type { PaperMeta } from "@/lib/types";

const EXAMPLES: { label: string; smiles?: string; name?: string }[] = [
  { label: "Caffeine", name: "caffeine" },
  { label: "Aspirin", name: "aspirin" },
  { label: "Bisphenol A", smiles: "CC(C)(c1ccc(O)cc1)c1ccc(O)cc1" },
  { label: "Aflatoxin B1", name: "aflatoxin B1" },
];

export default function AnalyzePage() {
  return (
    <Suspense fallback={<div className="p-6"><Skeleton className="h-32" /></div>}>
      <AnalyzePageInner />
    </Suspense>
  );
}

function AnalyzePageInner() {
  const params = useSearchParams();
  const [name, setName] = useState("");
  const [smiles, setSmiles] = useState("");
  const [papers, setPapers] = useState<PaperMeta[]>([]);
  const [papersLoading, setPapersLoading] = useState(true);
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set());
  const { events, report, running, error, run } = useAnalyzeStream();

  // Load uploaded papers once on mount.
  useEffect(() => {
    api
      .listPapers()
      .then((r) => setPapers(r.papers ?? []))
      .catch(() => setPapers([]))
      .finally(() => setPapersLoading(false));
  }, []);

  // Auto-fill + auto-run from ?name= / ?smiles= (used by "Re-analyze" from /reports).
  useEffect(() => {
    const n = params?.get("name") ?? "";
    const s = params?.get("smiles") ?? "";
    if (n || s) {
      setName(n);
      setSmiles(s);
      run({ query: { name: n || undefined, smiles: s || undefined } });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const paperIdsArray = useMemo(
    () => Array.from(selectedPaperIds),
    [selectedPaperIds],
  );

  const togglePaper = (id: string) => {
    setSelectedPaperIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedPaperIds.size === papers.length) {
      setSelectedPaperIds(new Set());
    } else {
      setSelectedPaperIds(new Set(papers.map((p) => p.paper_id)));
    }
  };

  const submit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!name.trim() && !smiles.trim()) return;
    run({
      query: {
        name: name.trim() || undefined,
        smiles: smiles.trim() || undefined,
      },
      paper_ids: paperIdsArray.length ? paperIdsArray : undefined,
    });
  };

  const fillExample = (ex: (typeof EXAMPLES)[number]) => {
    setName(ex.name ?? "");
    setSmiles(ex.smiles ?? "");
    run({
      query: { name: ex.name, smiles: ex.smiles },
      paper_ids: paperIdsArray.length ? paperIdsArray : undefined,
    });
  };

  return (
    <>
      <Topbar
        title="Compound analysis"
        subtitle="Resolve identity, compute descriptors, and score toxicity."
      />
      <div className="grid flex-1 gap-4 p-4 md:grid-cols-[1fr_360px] md:p-6">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Input</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={submit} className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="text-xs text-muted-foreground">Compound name</label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. caffeine"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">SMILES</label>
                  <Input
                    value={smiles}
                    onChange={(e) => setSmiles(e.target.value)}
                    placeholder="e.g. CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
                    className="mono"
                  />
                </div>
                <div className="md:col-span-2 flex flex-wrap items-center gap-2">
                  <Button type="submit" disabled={running}>
                    {running ? "Analyzing…" : "Analyze"}
                  </Button>
                  <span className="text-xs text-muted-foreground">try:</span>
                  {EXAMPLES.map((ex) => (
                    <Button
                      key={ex.label}
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => fillExample(ex)}
                      disabled={running}
                    >
                      {ex.label}
                    </Button>
                  ))}
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
              <div>
                <CardTitle className="text-base">Ground in literature</CardTitle>
                <p className="mt-1 text-xs text-muted-foreground">
                  Select uploaded papers to retrieve evidence passages and cite them in the report.
                </p>
              </div>
              {papers.length > 0 && (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={toggleAll}
                  disabled={running}
                >
                  {selectedPaperIds.size === papers.length ? "Clear" : "Select all"}
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {papersLoading ? (
                <Skeleton className="h-16" />
              ) : papers.length === 0 ? (
                <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                  No papers uploaded yet.{" "}
                  <Link href="/papers" className="underline">
                    Upload a PDF
                  </Link>{" "}
                  to ground reports in literature. Analysis still works without papers — the report
                  will rely on the LLM&apos;s prior knowledge instead of cited passages.
                </div>
              ) : (
                <div className="space-y-1.5">
                  {papers.map((p) => {
                    const checked = selectedPaperIds.has(p.paper_id);
                    return (
                      <label
                        key={p.paper_id}
                        className={`flex cursor-pointer items-start gap-3 rounded-md border p-2.5 text-sm transition-colors ${
                          checked
                            ? "border-primary/40 bg-primary/5"
                            : "border-transparent hover:bg-muted/40"
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 cursor-pointer accent-primary"
                          checked={checked}
                          onChange={() => togglePaper(p.paper_id)}
                          disabled={running}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 truncate font-medium">
                            <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            <span className="truncate">{p.title || p.filename}</span>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {p.pages} pages · {p.chunk_count} chunks
                          </div>
                        </div>
                      </label>
                    );
                  })}
                  <p className="pt-1 text-xs text-muted-foreground">
                    {selectedPaperIds.size === 0
                      ? "No papers selected — analysis will skip literature retrieval."
                      : `${selectedPaperIds.size} paper${
                          selectedPaperIds.size === 1 ? "" : "s"
                        } selected.`}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {error && (
            <Card>
              <CardContent className="pt-5 text-sm text-destructive">
                {error}
              </CardContent>
            </Card>
          )}

          {running && !report && (
            <div className="space-y-3">
              <Skeleton className="h-32" />
              <Skeleton className="h-64" />
            </div>
          )}

          {report && (
            <>
              <CompoundCard
                compound={report.compound}
                desc={report.descriptors}
                tox={report.toxicity}
              />
              <ReportViewer report={report} />
            </>
          )}
        </div>

        <McpTimeline events={events} />
      </div>
    </>
  );
}
