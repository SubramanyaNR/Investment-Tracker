"use client";

import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import type { Snapshot } from "@/lib/api";

function fmt(v: number) {
  if (v >= 10_000_000) return "₹" + (v / 10_000_000).toFixed(1) + "Cr";
  if (v >= 100_000)    return "₹" + (v / 100_000).toFixed(1) + "L";
  return "₹" + v.toLocaleString("en-IN");
}

function ChartTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-3 py-2.5 text-xs"
      style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", boxShadow: "var(--shadow-elevated)" }}>
      <p className="mb-1.5 text-[10px]" style={{ color: "var(--text-muted)" }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="font-semibold" style={{ color: p.color }}>
          {p.name}: {fmt(p.value)}
        </p>
      ))}
    </div>
  );
}

export default function NetWorthChart({ snapshots }: { snapshots: Snapshot[] }) {
  if (snapshots.length === 0) return null;

  const data = snapshots.map((s) => ({
    date: s.snapshot_date,
    "Net Worth": s.total_value,
    "Invested":  s.total_invested,
  }));

  return (
    <section className="card card-amber rounded-xl p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="section-title">Net Worth Over Time</h2>
          <p className="section-sub">
            {snapshots.length} {snapshots.length === 1 ? "snapshot" : "snapshots"} · refreshes daily
          </p>
        </div>
        {snapshots.length === 1 && (
          <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>More data builds with each daily refresh</span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={210}>
        <LineChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "var(--text-muted)" }} tickLine={false} axisLine={false} />
          <YAxis tickFormatter={fmt} tick={{ fontSize: 9, fill: "var(--text-muted)" }} tickLine={false} axisLine={false} width={64} />
          <Tooltip content={<ChartTooltip />} />
          <Line type="monotone" dataKey="Net Worth" stroke="#f59e0b" strokeWidth={2}
            dot={snapshots.length === 1 ? { fill: "#f59e0b", r: 4 } : false}
            activeDot={{ r: 4, fill: "#f59e0b" }} />
          <Line type="monotone" dataKey="Invested" stroke="#a78bfa" strokeWidth={1.5}
            strokeDasharray="5 3" dot={false} activeDot={{ r: 3, fill: "#a78bfa" }} />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-3 flex items-center gap-5">
        <span className="flex items-center gap-1.5 text-[10px]" style={{ color: "var(--text-secondary)" }}>
          <span className="h-[2px] w-5 rounded-full bg-amber-400" />Net Worth
        </span>
        <span className="flex items-center gap-1.5 text-[10px]" style={{ color: "var(--text-secondary)" }}>
          <span className="h-[2px] w-5 rounded-full bg-violet-400 opacity-60"
            style={{ backgroundImage: "repeating-linear-gradient(90deg,#a78bfa 0,#a78bfa 4px,transparent 4px,transparent 7px)" }} />
          Invested
        </span>
      </div>
    </section>
  );
}
