import type { LeadScanSummary } from "../../models/leads";
import Button from "../ui/Button";
import Card from "../ui/Card";

export function LeadScanSummaryCard({
  scan,
  scanning,
  onRunScan,
}: {
  scan: LeadScanSummary;
  scanning: boolean;
  onRunScan: () => void;
}) {
  return (
    <Card title="Son tarama">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-6 text-sm">
          <span>
            <span className="block app-muted">Taranan</span>
            <span className="font-medium app-heading">{scan.scanned_count}</span>
          </span>
          <span>
            <span className="block app-muted">BSD kuyruğu</span>
            <span className="font-medium app-heading">{scan.bsd_count}</span>
          </span>
          <span>
            <span className="block app-muted">Otonom (mail)</span>
            <span className="font-medium app-heading">{scan.autonomous_count}</span>
          </span>
          <span>
            <span className="block app-muted">Dışlanan</span>
            <span className="font-medium app-heading">{scan.excluded_count}</span>
          </span>
          <span>
            <span className="block app-muted">Gönderilen mail</span>
            <span className="font-medium app-heading">{scan.emailed_count}</span>
          </span>
        </div>
        <Button variant="secondary" onClick={onRunScan} disabled={scanning}>
          {scanning ? "Taranıyor..." : "Taramayı yeniden çalıştır"}
        </Button>
      </div>
    </Card>
  );
}