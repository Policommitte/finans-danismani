"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { AllocationSlice } from "../../models/portfolio";
import Card from "../ui/Card";

const colors = [
  "var(--color-primary)",
  "var(--color-success)",
  "var(--color-chart-yellow)",
  "var(--color-danger)",
  "var(--color-chart-purple)",
  "var(--color-chart-cyan)",
];

export function AssetAllocationChart({ items }: { items: AllocationSlice[] }) {
  return (
    <Card title="Varlik dagilimi">
      <div className="h-72">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={items} dataKey="class_pct" nameKey="asset_class" innerRadius={56} outerRadius={92}>
              {items.map((item, index) => (
                <Cell key={item.asset_class} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => `%${Number(value).toFixed(2)}`}
              contentStyle={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
                color: "var(--color-text)",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 grid gap-2 text-sm">
        {items.map((item, index) => (
          <div key={item.asset_class} className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />
              {item.asset_class}
            </span>
            <span className="font-medium">%{item.class_pct.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
