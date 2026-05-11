"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronRight, Search, ShieldAlert, ShieldCheck, TrendingUp } from "lucide-react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { RiskBand, ToxicityReport } from "@/lib/types";

interface Row {
  id: string;
  created_at: string;
  payload: ToxicityReport;
}

type Filter = "all" | RiskBand;

export default function ReportsPage() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [q, setQ] = useState("");

  useEffect(() => {
    api
      .listReports()
      .then((r) => setRows(r.reports ?? []))
      .catch((e) => setErr(String(e?.message ?? e)));
  }, []);

  const stats = useMemo(() => {
    if (!rows) return null;
    const byBand = { low: 0, moderate: 0, high: 0 } as Record<RiskBand, number>;
    const alertCounts: Record<string, number> = {};
    for (const r of rows) {
      byBand[r.payload.toxicity.risk_band] += 1;
      for (const a of r.payload.toxicity.structural_alerts) {
        alertCounts[a.name] = (alertCounts[a.name] ?? 0) + 1;
      }
    }
    const topAlert = Object.entries(alertCounts).sort((a, b) => b[1] - a[1])[0];
    return { total: rows.length, byBand, topAlert };
  }, [rows]);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const needle = q.trim().toLowerCase();
    return rows.filter((r) => {
      if (filter !== "all" && r.payload.toxicity.risk_band !== filter) return false;
      if (!needle) return true;
      const c = r.payload.compound;
      return [c.name, c.iupac_name, c.smiles, c.formula]
        .filter(Boolean)
        .some((v) => v!.toLowerCase().includes(needle));
    });
  }, [rows, filter, q]);

  return (
    <>
      <Topbar
        title="Reports"
        subtitle="Every analysis is auto-saved. Click a row to inspect, compare, or re-analyze."
      />
      <div className="flex-1 space-y-4 p-4 md:p-6">
        {err && (
          <Card>
            <CardContent className="pt-5 text-sm text-destructive">{err}</CardContent>
          </Card>
        )}

        {/* Stats banner */}
        {stats && (
          <div className="grid gap-3 md:grid-cols-4">
            <StatCard
              icon={TrendingUp}
              label="Total reports"
              value={stats.total}
            />
            <StatCard
              icon={ShieldAlert}
              label="High risk"
              value={stats.byBand.high}
              tone="high"
            />
            <StatCard
              icon={ShieldAlert}
              label="Moderate"
              value={stats.byBand.moderate}
              tone="moderate"
            />
            <StatCard
              icon={ShieldCheck}
              label="Low risk"
              value={stats.byBand.low}
              tone="low"
            />
          </div>
        )}

        {stats?.topAlert && (
          <Card>
            <CardContent className="flex items-center gap-3 py-3 text-sm">
              <span className="text-muted-foreground">Most frequent structural alert:</span>
              <Badge variant="secondary">{stats.topAlert[0]}</Badge>
              <span className="text-xs text-muted-foreground">
                seen in {stats.topAlert[1]} of {stats.total} reports
              </span>
            </CardContent>
          </Card>
        )}

        {/* Search + filter */}
        {rows && rows.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[240px]">
              <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search by name, SMILES, or formula…"
                className="pl-8"
              />
            </div>
            {(["all", "high", "moderate", "low"] as Filter[]).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={filter === f ? "default" : "outline"}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : f[0].toUpperCase() + f.slice(1)}
                {f !== "all" && stats && (
                  <span className="ml-1 text-xs opacity-75">({stats.byBand[f]})</span>
                )}
              </Button>
            ))}
          </div>
        )}

        {!rows && !err && (
          <div className="space-y-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        )}

        {rows && rows.length === 0 && (
          <Card>
            <CardHeader>
              <CardTitle>No reports yet</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Run an analysis from{" "}
              <Link href="/analyze" className="underline">
                /analyze
              </Link>
              . Reports save automatically.
            </CardContent>
          </Card>
        )}

        {rows && rows.length > 0 && filtered.length === 0 && (
          <p className="text-sm text-muted-foreground">No reports match this filter.</p>
        )}

        {filtered.length > 0 && (
          <Card>
            <CardContent className="p-0">
              <ul className="divide-y">
                {filtered.map((r) => {
                  const c = r.payload.compound;
                  const t = r.payload.toxicity;
                  return (
                    <li key={r.id}>
                      <Link
                        href={`/reports/${r.id}`}
                        className="flex items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-secondary/50"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium">
                            {c.name || c.iupac_name || c.smiles || "Unknown"}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            {c.formula ?? "—"} · CID {c.cid ?? "—"} ·{" "}
                            {new Date(r.created_at).toLocaleString()} ·{" "}
                            {t.structural_alerts.length} alert
                            {t.structural_alerts.length === 1 ? "" : "s"}
                          </p>
                        </div>
                        <Badge variant={t.risk_band}>
                          {t.risk_band.toUpperCase()} {(t.score * 100).toFixed(0)}%
                        </Badge>
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  tone?: RiskBand;
}) {
  const toneColour =
    tone === "high"
      ? "text-risk-high"
      : tone === "moderate"
        ? "text-risk-moderate"
        : tone === "low"
          ? "text-risk-low"
          : "text-primary";
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold tabular-nums">{value}</p>
        </div>
        <Icon className={cn("h-5 w-5", toneColour)} />
      </CardContent>
    </Card>
  );
}
