import type { RiskProfileResponse } from "../../models/risk";
import Card from "../ui/Card";

export function RiskScoreCard({ risk }: { risk: RiskProfileResponse }) {
  return (
    <Card title="Risk profili">
      <div className="flex items-end gap-3">
        <div className="text-5xl font-semibold app-heading">{risk.risk_score}</div>
        <div className="pb-1 text-sm app-muted">/ 100</div>
      </div>
      <div className="mt-3 text-sm font-medium app-primary-text">{risk.risk_level}</div>
      <div className="mt-4 h-2 rounded-full app-card-muted">
        <div className="h-2 rounded-full app-primary" style={{ width: `${Math.min(risk.risk_score, 100)}%` }} />
      </div>
      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="app-muted">Risk toleransi</dt>
          <dd className="font-medium">{risk.risk_tolerance ?? "Bilinmiyor"}</dd>
        </div>
        <div>
          <dt className="app-muted">Uyum</dt>
          <dd className="font-medium">{risk.tolerance_alignment}</dd>
        </div>
      </dl>
    </Card>
  );
}
