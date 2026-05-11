"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ToxicityReport } from "@/lib/types";

export function ReportViewer({ report }: { report: ToxicityReport }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardTitle>Toxicology brief</CardTitle>
            <Badge variant={report.toxicity.risk_band}>
              {report.toxicity.risk_band.toUpperCase()} · conf{" "}
              {(report.toxicity.confidence * 100).toFixed(0)}%
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {report.summary_md}
          </ReactMarkdown>
        </CardContent>
      </Card>

      {report.toxicity.structural_alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Structural alerts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.toxicity.structural_alerts.map((a, i) => (
              <div key={i} className="rounded border bg-muted/30 p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{a.name}</span>
                  <Badge
                    variant={
                      a.severity === "high"
                        ? "high"
                        : a.severity === "medium"
                          ? "moderate"
                          : "low"
                    }
                  >
                    {a.severity}
                  </Badge>
                </div>
                <p className="mono mt-1 text-xs text-muted-foreground">{a.smarts}</p>
                <p className="mt-1 text-xs">{a.description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {report.citations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Citations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.citations.map((c) => (
              <div key={c.n} className="text-sm">
                <span className="mr-2 inline-block rounded-full bg-secondary px-2 py-0.5 text-xs">
                  [{c.n}]
                </span>
                <span className="text-muted-foreground">paper {c.paper_id.slice(0, 8)} · p.{c.page}</span>
                <p className="mt-1 italic text-muted-foreground">{c.snippet}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground">{report.disclaimer}</p>
    </div>
  );
}
