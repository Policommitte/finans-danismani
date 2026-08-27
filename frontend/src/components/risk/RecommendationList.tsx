import { useLanguage } from "../../contexts/LanguageContext";
import type { RiskProfileResponse } from "../../models/risk";
import Card from "../ui/Card";

export function RecommendationList({ risk }: { risk: RiskProfileResponse }) {
  const { language } = useLanguage();

  return (
    <Card title={language === "tr" ? "Risk gerekçeleri ve öneriler" : "Risk reasons and recommendations"}>
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold app-heading">{language === "tr" ? "Gerekçeler" : "Reasons"}</h3>
          <ul className="space-y-2 text-sm app-muted">
            {risk.reasons.map((reason) => (
              <li key={reason} className="rounded-md app-card-muted p-3">
                {reason}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold app-heading">{language === "tr" ? "Öneriler" : "Recommendations"}</h3>
          <ul className="space-y-2 text-sm app-muted">
            {risk.suggestions.map((suggestion) => (
              <li key={suggestion} className="rounded-md app-primary-soft p-3">
                {suggestion}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
