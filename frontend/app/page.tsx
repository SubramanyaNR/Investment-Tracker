"use client";

import { useEffect, useState } from "react";
import {
  createAsset,
  deleteAsset,
  getAssets,
  getDashboard,
  recalculateValuations,
  sellCrypto,
  type Asset,
  type CryptoMarket,
} from "@/lib/api";
import CryptoSelector from "@/components/CryptoSelector";

type Dashboard = {
  total_value: number;
  total_invested: number;
  total_pnl: number;
  pnl_percent?: number;
};

const TYPE_CFG: Record<string, { dot: string; badge: string }> = {
  CRYPTO:      { dot: "bg-cyan-400",    badge: "border-cyan-400/20 bg-cyan-400/[0.08] text-cyan-300" },
  MUTUAL_FUND: { dot: "bg-violet-400",  badge: "border-violet-400/20 bg-violet-400/[0.08] text-violet-300" },
  FD:          { dot: "bg-amber-400",   badge: "border-amber-400/20 bg-amber-400/[0.08] text-amber-300" },
  RD:          { dot: "bg-amber-400",   badge: "border-amber-400/20 bg-amber-400/[0.08] text-amber-300" },
  PPF:         { dot: "bg-emerald-400", badge: "border-emerald-400/20 bg-emerald-400/[0.08] text-emerald-300" },
};

