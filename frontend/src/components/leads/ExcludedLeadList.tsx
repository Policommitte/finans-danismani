import type { LeadQueueItem } from "../../models/leads";
import Card from "../ui/Card";

const NEDEN_ETIKETLERI: Record<string, string> = {
  consent_missing: "İletişim izni yok",
  email_missing: "E-posta adresi yok",
  income_below_threshold: "Beyan edilmiş geliri yok",
  balance_below_threshold: "Portföy değeri çok düşük",
  above_upper_limit: "Zaten üst segment (kampanya dışı)",
  recently_active: "Yakın zamanda aktif",
  cooldown_active: "Yakın zamanda temas edildi",
};

export function ExcludedLeadList({ items }: { items: LeadQueueItem[] }) {
  return (
    <Card title="Dışlananlar">
      {items.length === 0 ? (
        <p className="text-sm app-muted">Dışlanan kimse yok.</p>
      ) : (
        <div className="divide-y app-border-soft">
          {items.map((item) => (
            <div key={item.user_id} className="flex items-center justify-between py-3 text-sm">
              <span>
                <span className="block font-medium app-heading">
                  {item.first_name} {item.last_name}
                </span>
                <span className="app-muted">{item.email}</span>
              </span>
              <span className="app-muted">
                {NEDEN_ETIKETLERI[item.exclusion_reason ?? ""] ?? item.exclusion_reason}
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}