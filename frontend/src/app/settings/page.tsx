import Card from "../../components/ui/Card";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">Ayarlar</h1>
        <p className="mt-1 text-sm app-muted">Bu ekran yakında hazır olacak.</p>
      </div>
      <Card title="Yakında">
        <p className="text-sm app-muted">
          Ayarlar sayfasının içeriği ve tasarımı ayrıca iletilecek. Bu ekran şimdilik placeholder olarak tutulur.
        </p>
      </Card>
    </div>
  );
}
