export type RiskTone = {
  textClass: string;
  color: string;
};

const riskTones: Record<string, RiskTone> = {
  dusuk: { textClass: "app-success", color: "var(--color-success)" },
  orta: { textClass: "text-[var(--color-warning-text)]", color: "var(--color-warning-text)" },
  yuksek: { textClass: "app-danger", color: "var(--color-danger)" },
  "cok yuksek": { textClass: "app-danger", color: "var(--color-danger)" },
  hesaplanamadi: { textClass: "app-muted", color: "var(--color-muted)" },
};

export function getRiskTone(level: string): RiskTone {
  return riskTones[level.toLocaleLowerCase("tr-TR")] ?? riskTones.hesaplanamadi;
}
