import Button from "../ui/Button";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border app-danger-box p-5 text-sm">
      <div className="font-semibold">Veri alinamadi</div>
      <p className="mt-1">{message}</p>
      {onRetry && (
        <Button className="mt-3" variant="secondary" onClick={onRetry}>
          Tekrar dene
        </Button>
      )}
    </div>
  );
}
