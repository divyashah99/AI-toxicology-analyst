import Link from "next/link";
import { Beaker, FlaskConical, GitBranch, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

export default function Landing() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,hsl(199_89%_48%/0.18),transparent_60%)]" />
      <header className="relative z-10 flex items-center justify-between px-6 py-4 md:px-10">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-md bg-primary text-primary-foreground">
            <Beaker className="h-4 w-4" />
          </div>
          <span className="font-semibold tracking-tight">ToxAnalyst</span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild>
            <Link href="/dashboard">Open app →</Link>
          </Button>
        </div>
      </header>

      <section className="relative z-10 mx-auto max-w-5xl px-6 py-20 text-center md:py-28">
        <span className="inline-flex items-center gap-2 rounded-full border bg-card/60 px-3 py-1 text-xs text-muted-foreground backdrop-blur">
          <Sparkles className="h-3 w-3" /> MCP-orchestrated. Cost-aware. Deployable today.
        </span>
        <h1 className="mt-6 text-4xl font-semibold tracking-tight md:text-6xl">
          AI Toxicology Analyst
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-base text-muted-foreground md:text-lg">
          Drop in a compound or a research PDF. The agent orchestrates four MCP
          servers — PubChem, RDKit, Papers, Toxicity — to produce a citation-aware
          risk brief with a transparent reasoning trace.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Button size="lg" asChild>
            <Link href="/analyze">Analyze a compound</Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/papers">Upload a paper</Link>
          </Button>
        </div>
      </section>

      <section className="relative z-10 mx-auto grid max-w-5xl gap-6 px-6 pb-24 md:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="rounded-lg border bg-card/60 p-5 backdrop-blur">
            <f.icon className="h-5 w-5 text-primary" />
            <h3 className="mt-3 text-sm font-semibold">{f.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{f.body}</p>
          </div>
        ))}
      </section>
    </main>
  );
}

const features = [
  {
    icon: GitBranch,
    title: "Deterministic agent",
    body: "Worst-case ~3 LLM calls per analysis. Predictable, low-cost, easy to audit.",
  },
  {
    icon: FlaskConical,
    title: "Real cheminformatics",
    body: "RDKit descriptors, fingerprints, similarity. PubChem identity. ChromaDB retrieval.",
  },
  {
    icon: Sparkles,
    title: "Reasoning transparency",
    body: "Every tool call, args, and duration streams to the UI as a live timeline.",
  },
];
