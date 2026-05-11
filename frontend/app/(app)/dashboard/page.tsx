import Link from "next/link";
import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Beaker, FileText, GitBranch } from "lucide-react";

export default function DashboardPage() {
  return (
    <>
      <Topbar title="Dashboard" subtitle="Overview of MCP servers and your workspace" />
      <div className="grid flex-1 gap-4 p-4 md:grid-cols-3 md:p-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Beaker className="h-4 w-4 text-primary" /> Analyze
            </CardTitle>
            <CardDescription>Run a compound through PubChem + RDKit + toxicity scoring.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/analyze">Open analyzer →</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" /> Papers
            </CardTitle>
            <CardDescription>Upload PDFs to ground reports in literature.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="secondary" asChild>
              <Link href="/papers">Manage library →</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-primary" /> MCP servers
            </CardTitle>
            <CardDescription>4 servers in-process: PubChem, RDKit, Papers, Toxicity.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Worst-case 3 LLM calls per analysis. ChromaDB persistent retrieval.
            </p>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
