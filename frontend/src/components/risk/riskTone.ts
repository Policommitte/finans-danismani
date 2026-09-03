export type RiskTone = {
  textClass: string;
  color: string;
};

//: "orta" eskiden `--color-warning-text` kullaniyordu - okunabilirlik icin
//: koyulastirilmis bu ton kahverengiye cok yakin duruyordu. Trafik isigi
//: mantigina (dusuk=yesil, orta=sari, yuksek=kirmizi) tam oturmasi icin
//: gercek sari tondaki `--color-chart-yellow` kullanilir.
const riskTones: Record<string, RiskTone> = {
  dusuk: { textClass: "app-success", color: "var(--color-success)" },
  orta: { textClass: "text-[var(--color-chart-yellow)]", color: "var(--color-chart-yellow)" },
  yuksek: { textClass: "app-danger", color: "var(--color-danger)" },
  "cok yuksek": { textClass: "app-danger", color: "var(--color-danger)" },
  hesaplanamadi: { textClass: "app-muted", color: "var(--color-muted)" },
};

export function getRiskTone(level: string): RiskTone {
  return riskTones[level.toLocaleLowerCase("tr-TR")] ?? riskTones.hesaplanamadi;
}
