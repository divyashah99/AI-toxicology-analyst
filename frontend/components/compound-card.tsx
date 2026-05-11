import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fmt } from "@/lib/utils";
import type { CompoundIdentity, Descriptors, ToxicitySignal } from "@/lib/types";

export function CompoundCard({
  compound,
  desc,
  tox,
}: {
  compound: CompoundIdentity;
  desc: Descriptors;
  tox: ToxicitySignal;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="truncate">
              {compound.name || compound.iupac_name || "Unknown compound"}
            </CardTitle>
            <p className="mono mt-1 truncate text-xs text-muted-foreground">
              {compound.smiles}
            </p>
          </div>
          <div
            className="flex flex-col items-end gap-1"
            title={`Heuristic risk score from structural alerts + physchem flags. Score ${(tox.score * 100).toFixed(0)}% (band ${tox.risk_band}), confidence ${(tox.confidence * 100).toFixed(0)}%.`}
          >
            <Badge variant={tox.risk_band}>
              {tox.risk_band.toUpperCase()} RISK
            </Badge>
            <span className="text-xs text-muted-foreground">
              score {(tox.score * 100).toFixed(0)}/100 · conf{" "}
              {(tox.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm md:grid-cols-4">
        <Stat label="CID" value={compound.cid ?? "—"} />
        <Stat label="Formula" value={compound.formula ?? "—"} />
        <Stat label="MW" value={fmt(desc.mw, 1)} />
        <Stat label="logP" value={fmt(desc.logp, 2)} />
        <Stat label="TPSA" value={fmt(desc.tpsa, 0)} />
        <Stat label="HBD / HBA" value={`${desc.h_donors ?? "—"} / ${desc.h_acceptors ?? "—"}`} />
        <Stat label="QED" value={fmt(desc.qed, 2)} />
        <Stat label="Lipinski" value={`${desc.lipinski_violations ?? 0} viol.`} />
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}
