"use client";

import { useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import type { Snapshot } from "@/lib/api";

type RangeKey = "1W" | "1M" | "1Y" | "ALL";

const RANGE_OPTIONS: RangeKey[] = ["1W", "1M", "1Y", "ALL"];

function fmt(v: number) {
  if (v >= 10_000_000) return "₹" + (v / 10_000_000).toFixed(1) + "Cr";
  if (v >= 100_000)    return "₹" + (v / 100_000).toFixed(1) + "L";
  return "₹" + v.toLocaleString("en-IN");
}

function snapshotTime(date: string) {
  return new Date(`${date}T00:00:00`).getTime();
}

function rangeStart(range: RangeKey) {
  if (range === "ALL") return null;

  const start = new Date();
  start.setHours(0, 0, 0, 0);

  if (range === "1W") start.setDate(start.getDate() - 7);
  if (range === "1M") start.setMonth(start.getMonth() - 1);
  if (range === "1Y") start.setFullYear(start.getFullYear() - 1);

  return start.getTime();
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
  const [range, setRange] = useState<RangeKey>("1M");

  if (snapshots.length === 0) return null;

  const start = rangeStart(range);
  const filteredSnapshots = start === null
    ? snapshots
    : snapshots.filter((s) => snapshotTime(s.snapshot_date) >= start);
  const showDots = filteredSnapshots.length < 10;

  const data = filteredSnapshots.map((s) => ({
    date: s.snapshot_date,
    "Net Worth": s.total_value,
    "Invested":  s.total_invested,
  }));

  return (
    <section className="card card-amber rounded-xl p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="section-title">Net Worth Over Time</h2>
          <p className="section-sub">
            {filteredSnapshots.length} of {snapshots.length} {snapshots.length === 1 ? "snapshot" : "snapshots"}
          </p>
        </div>
        <div className="flex shrink-0 overflow-hidden rounded-lg"
          style={{ border: "1px solid var(--border-subtle)" }}>
          {RANGE_OPTIONS.map((option, i) => (
            <button key={option} type="button" onClick={() => setRange(option)}
              aria-pressed={range === option}
              className="min-h-8 min-w-10 px-2.5 py-1 text-[10px] font-semibold uppercase transition-colors sm:min-w-11 sm:px-3"
              style={{
                background: range === option ? "var(--input-focus-bg)" : "transparent",
                color: range === option ? "var(--text-primary)" : "var(--text-muted)",
                borderLeft: i > 0 ? "1px solid var(--border-subtle)" : undefined,
                backgroundColor: range === option ? "rgba(245,158,11,0.15)" : undefined,
              }}>
              {option}
            </button>
          ))}
        </div>
      </div>

      {data.length === 0 ? (
        <div className="flex h-[210px] items-center justify-center rounded-lg border border-dashed px-4 text-center"
          style={{ borderColor: "var(--border-subtle)", color: "var(--text-muted)" }}>
          <p className="text-xs">No data for this period — try a wider range.</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={210}>
          <LineChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 9, fill: "var(--text-muted)" }} tickLine={false} axisLine={false} />
            <YAxis tickFormatter={fmt} tick={{ fontSize: 9, fill: "var(--text-muted)" }} tickLine={false} axisLine={false} width={64} />
            <Tooltip content={<ChartTooltip />} />
            <Line type="monotone" dataKey="Net Worth" stroke="#f59e0b" strokeWidth={2}
              dot={showDots ? { fill: "#f59e0b", r: 3 } : false}
              activeDot={{ r: 4, fill: "#f59e0b" }} />
            <Line type="monotone" dataKey="Invested" stroke="#a78bfa" strokeWidth={1.5}
              strokeDasharray="5 3" dot={showDots ? { fill: "#a78bfa", r: 2.5 } : false} activeDot={{ r: 3, fill: "#a78bfa" }} />
          </LineChart>
        </ResponsiveContainer>
      )}

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
