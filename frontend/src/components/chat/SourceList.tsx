import type { Source } from "../../models/chat";

export function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1">
      {sources.slice(0, 3).map((source) => (
        <div key={source.doc_id} className="rounded-md app-surface px-2 py-1 text-xs app-muted">
          {source.baslik}
          {source.sirket ? ` · ${source.sirket}` : ""}
        </div>
      ))}
    </div>
  );
}
