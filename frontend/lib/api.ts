import type { PaperMeta, ToxicityReport, TraceEvent } from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,

  health: () => http<{ status: string }>("/healthz"),

  servers: () =>
    http<{ servers: Array<{ name: string; description: string; tools: { name: string; description: string }[] }> }>(
      "/api/analyze/servers",
    ),

  // ----- papers -----
  listPapers: () => http<{ papers: PaperMeta[]; chunks_indexed: number }>("/api/papers"),

  uploadPaper: async (file: File): Promise<PaperMeta> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/api/papers/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  deletePaper: (id: string) =>
    fetch(`${BASE}/api/papers/${id}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) throw new Error(r.statusText);
    }),

  // ----- reports -----
  listReports: () =>
    http<{ reports: Array<{ id: string; created_at: string; payload: ToxicityReport }> }>(
      "/api/reports",
    ),

  getReport: (id: string) =>
    http<{ id: string; created_at: string; payload: ToxicityReport }>(
      `/api/reports/${id}`,
    ),

  deleteReport: (id: string) =>
    fetch(`${BASE}/api/reports/${id}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) throw new Error(r.statusText);
    }),

  // ----- analyze (one-shot) -----
  analyze: (body: {
    query: { name?: string; smiles?: string; cid?: number };
    paper_ids?: string[];
  }) =>
    http<{ report: ToxicityReport; trace: TraceEvent[] }>("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ ...body, stream: false }),
    }),
};

/** Stream the analyze SSE endpoint. Returns an async iterable of parsed events. */
export async function* analyzeStream(body: {
  query: { name?: string; smiles?: string; cid?: number };
  paper_ids?: string[];
}): AsyncGenerator<{ event: string; data: any }> {
  const res = await fetch(`${BASE}/api/analyze/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);
  yield* parseSse(res.body);
}

export async function* chatStream(body: {
  messages: { role: "user" | "assistant" | "system"; content: string }[];
  paper_ids?: string[];
}): AsyncGenerator<{ event: string; data: any }> {
  const res = await fetch(`${BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);
  yield* parseSse(res.body);
}

async function* parseSse(stream: ReadableStream<Uint8Array>) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const lines = block.split("\n");
      let event = "message";
      let data = "";
      for (const ln of lines) {
        if (ln.startsWith("event:")) event = ln.slice(6).trim();
        else if (ln.startsWith("data:")) data += ln.slice(5).trim();
      }
      if (!data) continue;
      try {
        yield { event, data: JSON.parse(data) };
      } catch {
        yield { event, data };
      }
    }
  }
}