function inr(n: number) {
  return "₹" + Math.abs(n).toLocaleString("en-IN");
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard>({
    total_value: 0,
    total_invested: 0,
    total_pnl: 0,
  });
  const [assets, setAssets] = useState<Asset[]>([]);
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState("MUTUAL_FUND");
  const [selectedCrypto, setSelectedCrypto] = useState<CryptoMarket | null>(null);
  const [quantity, setQuantity] = useState("");
  const [avgBuyPrice, setAvgBuyPrice] = useState("");
  const [boughtAtCurrentPrice, setBoughtAtCurrentPrice] = useState(false);
  const [sellQuantities, setSellQuantities] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  function handleCryptoSelect(coin: CryptoMarket) {
    setSelectedCrypto(coin);
    if (boughtAtCurrentPrice) setAvgBuyPrice(String(coin.current_price));
  }

  function handleBoughtAtCurrentPrice(checked: boolean) {
    setBoughtAtCurrentPrice(checked);
    if (checked && selectedCrypto) setAvgBuyPrice(String(selectedCrypto.current_price));
  }

  async function loadData() {
    const [d, a] = await Promise.all([getDashboard(), getAssets()]);
    setDashboard(d);
    setAssets(a);
  }

  useEffect(() => {
    loadData().catch(() => setError("Failed to load dashboard data."));
  }, []);

  async function addAsset() {
    if (!name.trim()) { setError("Enter an asset name."); return; }
    if (assetType === "CRYPTO" && (!selectedCrypto || !quantity || !avgBuyPrice)) {
      setError("Select a coin, enter quantity and buy price.");
      return;
    }
    try {
      setLoading(true);
      setError("");
      await createAsset({
        name,
        asset_type: assetType,
        category: assetType === "CRYPTO" ? "crypto" : ["FD","RD","PPF"].includes(assetType) ? "debt" : "equity",
        liquidity_tier: ["FD","PPF"].includes(assetType) ? "LOCKED" : "LIQUID",
        ...(assetType === "CRYPTO" && selectedCrypto ? {
          coingecko_id: selectedCrypto.id,
          symbol: selectedCrypto.symbol,
          quantity: Number(quantity),
          avg_buy_price: Number(avgBuyPrice),
        } : {}),
      });
      setName(""); setQuantity(""); setAvgBuyPrice("");
      setSelectedCrypto(null); setBoughtAtCurrentPrice(false);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add asset.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshValuations() {
    try {
      setRefreshing(true);
      setError("");
      await recalculateValuations();
      await loadData();
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh prices.");
    } finally {
      setRefreshing(false);
    }
  }

  async function removeAsset(assetId: string) {
    if (!confirm("Delete this asset? This cannot be undone.")) return;
    try {
      setError("");
      await deleteAsset(assetId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete asset.");
    }
  }

  async function sellExistingCrypto(assetId: string) {
    const qty = Number(sellQuantities[assetId]);
    if (!qty || qty <= 0) { setError("Enter a valid sell quantity."); return; }
    try {
      setError("");
      await sellCrypto(assetId, qty);
      setSellQuantities((c) => ({ ...c, [assetId]: "" }));
      await recalculateValuations();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sell crypto.");
    }
  }

  const pnlPositive = dashboard.total_pnl >= 0;
  const pnlPct =
    dashboard.pnl_percent ??
    (dashboard.total_invested > 0 ? (dashboard.total_pnl / dashboard.total_invested) * 100 : 0);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-base)" }}>
      {/* Dot grid overlay */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          backgroundImage: "radial-gradient(rgba(255,255,255,0.028) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />
      {/* Top edge glow */}
      <div
        className="pointer-events-none fixed inset-x-0 top-0 z-0 h-px"
        style={{ background: "linear-gradient(90deg, transparent 0%, rgba(34,211,238,0.3) 50%, transparent 100%)" }}
      />

      <div className="relative z-10 mx-auto max-w-screen-xl px-6 py-5 space-y-6">

        {/* ── Header ── */}
        <header
          className="flex flex-col gap-4 pb-5 sm:flex-row sm:items-center sm:justify-between"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
        >
          <div className="flex items-center gap-3">
            {/* Brand mark */}
            <div
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
              style={{
                background: "linear-gradient(135deg, rgba(34,211,238,0.15) 0%, rgba(167,139,250,0.1) 100%)",
                border: "1px solid rgba(34,211,238,0.22)",
                boxShadow: "0 0 20px rgba(34,211,238,0.08)",
              }}
            >
              <svg className="h-4 w-4 text-cyan-400" viewBox="0 0 16 16" fill="none">
                <polyline
                  points="1,13 5,8 9,10.5 15,3"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="15" cy="3" r="1.5" fill="currentColor" />
              </svg>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-slate-100 tracking-tight">
                  Investment Tracker
                </h1>
                <span
                  className="flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider"
                  style={{
                    background: "rgba(52,211,153,0.09)",
                    border: "1px solid rgba(52,211,153,0.22)",
                    color: "#34d399",
                  }}
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-600">Portfolio Command Center</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {lastRefreshed && (
              <p className="hidden text-[11px] text-slate-700 sm:block">
                Updated&nbsp;
                {lastRefreshed.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
              </p>
            )}
            <button
              type="button"
              onClick={refreshValuations}
              disabled={refreshing}
              className="flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-medium transition-colors hover:bg-cyan-400/[0.06] disabled:opacity-50"
              style={{ border: "1px solid rgba(34,211,238,0.22)", color: "#22d3ee" }}
            >
              <svg
                className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`}
                viewBox="0 0 16 16"
                fill="none"
              >
                <path
                  d="M14 8A6 6 0 1 1 8 2"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
                <path
                  d="M13.5 2v3.5H10"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              {refreshing ? "Refreshing…" : "Refresh Prices"}
            </button>
          </div>
        </header>

        {/* ── Error Banner ── */}
        {error && (
          <div
            className="flex items-center gap-3 rounded-lg px-4 py-3 text-sm"
            style={{
              background: "rgba(248,113,113,0.07)",
              border: "1px solid rgba(248,113,113,0.2)",
            }}
          >
            <svg className="h-3.5 w-3.5 shrink-0 text-red-400" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3" />
              <path
                d="M8 5v3.5M8 10.8h.01"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            <span className="text-red-300/90">{error}</span>
            <button
              onClick={() => setError("")}
              className="ml-auto text-base leading-none text-red-500 transition-colors hover:text-red-300"
            >
              ×
            </button>
          </div>
        )}

        {/* ── KPI Strip ── */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <KpiCard
            label="Net Worth"
            value={inr(dashboard.total_value)}
            sub="Total portfolio value"
            accent="cyan"
          />
          <KpiCard
            label="Total Invested"
            value={inr(dashboard.total_invested)}
            sub={`${assets.length} position${assets.length !== 1 ? "s" : ""} tracked`}
            accent="violet"
          />
          <KpiCard
            label="Profit / Loss"
            value={(pnlPositive ? "+" : "−") + inr(dashboard.total_pnl)}
            sub={`${pnlPositive ? "+" : "−"}${Math.abs(pnlPct).toFixed(2)}% overall return`}
            accent={pnlPositive ? "emerald" : "red"}
          />
        </section>

        {/* ── Holdings + Add Position ── */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_360px]">

          {/* Holdings */}
          <section
            className="overflow-hidden rounded-xl"
            style={{ background: "var(--bg-surface)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            {/* Section header */}
            <div
              className="flex items-center justify-between px-5 py-4"
              style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
            >
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Holdings</h2>
                <p className="mt-0.5 text-[11px] text-slate-600">
                  Active positions across asset classes
                </p>
              </div>
              <span
                className="rounded-full px-2.5 py-1 text-[10px] font-semibold"
                style={{
                  background: "rgba(34,211,238,0.07)",
                  border: "1px solid rgba(34,211,238,0.15)",
                  color: "#22d3ee",
                }}
              >
                {assets.length} {assets.length === 1 ? "position" : "positions"}
              </span>
            </div>

            {/* Column headers */}
            {assets.length > 0 && (
              <div
                className="grid min-w-[560px] px-5 py-2.5 text-[9px] font-bold uppercase tracking-[0.13em] text-slate-700"
                style={{
                  gridTemplateColumns: "minmax(0,1fr) 110px 72px 88px minmax(160px,200px)",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                }}
              >
                <span>Asset</span>
                <span>Type</span>
                <span>Class</span>
                <span>Liquidity</span>
                <span>Actions</span>
              </div>
            )}

            {/* Empty state */}
            {assets.length === 0 ? (
              <div className="flex flex-col items-center justify-center px-5 py-16 text-center">
                <div
                  className="mb-4 flex h-12 w-12 items-center justify-center rounded-full"
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.07)",
                  }}
                >
                  <svg className="h-5 w-5 text-slate-700" viewBox="0 0 20 20" fill="none">
                    <rect
                      x="3" y="7" width="14" height="10" rx="2"
                      stroke="currentColor" strokeWidth="1.5"
                    />
                    <path
                      d="M7 7V5a3 3 0 0 1 6 0v2"
                      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
                    />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-500">No positions yet</p>
                <p className="mt-1 text-[11px] text-slate-700">
                  Use the form to record your first holding →
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                {assets.map((asset, idx) => {
                  const cfg = TYPE_CFG[asset.asset_type] ?? TYPE_CFG.MUTUAL_FUND;
                  return (
                    <div
                      key={asset.id}
                      className="group grid min-w-[560px] items-center px-5 transition-colors hover:bg-white/[0.017]"
                      style={{
                        gridTemplateColumns: "minmax(0,1fr) 110px 72px 88px minmax(160px,200px)",
                        paddingTop: "11px",
                        paddingBottom: "11px",
                        borderBottom:
                          idx < assets.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                      }}
                    >
                      {/* Name + ID */}
                      <div className="flex min-w-0 items-center gap-2.5">
                        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${cfg.dot}`} />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-200">
                            {asset.name}
                          </p>
                          <p className="font-mono text-[9px] text-slate-700">
                            {asset.id.slice(0, 10)}…
                          </p>
                        </div>
                      </div>

                      {/* Type badge */}
                      <div>
                        <span
                          className={`inline-block rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${cfg.badge}`}
                        >
                          {asset.asset_type.replace("_", " ")}
                        </span>
                      </div>

                      {/* Category */}
                      <span className="text-[11px] capitalize text-slate-600">
                        {asset.category}
                      </span>

                      {/* Liquidity */}
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            asset.liquidity_tier === "LIQUID" ? "bg-emerald-400" : "bg-amber-400"
                          }`}
                        />
                        <span
                          className={`text-[11px] ${
                            asset.liquidity_tier === "LIQUID" ? "text-emerald-400" : "text-amber-400"
                          }`}
                        >
                          {asset.liquidity_tier === "LIQUID" ? "Liquid" : "Locked"}
                        </span>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1.5">
                        {asset.asset_type === "CRYPTO" && (
                          <>
                            <input
                              value={sellQuantities[asset.id] ?? ""}
                              onChange={(e) =>
                                setSellQuantities((c) => ({ ...c, [asset.id]: e.target.value }))
                              }
                              placeholder="qty"
                              inputMode="decimal"
                              className="w-14 rounded-md px-2 py-1 text-[11px] text-slate-300 outline-none transition-colors"
                              style={{
                                background: "rgba(255,255,255,0.04)",
                                border: "1px solid rgba(255,255,255,0.08)",
                              }}
                            />
                            <button
                              type="button"
                              onClick={() => sellExistingCrypto(asset.id)}
                              className="rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors hover:bg-amber-400/20"
                              style={{
                                background: "rgba(251,191,36,0.07)",
                                border: "1px solid rgba(251,191,36,0.18)",
                                color: "#fbbf24",
                              }}
                            >
                              Sell
                            </button>
                          </>
                        )}
                        <button
                          type="button"
                          onClick={() => removeAsset(asset.id)}
                          className="rounded-md px-2.5 py-1 text-[11px] font-medium opacity-0 transition-all group-hover:opacity-100 hover:bg-red-400/20"
                          style={{
                            background: "rgba(248,113,113,0.06)",
                            border: "1px solid rgba(248,113,113,0.14)",
                            color: "#f87171",
                          }}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Add Position Panel */}
          <section
            className="rounded-xl p-5"
            style={{ background: "var(--bg-surface)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <div
              className="pb-4"
              style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
            >
              <h2 className="text-sm font-semibold text-slate-200">Add Position</h2>
              <p className="mt-0.5 text-[11px] text-slate-600">
                Record a new holding in your portfolio
              </p>
            </div>

            <div className="mt-4 space-y-3.5">
              <FormField label="Asset Name">
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Bitcoin, PPFAS Flexi Cap, SBI FD…"
                  className="field-input"
                />
              </FormField>

              <FormField label="Asset Type">
                <select
                  value={assetType}
                  onChange={(e) => setAssetType(e.target.value)}
                  className="field-input appearance-none"
                >
                  <option value="MUTUAL_FUND">Mutual Fund</option>
                  <option value="CRYPTO">Crypto</option>
                  <option value="FD">Fixed Deposit (FD)</option>
                  <option value="RD">Recurring Deposit (RD)</option>
                  <option value="PPF">PPF</option>
                </select>
              </FormField>

              {assetType === "CRYPTO" && (
                <>
                  <FormField label="Coin">
                    <CryptoSelector selected={selectedCrypto} onSelect={handleCryptoSelect} />
                  </FormField>

                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Quantity">
                      <input
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                        placeholder="0.05"
                        inputMode="decimal"
                        className="field-input"
                      />
                    </FormField>
                    <FormField label="Avg Buy Price (₹)">
                      <input
                        value={avgBuyPrice}
                        onChange={(e) => setAvgBuyPrice(e.target.value)}
                        placeholder="9200000"
                        inputMode="decimal"
                        disabled={boughtAtCurrentPrice}
                        className="field-input"
                      />
                    </FormField>
                  </div>

                  <label
                    className="flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2.5 transition-colors hover:bg-white/[0.02]"
                    style={{
                      background: "rgba(255,255,255,0.025)",
                      border: "1px solid rgba(255,255,255,0.06)",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={boughtAtCurrentPrice}
                      onChange={(e) => handleBoughtAtCurrentPrice(e.target.checked)}
                      className="h-3.5 w-3.5 accent-cyan-400"
                    />
                    <span className="text-xs text-slate-500">Bought at current market price</span>
                    {selectedCrypto && boughtAtCurrentPrice && (
                      <span className="ml-auto text-xs font-semibold text-cyan-300">
                        ₹{selectedCrypto.current_price.toLocaleString("en-IN")}
                      </span>
                    )}
                  </label>
                </>
              )}
            </div>

            <button
              type="button"
              onClick={addAsset}
              disabled={loading}
              className="mt-5 w-full rounded-lg py-2.5 text-sm font-semibold tracking-wide transition-opacity disabled:opacity-50"
              style={{
                background: "linear-gradient(135deg, #22d3ee 0%, #67e8f9 100%)",
                color: "#020617",
                boxShadow: "0 0 24px rgba(34,211,238,0.18)",
              }}
            >
              {loading ? "Adding…" : "Add Position"}
            </button>
          </section>

        </div>
      </div>
    </div>
  );
}

// ── FormField ──────────────────────────────────────────────────────────────

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-700">{label}</p>
      {children}
    </div>
  );
}

// ── KpiCard ────────────────────────────────────────────────────────────────

const ACCENT = {
  cyan:    {
    bar: "rgba(34,211,238,0.55)",
    border: "rgba(34,211,238,0.12)",
    glow: "rgba(34,211,238,0.06)",
    label: "#22d3ee",
  },
  violet:  {
    bar: "rgba(167,139,250,0.55)",
    border: "rgba(167,139,250,0.12)",
    glow: "rgba(167,139,250,0.06)",
    label: "#a78bfa",
  },
  emerald: {
    bar: "rgba(52,211,153,0.55)",
    border: "rgba(52,211,153,0.12)",
    glow: "rgba(52,211,153,0.06)",
    label: "#34d399",
  },
  red:     {
    bar: "rgba(248,113,113,0.55)",
    border: "rgba(248,113,113,0.12)",
    glow: "rgba(248,113,113,0.06)",
    label: "#f87171",
  },
};

function KpiCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  accent: keyof typeof ACCENT;
}) {
  const a = ACCENT[accent];
  return (
    <div
      className="relative overflow-hidden rounded-xl p-5"
      style={{
        background: `radial-gradient(ellipse at 100% 0%, ${a.glow} 0%, transparent 60%), var(--bg-surface)`,
        border: `1px solid ${a.border}`,
      }}
    >
      {/* Top accent line */}
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{
          background: `linear-gradient(90deg, ${a.bar} 0%, transparent 70%)`,
        }}
      />

      <p
        className="text-[9px] font-bold uppercase tracking-[0.18em]"
        style={{ color: a.label }}
      >
        {label}
      </p>
      <p className="mt-3 text-[26px] font-bold tracking-tight leading-none text-white">
        {value}
      </p>
      <p className="mt-2 text-[11px] text-slate-600">{sub}</p>
    </div>
  );
}
