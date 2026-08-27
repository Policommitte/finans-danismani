import { useLanguage } from "../../contexts/LanguageContext";
import type { RiskProfileResponse } from "../../models/risk";
import Card from "../ui/Card";

const riskLevelLabels: Record<string, string> = {
  dusuk: "low",
  orta: "medium",
  yuksek: "high",
  "cok yuksek": "very high",
};

const riskLevelLabelsTr: Record<string, string> = {
  dusuk: "Düşük",
  orta: "Orta",
  yuksek: "Yüksek",
  "cok yuksek": "Çok yüksek",
  hesaplanamadi: "Hesaplanamadı",
};

const toleranceLabelsTr: Record<string, string> = {
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
};

const alignmentLabels: Record<string, string> = {
  uyumlu: "aligned",
  "tolerans ustu": "above tolerance",
  "tolerans alti": "below tolerance",
};

const alignmentLabelsTr: Record<string, string> = {
  uyumlu: "Uyumlu",
  "tolerans ustu": "Tolerans üstü",
  "tolerans alti": "Tolerans altı",
  bilinmiyor: "Bilinmiyor",
};

export function RiskScoreCard({ risk }: { risk: RiskProfileResponse }) {
  const { language } = useLanguage();
  const riskLevelKey = risk.risk_level.toLocaleLowerCase("tr-TR");
  const alignmentKey = risk.tolerance_alignment.toLocaleLowerCase("tr-TR");

  return (
    <Card title={language === "tr" ? "Risk profili" : "Risk profile"}>
      <div className="flex items-end gap-3">
        <div className="text-5xl font-semibold app-heading">{risk.risk_score}</div>
        <div className="pb-1 text-sm app-muted">/ 100</div>
      </div>
      <div className="mt-3 text-sm font-medium app-primary-text">
        {language === "tr"
          ? riskLevelLabelsTr[riskLevelKey] ?? risk.risk_level
          : riskLevelLabels[riskLevelKey] ?? risk.risk_level}
      </div>
      <div className="mt-4 h-2 rounded-full app-card-muted">
        <div className="h-2 rounded-full app-primary" style={{ width: `${Math.min(risk.risk_score, 100)}%` }} />
      </div>
      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="app-muted">{language === "tr" ? "Risk toleransı" : "Risk tolerance"}</dt>
          <dd className="font-medium">
            {risk.risk_tolerance
              ? language === "tr"
                ? toleranceLabelsTr[risk.risk_tolerance.toUpperCase()] ?? risk.risk_tolerance
                : risk.risk_tolerance
              : language === "tr"
                ? "Bilinmiyor"
                : "Unknown"}
          </dd>
        </div>
        <div>
          <dt className="app-muted">{language === "tr" ? "Uyum" : "Alignment"}</dt>
          <dd className="font-medium">
            {language === "tr"
              ? alignmentLabelsTr[alignmentKey] ?? risk.tolerance_alignment
              : alignmentLabels[alignmentKey] ?? risk.tolerance_alignment}
          </dd>
        </div>
      </dl>
    </Card>
  );
}
