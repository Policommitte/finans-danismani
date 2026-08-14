import Card from "../../components/ui/Card";

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Raporlar</h1>
        <p className="mt-1 text-sm text-slate-500">Detayli rapor uretimi Sprint 4 kapsamindadir.</p>
      </div>
      <Card title="Sprint 4 kapsaminda">
        <p className="text-sm text-slate-600">
          Bu ekran simdilik stub olarak tutulur. Backend tarafinda rapor endpointleri acildiginda
          PDF/rapor listesi ve detayli rapor olusturma akisi buraya baglanacak.
        </p>
      </Card>
    </div>
  );
}
