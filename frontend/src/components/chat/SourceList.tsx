import type { Source } from "../../models/chat";

export function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1">
      {sources.slice(0, 3).map((source) => (
        <div key={source.doc_id} className="rounded-md bg-white/80 px-2 py-1 text-xs text-slate-600">
          {source.baslik}
          {source.sirket ? ` · ${source.sirket}` : ""}
        </div>
      ))}
    </div>
  );
}
