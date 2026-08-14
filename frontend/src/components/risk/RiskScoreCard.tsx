import type { RiskProfileResponse } from "../../models/risk";
import Card from "../ui/Card";

export function RiskScoreCard({ risk }: { risk: RiskProfileResponse }) {
  return (
    <Card title="Risk profili">
      <div className="flex items-end gap-3">
        <div className="text-5xl font-semibold text-slate-950">{risk.risk_score}</div>
        <div className="pb-1 text-sm text-slate-500">/ 100</div>
      </div>
      <div className="mt-3 text-sm font-medium text-blue-800">{risk.risk_level}</div>
      <div className="mt-4 h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-blue-700" style={{ width: `${Math.min(risk.risk_score, 100)}%` }} />
      </div>
      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Risk toleransi</dt>
          <dd className="font-medium">{risk.risk_tolerance ?? "Bilinmiyor"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Uyum</dt>
          <dd className="font-medium">{risk.tolerance_alignment}</dd>
        </div>
      </dl>
    </Card>
  );
}
