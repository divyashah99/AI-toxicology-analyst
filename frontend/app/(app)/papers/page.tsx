"use client";
import { useEffect, useRef, useState } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { PaperMeta } from "@/lib/types";
import { Trash2, Upload } from "lucide-react";

export default function PapersPage() {
  const [papers, setPapers] = useState<PaperMeta[]>([]);
  const [chunks, setChunks] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = async () => {
    try {
      const r = await api.listPapers();
      setPapers(r.papers ?? []);
      setChunks(r.chunks_indexed ?? 0);
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      await api.uploadPaper(file);
      await refresh();
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const onDelete = async (id: string) => {
    setBusy(true);
    try {
      await api.deletePaper(id);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Topbar
        title="Papers"
        subtitle={`${papers.length} paper${papers.length === 1 ? "" : "s"} · ${chunks} chunks indexed`}
      />
      <div className="flex-1 space-y-4 p-4 md:p-6">
        <Card>
          <CardHeader>
            <CardTitle>Upload PDF</CardTitle>
          </CardHeader>
          <CardContent>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              hidden
              onChange={onUpload}
            />
            <Button
              disabled={busy}
              onClick={() => inputRef.current?.click()}
              className="gap-2"
            >
              <Upload className="h-4 w-4" />
              {busy ? "Uploading…" : "Choose PDF"}
            </Button>
            {err && <p className="mt-2 text-sm text-destructive">{err}</p>}
            <p className="mt-2 text-xs text-muted-foreground">
              Parsed locally with pypdf, chunked, embedded with OpenAI, stored in
              ChromaDB. Max 20 MB per file.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Library</CardTitle>
          </CardHeader>
          <CardContent>
            {papers.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No papers uploaded yet.
              </p>
            ) : (
              <ul className="divide-y">
                {papers.map((p) => (
                  <li key={p.paper_id} className="flex items-center gap-3 py-3 text-sm">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{p.title || p.filename}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {p.filename} · {p.pages} pages · {p.chunk_count} chunks
                      </p>
                    </div>
                    <Badge variant="outline">{p.paper_id.slice(0, 8)}</Badge>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => onDelete(p.paper_id)}
                      disabled={busy}
                      aria-label="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
