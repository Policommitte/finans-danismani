import type { RiskProfileResponse } from "../../models/risk";
import Card from "../ui/Card";

export function RecommendationList({ risk }: { risk: RiskProfileResponse }) {
  return (
    <Card title="Risk gerekceleri ve oneriler">
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Gerekceler</h3>
          <ul className="space-y-2 text-sm text-slate-600">
            {risk.reasons.map((reason) => (
              <li key={reason} className="rounded-md bg-slate-50 p-3">
                {reason}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Oneriler</h3>
          <ul className="space-y-2 text-sm text-slate-600">
            {risk.suggestions.map((suggestion) => (
              <li key={suggestion} className="rounded-md bg-blue-50 p-3 text-blue-900">
                {suggestion}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
