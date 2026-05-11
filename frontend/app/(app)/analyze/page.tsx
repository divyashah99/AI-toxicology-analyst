"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { McpTimeline } from "@/components/mcp-timeline";
import { CompoundCard } from "@/components/compound-card";
import { ReportViewer } from "@/components/report-viewer";
import { useAnalyzeStream } from "@/hooks/use-analyze-stream";

const EXAMPLES: { label: string; smiles?: string; name?: string }[] = [
  { label: "Caffeine", name: "caffeine" },
  { label: "Aspirin", name: "aspirin" },
  { label: "Bisphenol A", smiles: "CC(C)(c1ccc(O)cc1)c1ccc(O)cc1" },
  { label: "Aflatoxin B1", name: "aflatoxin B1" },
];

// Outer component: wrap the inner client component in <Suspense> so Next can
// statically render the shell. `useSearchParams` requires this in Next 15+.
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
  const { events, report, running, error, run } = useAnalyzeStream();

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

  const submit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!name.trim() && !smiles.trim()) return;
    run({
      query: {
        name: name.trim() || undefined,
        smiles: smiles.trim() || undefined,
      },
    });
  };

  const fillExample = (ex: (typeof EXAMPLES)[number]) => {
    setName(ex.name ?? "");
    setSmiles(ex.smiles ?? "");
    run({ query: { name: ex.name, smiles: ex.smiles } });
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
