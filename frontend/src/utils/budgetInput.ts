/**
 * Parses a free-text budget the user typed into the chat ("10.000 TL",
 * "25 bin", "1,5 milyon", "50k", "₺75000") into a TRY amount.
 *
 * Returns null when no usable number is found so the flow can ask again
 * instead of guessing.
 */
export function parseBudgetInput(raw: string): number | null {
  const text = raw
    .toLocaleLowerCase("tr-TR")
    .replace(/₺|tl\b|try\b|lira(sı)?\b/g, " ")
    .trim();
  if (!text) return null;

  if (/(^|\s)-\s*\d/.test(text)) return null;
  const match = text.match(/(\d[\d.,\s]*)\s*(bin|k|milyon|mn|m)?\b/);
  if (!match) return null;

  let digits = match[1].replace(/\s/g, "");
  const suffix = match[2];

  // "10.000" / "10,000" are thousand separators; "1,5" / "1.5" are decimals.
  const thousandsPattern = /^\d{1,3}([.,]\d{3})+$/;
  if (thousandsPattern.test(digits)) {
    digits = digits.replace(/[.,]/g, "");
  } else {
    digits = digits.replace(/\.(?=\d{3}\b)/g, "").replace(",", ".");
  }

  const value = Number(digits);
  if (!Number.isFinite(value) || value <= 0) return null;

  const multiplier = suffix === "bin" || suffix === "k" ? 1_000 : suffix ? 1_000_000 : 1;
  return Math.round(value * multiplier * 100) / 100;
}

export function formatBudget(amount: number, locale: "tr-TR" | "en-US" = "tr-TR"): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount);
}
