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
            <CartesianGrid stroke="var(--color-chart-grid)" strokeDasharray="3 3" />
            <XAxis dataKey="ts" tick={{ fontSize: 11, fill: "var(--color-muted)" }} />
            <YAxis tick={{ fontSize: 11, fill: "var(--color-muted)" }} />
            <Tooltip
              contentStyle={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
                color: "var(--color-text)",
              }}
            />
            <Line type="monotone" dataKey="price" stroke="var(--color-primary)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
