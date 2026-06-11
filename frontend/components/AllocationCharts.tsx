"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import type { Asset, Valuation } from "@/lib/api";

type PieEntry = { name: string; value: number; color: string };

const TYPE_GROUP: Record<string, { label: string; color: string }> = {
  CRYPTO:      { label: "Crypto",         color: "#f59e0b" },
  MUTUAL_FUND: { label: "Mutual Funds",   color: "#a78bfa" },
  FD:          { label: "Fixed Income",   color: "#38bdf8" },
  RD:          { label: "Fixed Income",   color: "#38bdf8" },
  PPF:         { label: "Fixed Income",   color: "#38bdf8" },
  SAVINGS_ACC: { label: "Cash & Savings", color: "#34d399" },
};

const LIQUIDITY_COLOR: Record<string, string> = {
  LIQUID: "#34d399",
  LOCKED: "#f97316",
};

function fmt(v: number) {
  if (v >= 10_000_000) return "₹" + (v / 10_000_000).toFixed(1) + "Cr";
  if (v >= 100_000)    return "₹" + (v / 100_000).toFixed(1) + "L";
  return "₹" + Math.round(v).toLocaleString("en-IN");
}

function PieTooltip({ active, payload }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: PieEntry }>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs"
      style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", boxShadow: "var(--shadow-elevated)" }}
    >
      <p className="font-semibold" style={{ color: d.payload.color }}>{d.name}</p>
      <p className="mt-0.5 text-slate-300" style={{ color: "var(--text-secondary)" }}>{fmt(d.value)}</p>
    </div>
  );
}

function EmptyState({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <div className="mb-3 h-16 w-16 rounded-full opacity-10" style={{ background: "conic-gradient(#f59e0b 0%, #a78bfa 33%, #38bdf8 66%, #34d399 100%)" }} />
      <p className="text-xs text-slate-600">{title}</p>
    </div>
  );
}

function DonutChart({ data, title, total }: { data: PieEntry[]; title: string; total: number }) {
  if (total === 0) return <EmptyState title="No data yet" />;

  return (
    <div>
      <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-600">{title}</p>
      <div className="relative">
        <ResponsiveContainer width="100%" height={160}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={48}
              outerRadius={68}
              dataKey="value"
              paddingAngle={2}
              strokeWidth={0}
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} opacity={0.9} />
              ))}
            </Pie>
            <Tooltip content={<PieTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-[13px] font-bold" style={{ color: "var(--text-primary)" }}>{fmt(total)}</p>
            <p className="text-[8px] text-slate-600 uppercase tracking-wider">total</p>
          </div>
        </div>
      </div>

      <div className="mt-3 space-y-1.5">
        {data.map((d, i) => {
          const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : "0";
          return (
            <div key={i} className="flex items-center justify-between gap-3">
              <span className="flex min-w-0 items-center gap-1.5">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: d.color }} />
                <span className="truncate text-[10px] text-slate-400">{d.name}</span>
              </span>
              <span className="shrink-0 text-[10px] font-medium text-slate-300">
                {fmt(d.value)}{" "}
                <span className="text-slate-600">{pct}%</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AllocationCharts({
  assets,
  valuations,
}: {
  assets: Asset[];
  valuations: Record<string, Valuation>;
}) {
  // Build asset-class pie data
  const typeMap = new Map<string, { label: string; color: string; value: number }>();
  for (const asset of assets) {
    const grp = TYPE_GROUP[asset.asset_type];
    const val = valuations[asset.id]?.current_value ?? 0;
    if (!grp || val === 0) continue;
    const existing = typeMap.get(grp.label);
    if (existing) {
      existing.value += val;
    } else {
      typeMap.set(grp.label, { label: grp.label, color: grp.color, value: val });
    }
  }
  const typeData: PieEntry[] = Array.from(typeMap.values()).map((d) => ({
    name: d.label,
    value: d.value,
    color: d.color,
  })).sort((a, b) => b.value - a.value);
  const typeTotal = typeData.reduce((s, d) => s + d.value, 0);

  // Build liquidity pie data
  const liquidityMap: Record<string, number> = { LIQUID: 0, LOCKED: 0 };
  for (const asset of assets) {
    const val = valuations[asset.id]?.current_value ?? 0;
    if (val === 0) continue;
    const tier = asset.liquidity_tier in liquidityMap ? asset.liquidity_tier : "LIQUID";
    liquidityMap[tier] += val;
  }
  const liquidityData: PieEntry[] = [
    { name: "Liquid",   value: liquidityMap.LIQUID, color: LIQUIDITY_COLOR.LIQUID },
    { name: "Locked",   value: liquidityMap.LOCKED, color: LIQUIDITY_COLOR.LOCKED },
  ].filter((d) => d.value > 0);
  const liquidityTotal = liquidityData.reduce((s, d) => s + d.value, 0);

  if (typeTotal === 0 && liquidityTotal === 0) return null;

  const hasManualAssets = assets.some((a) => a.asset_type === "MANUAL");

  return (
    <div>
    <section
      className="grid grid-cols-1 gap-5 sm:grid-cols-2"
    >
      <div
        className="card rounded-xl p-5"
        style={{
          background: "linear-gradient(160deg, rgba(245,158,11,0.05) 0%, var(--bg-surface) 50%)",
        }}
      >
        <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Asset Allocation</h2>
        <p className="mb-4 mt-0.5 text-[11px] text-slate-600">Portfolio by asset class</p>
        <DonutChart data={typeData} title="by value" total={typeTotal} />
      </div>

      <div
        className="card rounded-xl p-5"
        style={{
          background: "linear-gradient(160deg, rgba(52,211,153,0.05) 0%, var(--bg-surface) 50%)",
        }}
      >
        <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Liquidity Split</h2>
        <p className="mb-4 mt-0.5 text-[11px] text-slate-600">Accessible vs locked capital</p>
        <DonutChart data={liquidityData} title="by value" total={liquidityTotal} />
      </div>
    </section>
    {hasManualAssets && (
      <p className="mt-2 text-right text-[10px]" style={{ color: "var(--text-muted)" }}>
        Asset allocation excludes manually tracked assets.
      </p>
    )}
    </div>
  );
}
