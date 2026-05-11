// Mirrors backend/app/models/schemas.py — keep in sync.

export type RiskBand = "low" | "moderate" | "high";

export interface CompoundIdentity {
  cid?: number | null;
  name?: string | null;
  iupac_name?: string | null;
  smiles?: string | null;
  inchi?: string | null;
  inchikey?: string | null;
  formula?: string | null;
  mw?: number | null;
}

export interface Descriptors {
  mw?: number | null;
  logp?: number | null;
  tpsa?: number | null;
  h_donors?: number | null;
  h_acceptors?: number | null;
  rotatable_bonds?: number | null;
  aromatic_rings?: number | null;
  heavy_atoms?: number | null;
  qed?: number | null;
  lipinski_violations?: number | null;
}

export interface StructuralAlert {
  name: string;
  smarts: string;
  severity: "low" | "medium" | "high";
  description: string;
}

export interface ToxicitySignal {
  score: number;
  risk_band: RiskBand;
  confidence: number;
  structural_alerts: StructuralAlert[];
  physchem_flags: string[];
}

export interface RetrievedChunk {
  paper_id: string;
  chunk_idx: number;
  page: number;
  text: string;
  score: number;
}

export interface Citation {
  n: number;
  paper_id: string;
  page: number;
  snippet: string;
}

export interface ToxicityReport {
  compound: CompoundIdentity;
  descriptors: Descriptors;
  toxicity: ToxicitySignal;
  summary_md: string;
  affected_pathways: string[];
  evidence: RetrievedChunk[];
  citations: Citation[];
  disclaimer: string;
  generated_at: string;
}

export type TraceKind =
  | "intent"
  | "plan"
  | "tool_call"
  | "tool_result"
  | "llm_call"
  | "llm_chunk"
  | "done"
  | "error";

export interface TraceEvent {
  kind: TraceKind;
  label: string;
  server?: string | null;
  tool?: string | null;
  args?: Record<string, unknown> | null;
  output?: Record<string, unknown> | string | null;
  duration_ms?: number | null;
  text?: string | null;
  ts: string;
}

export interface PaperMeta {
  paper_id: string;
  filename: string;
  title?: string | null;
  pages: number;
  chunk_count: number;
  uploaded_at: string;
}
