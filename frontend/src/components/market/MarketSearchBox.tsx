"use client";

import { FormEvent, useState } from "react";
import type { MarketSearchResponse } from "../../models/market";
import Button from "../ui/Button";
import Card from "../ui/Card";

export function MarketSearchBox({
  result,
  searching,
  onSearch,
}: {
  result: MarketSearchResponse | null;
  searching: boolean;
  onSearch: (query: string) => void;
}) {
  const [query, setQuery] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    onSearch(query);
  }

  return (
    <Card title="RAG destekli piyasa aramasi">
      <form className="flex gap-2" onSubmit={submit}>
        <input
          className="min-w-0 flex-1 rounded-md border app-input px-3 py-2 text-sm outline-none"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="THYAO haberleri, son bilanco, piyasa yorumu..."
        />
        <Button disabled={searching}>{searching ? "Araniyor" : "Ara"}</Button>
      </form>
      {result && (
        <div className="mt-4 space-y-3">
          {result.items.map((item) => (
            <div key={`${item.doc_id}-${item.baslik}`} className="rounded-md app-card-muted p-3 text-sm">
              <div className="font-medium app-heading">{item.baslik ?? item.symbol ?? "Kaynak"}</div>
              <div className="mt-1 app-muted">{item.excerpt}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
