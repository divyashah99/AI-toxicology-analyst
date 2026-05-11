"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Trash2 } from "lucide-react";
import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CompoundCard } from "@/components/compound-card";
import { ReportViewer } from "@/components/report-viewer";
import { api } from "@/lib/api";
import type { ToxicityReport } from "@/lib/types";

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<ToxicityReport | null>(null);
  const [createdAt, setCreatedAt] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id) return;
    api
      .getReport(params.id)
      .then((r) => {
        setReport(r.payload);
        setCreatedAt(r.created_at);
      })
      .catch((e) => setErr(String(e?.message ?? e)));
  }, [params?.id]);

  const onDelete = async () => {
    if (!params?.id) return;
    if (!confirm("Delete this report? This cannot be undone.")) return;
    await api.deleteReport(params.id);
    router.push("/reports");
  };

  const reanalyzeHref = report
    ? {
        pathname: "/analyze",
        query: {
          name: report.compound.name ?? "",
          smiles: report.compound.smiles ?? "",
        },
      }
    : "/analyze";

  return (
    <>
      <Topbar
        title={report?.compound.name || report?.compound.iupac_name || "Report"}
        subtitle={createdAt ? `Saved ${new Date(createdAt).toLocaleString()}` : ""}
      />
      <div className="flex-1 space-y-4 p-4 md:p-6">
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/reports">
              <ArrowLeft className="mr-1 h-4 w-4" /> All reports
            </Link>
          </Button>
          <div className="flex-1" />
          {report && (
            <Button variant="outline" size="sm" asChild>
              <Link href={reanalyzeHref}>
                <RefreshCw className="mr-1 h-4 w-4" /> Re-analyze
              </Link>
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={onDelete}>
            <Trash2 className="mr-1 h-4 w-4" /> Delete
          </Button>
        </div>

        {err && (
          <Card>
            <CardContent className="pt-5 text-sm text-destructive">{err}</CardContent>
          </Card>
        )}
        {!report && !err && (
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
    </>
  );
}
