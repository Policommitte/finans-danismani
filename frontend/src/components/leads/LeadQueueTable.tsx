import type { LeadQueueItem } from "../../models/leads";
import Badge from "../ui/Badge";
import Card from "../ui/Card";

export function LeadQueueTable({
  title,
  items,
  variant,
}: {
  title: string;
  items: LeadQueueItem[];
  variant: "bsd" | "autonomous";
}) {
  return (
    <Card title={title}>
      {items.length === 0 ? (
        <p className="text-sm app-muted">Bu kuyrukta kimse yok.</p>
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
              <span className="flex items-center gap-3">
                <span className="app-muted">Skor: {item.score}</span>
                <Badge className={variant === "bsd" ? "app-warning-box border" : "app-primary-soft"}>
                  {variant === "bsd" ? "Aranacak" : "Mail gönderildi"}
                </Badge>
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}