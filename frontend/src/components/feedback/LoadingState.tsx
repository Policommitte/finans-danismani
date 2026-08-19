export function LoadingState({ label = "Veriler yukleniyor" }: { label?: string }) {
  return (
    <div className="rounded-lg border app-card p-6 text-sm app-muted">
      {label}...
    </div>
  );
}
