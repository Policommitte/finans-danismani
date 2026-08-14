"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HistoryResponse } from "../../models/market";
import Card from "../ui/Card";

export function PriceHistoryChart({ history }: { history: HistoryResponse }) {
  return (
    <Card title={`${history.symbol} fiyat gecmisi`}>
      <div className="h-72">
        <ResponsiveContainer>
          <LineChart data={history.points}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="ts" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="price" stroke="#2563eb" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
