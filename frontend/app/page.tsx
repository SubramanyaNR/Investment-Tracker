"use client";

import { useEffect, useState } from "react";
import {
  createAsset,
  deleteAsset,
  getAssets,
  getDashboard,
  getLatestValuations,
  getSnapshots,
  getTransactions,
  recalculateValuations,
  redeemMutualFund,
  sellCrypto,
  topUpSavings,
  type Asset,
  type CryptoMarket,
  type MutualFundScheme,
  type Snapshot,
  type TxRecord,
  type Valuation,
} from "@/lib/api";
import CryptoSelector from "@/components/CryptoSelector";
import MutualFundSelector from "@/components/MutualFundSelector";
import NetWorthChart from "@/components/NetWorthChart";
import AllocationCharts from "@/components/AllocationCharts";

type Dashboard = {
  total_value: number;
  total_invested: number;
  total_pnl: number;
  pnl_percent?: number;
};

const TYPE_CFG: Record<string, { dot: string; badge: string; rowAccent: string }> = {
  CRYPTO:      { dot: "bg-amber-400",   badge: "border-amber-400/30 bg-amber-400/[0.14] text-amber-300",   rowAccent: "rgba(245,158,11,0.04)" },
  MUTUAL_FUND: { dot: "bg-violet-400",  badge: "border-violet-400/30 bg-violet-400/[0.14] text-violet-300", rowAccent: "rgba(167,139,250,0.03)" },
  FD:          { dot: "bg-sky-400",     badge: "border-sky-400/30 bg-sky-400/[0.14] text-sky-300",          rowAccent: "rgba(56,189,248,0.03)" },
  RD:          { dot: "bg-sky-400",     badge: "border-sky-400/30 bg-sky-400/[0.14] text-sky-300",          rowAccent: "rgba(56,189,248,0.03)" },
  PPF:         { dot: "bg-emerald-400", badge: "border-emerald-400/30 bg-emerald-400/[0.14] text-emerald-300", rowAccent: "rgba(52,211,153,0.03)" },
  SAVINGS_ACC: { dot: "bg-emerald-400", badge: "border-emerald-400/30 bg-emerald-400/[0.14] text-emerald-300", rowAccent: "rgba(52,211,153,0.03)" },
};

const TX_CFG: Record<string, { color: string; bg: string; border: string }> = {
  BUY:     { color: "#34d399", bg: "rgba(52,211,153,0.12)",  border: "rgba(52,211,153,0.3)" },
  SELL:    { color: "#f87171", bg: "rgba(248,113,113,0.12)", border: "rgba(248,113,113,0.3)" },
  DEPOSIT: { color: "#818cf8", bg: "rgba(129,140,248,0.12)", border: "rgba(129,140,248,0.3)" },
};

function inr(n: number) {
  return "₹" + Math.abs(n).toLocaleString("en-IN");
}

function fmtQty(n: number) {
  return parseFloat(n.toFixed(8)).toString();
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard>({ total_value: 0, total_invested: 0, total_pnl: 0 });
  const [assets, setAssets] = useState<Asset[]>([]);
  const [valuations, setValuations] = useState<Record<string, Valuation>>({});
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [transactions, setTransactions] = useState<TxRecord[]>([]);

  // Form — shared
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState("MUTUAL_FUND");
  // Crypto
  const [selectedCrypto, setSelectedCrypto] = useState<CryptoMarket | null>(null);
  const [quantity, setQuantity] = useState("");
  const [avgBuyPrice, setAvgBuyPrice] = useState("");
  const [boughtAtCurrentPrice, setBoughtAtCurrentPrice] = useState(false);
  // Fixed income
  const [principal, setPrincipal] = useState("");
  const [annualRate, setAnnualRate] = useState("");
  const [startDate, setStartDate] = useState("");
  const [maturityDate, setMaturityDate] = useState("");
  const [compFrequency, setCompFrequency] = useState("YEARLY");
  // Mutual fund
  const [selectedFund, setSelectedFund] = useState<MutualFundScheme | null>(null);
  const [mfAmount, setMfAmount] = useState("");
  const [mfNav, setMfNav] = useState("");
  const [mfSip, setMfSip] = useState("");

  const [rdTotalInvested, setRdTotalInvested] = useState("");

  const [sellQuantities, setSellQuantities] = useState<Record<string, string>>({});
  const [redeemUnits, setRedeemUnits] = useState<Record<string, string>>({});
  const [depositAmounts, setDepositAmounts] = useState<Record<string, string>>({});
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
    const [d, a, v, s, tx] = await Promise.all([
      getDashboard(),
      getAssets(),
      getLatestValuations(),
      getSnapshots(),
      getTransactions(),
    ]);
    setDashboard(d as Dashboard);
    setAssets(a);
    const vMap: Record<string, Valuation> = {};
    v.forEach((val) => { vMap[val.asset_id] = val; });
    setValuations(vMap);
    setSnapshots(s);
    setTransactions(tx);
  }

  useEffect(() => {
    loadData().catch(() => setError("Failed to load dashboard data."));
  }, []);

  function resetForm() {
    setName(""); setQuantity(""); setAvgBuyPrice(""); setSelectedCrypto(null);
    setBoughtAtCurrentPrice(false); setPrincipal(""); setAnnualRate("");
    setStartDate(""); setMaturityDate(""); setCompFrequency("YEARLY");
    setSelectedFund(null); setMfAmount(""); setMfNav(""); setMfSip("");
    setRdTotalInvested("");
  }

  function handleRdTotalInvested(total: string) {
    setRdTotalInvested(total);
    const monthly = Number(principal);
    const totalNum = Number(total);
    if (monthly > 0 && totalNum > 0) {
      const months = Math.floor(totalNum / monthly);
      if (months > 0) {
        const d = new Date();
        d.setMonth(d.getMonth() - (months - 1));
        setStartDate(d.toISOString().slice(0, 10));
      }
    }
  }

  async function addAsset() {
    if (!name.trim()) { setError("Enter an asset name."); return; }

    const FI = ["FD", "RD", "PPF", "SAVINGS_ACC"];
    if (assetType === "CRYPTO" && (!selectedCrypto || !quantity || !avgBuyPrice)) {
      setError("Select a coin, enter quantity and buy price."); return;
    }
    if (FI.includes(assetType) && (!principal || !annualRate || !startDate)) {
      setError(`${assetType} requires balance/principal, interest rate, and start date.`); return;
    }
    if (assetType === "MUTUAL_FUND" && (!selectedFund || !mfAmount || !mfNav)) {
      setError("Select a fund, enter total amount invested and NAV."); return;
    }

    try {
      setLoading(true); setError("");
      await createAsset({
        name,
        asset_type: assetType,
        category: assetType === "CRYPTO" ? "crypto" : assetType === "SAVINGS_ACC" ? "savings" : FI.includes(assetType) ? "debt" : "equity",
        liquidity_tier: ["FD", "PPF"].includes(assetType) ? "LOCKED" : "LIQUID",
        ...(assetType === "CRYPTO" && selectedCrypto ? {
          coingecko_id: selectedCrypto.id,
          symbol: selectedCrypto.symbol,
          quantity: Number(quantity),
          avg_buy_price: Number(avgBuyPrice),
        } : {}),
        ...(FI.includes(assetType) ? {
          principal: Number(principal),
          annual_rate: Number(annualRate),
          start_date: startDate,
          maturity_date: maturityDate || undefined,
          compounding_frequency: compFrequency,
        } : {}),
        ...(assetType === "MUTUAL_FUND" && selectedFund ? {
          scheme_code: selectedFund.scheme_code,
          amount_invested: Number(mfAmount),
          nav_at_purchase: Number(mfNav),
          monthly_sip: mfSip ? Number(mfSip) : undefined,
        } : {}),
      });
      resetForm();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add asset.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshValuations() {
    try {
      setRefreshing(true); setError("");
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

  async function redeemExistingMF(assetId: string) {
    const units = Number(redeemUnits[assetId]);
    if (!units || units <= 0) { setError("Enter valid units to redeem."); return; }
    try {
      setError("");
      await redeemMutualFund(assetId, units);
      setRedeemUnits((c) => ({ ...c, [assetId]: "" }));
      await recalculateValuations();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to redeem units.");
    }
  }

  async function topUpExistingSavings(assetId: string) {
    const amount = Number(depositAmounts[assetId]);
    if (!amount || amount <= 0) { setError("Enter a valid top-up amount."); return; }
    try {
      setError("");
      await topUpSavings(assetId, amount);
      setDepositAmounts((c) => ({ ...c, [assetId]: "" }));
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to top up savings.");
    }
  }

  const pnlPositive = dashboard.total_pnl >= 0;
  const pnlPct =
    dashboard.pnl_percent ??
    (dashboard.total_invested > 0 ? (dashboard.total_pnl / dashboard.total_invested) * 100 : 0);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-base)" }}>
      {/* Background ambience */}
      <div className="pointer-events-none fixed inset-0 z-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.032) 1px, transparent 1px)", backgroundSize: "28px 28px" }} />
      <div className="pointer-events-none fixed inset-0 z-0" style={{ background: "radial-gradient(ellipse 80% 40% at 20% 0%, rgba(245,158,11,0.07) 0%, transparent 60%)" }} />
      <div className="pointer-events-none fixed inset-0 z-0" style={{ background: "radial-gradient(ellipse 60% 50% at 80% 100%, rgba(167,139,250,0.06) 0%, transparent 60%)" }} />
      <div className="pointer-events-none fixed inset-x-0 top-0 z-0 h-px" style={{ background: "linear-gradient(90deg, transparent 0%, rgba(245,158,11,0.5) 50%, transparent 100%)" }} />

      <div className="relative z-10 mx-auto max-w-screen-xl px-6 py-5 space-y-6">

        {/* Header */}
        <header className="flex flex-col gap-4 pb-5 sm:flex-row sm:items-center sm:justify-between" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl" style={{ background: "linear-gradient(135deg, rgba(245,158,11,0.22) 0%, rgba(251,191,36,0.12) 100%)", border: "1px solid rgba(245,158,11,0.35)", boxShadow: "0 0 24px rgba(245,158,11,0.14)" }}>
              <svg className="h-4 w-4 text-amber-400" viewBox="0 0 16 16" fill="none">
                <polyline points="1,13 5,8 9,10.5 15,3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="15" cy="3" r="1.5" fill="currentColor"/>
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight text-slate-100">Investment Tracker</h1>
                <span className="flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider" style={{ background: "rgba(52,211,153,0.12)", border: "1px solid rgba(52,211,153,0.3)", color: "#34d399" }}>
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />Live
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-500">Portfolio Command Center</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {lastRefreshed && <p className="hidden text-[11px] text-slate-600 sm:block">Updated {lastRefreshed.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</p>}
            <button type="button" onClick={refreshValuations} disabled={refreshing}
              className="flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-medium transition-all hover:bg-amber-400/[0.09] disabled:opacity-50"
              style={{ border: "1px solid rgba(245,158,11,0.35)", color: "#f59e0b", background: "rgba(245,158,11,0.06)" }}>
              <svg className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} viewBox="0 0 16 16" fill="none">
                <path d="M14 8A6 6 0 1 1 8 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M13.5 2v3.5H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {refreshing ? "Refreshing…" : "Refresh Prices"}
            </button>
          </div>
        </header>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-3 rounded-lg px-4 py-3 text-sm" style={{ background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.3)" }}>
            <svg className="h-3.5 w-3.5 shrink-0 text-red-400" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3"/><path d="M8 5v3.5M8 10.8h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
            <span className="text-red-300">{error}</span>
            <button onClick={() => setError("")} className="ml-auto text-base leading-none text-red-500 hover:text-red-300">×</button>
          </div>
        )}

        {/* KPI Strip */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <KpiCard label="Net Worth" value={inr(dashboard.total_value)} sub="Total portfolio value" accent="amber"/>
          <KpiCard label="Total Invested" value={inr(dashboard.total_invested)} sub={`${assets.length} position${assets.length !== 1 ? "s" : ""} tracked`} accent="violet"/>
          <KpiCard label="Profit / Loss" value={(pnlPositive ? "+" : "−") + inr(dashboard.total_pnl)} sub={`${pnlPositive ? "+" : "−"}${Math.abs(pnlPct).toFixed(2)}% overall return`} accent={pnlPositive ? "emerald" : "red"}/>
        </section>

        {/* Allocation Charts */}
        <AllocationCharts assets={assets} valuations={valuations} />

        {/* Net Worth Chart */}
        {snapshots.length > 0 && <NetWorthChart snapshots={snapshots} />}

        {/* Holdings + Add Position */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_360px]">

          {/* Holdings Table */}
          <section className="overflow-hidden rounded-xl" style={{ background: "linear-gradient(160deg, rgba(245,158,11,0.04) 0%, var(--bg-surface) 25%)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 1px 40px rgba(0,0,0,0.4)" }}>
            <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", background: "rgba(255,255,255,0.02)" }}>
              <div>
                <h2 className="text-sm font-semibold text-slate-100">Holdings</h2>
                <p className="mt-0.5 text-[11px] text-slate-500">Active positions · click Refresh to update values</p>
              </div>
              <span className="rounded-full px-2.5 py-1 text-[10px] font-semibold" style={{ background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)", color: "#f59e0b" }}>
                {assets.length} {assets.length === 1 ? "position" : "positions"}
              </span>
            </div>

            {assets.length > 0 && (
              <div className="grid min-w-[640px] px-5 py-2.5 text-[9px] font-bold uppercase tracking-[0.13em] text-slate-600"
                style={{ gridTemplateColumns: "minmax(0,1fr) 100px 110px 110px 110px minmax(130px,160px)", borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.015)" }}>
                <span>Asset</span><span>Type</span><span>Invested</span><span>Current</span><span>P&amp;L</span><span>Actions</span>
              </div>
            )}

            {assets.length === 0 ? (
              <div className="flex flex-col items-center justify-center px-5 py-16 text-center">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)" }}>
                  <svg className="h-5 w-5 text-slate-600" viewBox="0 0 20 20" fill="none"><rect x="3" y="7" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.5"/><path d="M7 7V5a3 3 0 0 1 6 0v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
                </div>
                <p className="text-sm font-medium text-slate-400">No positions yet</p>
                <p className="mt-1 text-[11px] text-slate-600">Use the form to record your first holding →</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                {assets.map((asset, idx) => {
                  const cfg = TYPE_CFG[asset.asset_type] ?? TYPE_CFG.MUTUAL_FUND;
                  const val = valuations[asset.id];
                  const pnlPos = val ? val.pnl >= 0 : true;

                  return (
                    <div key={asset.id}
                      className="group grid min-w-[640px] items-center px-5 transition-colors"
                      style={{
                        gridTemplateColumns: "minmax(0,1fr) 100px 110px 110px 110px minmax(130px,160px)",
                        paddingTop: "12px",
                        paddingBottom: "12px",
                        borderBottom: idx < assets.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none",
                        background: `linear-gradient(90deg, ${cfg.rowAccent} 0%, transparent 40%)`,
                      }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.03)"; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = `linear-gradient(90deg, ${cfg.rowAccent} 0%, transparent 40%)`; }}>

                      {/* Asset name + sub-line */}
                      <div className="flex min-w-0 items-center gap-2.5">
                        <span className={`h-2 w-2 shrink-0 rounded-full ${cfg.dot}`} style={{ boxShadow: `0 0 6px currentColor` }} />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-100">{asset.name}</p>
                          {asset.holding && (
                            <p className="mt-0.5 text-[10px] text-slate-500">
                              <span className="font-semibold text-amber-400">{fmtQty(asset.holding.quantity)} {asset.holding.symbol.toUpperCase()}</span>
                              <span className="mx-1.5 text-slate-700">·</span>
                              <span>Avg {inr(asset.holding.avg_buy_price)}</span>
                              <span className="mx-1.5 text-slate-700">·</span>
                              <span className={asset.liquidity_tier === "LIQUID" ? "text-emerald-400" : "text-orange-400"}>{asset.liquidity_tier === "LIQUID" ? "Liquid" : "Locked"}</span>
                            </p>
                          )}
                          {asset.fi_holding && (
                            <p className="mt-0.5 text-[10px] text-slate-500">
                              <span className={`font-semibold ${asset.asset_type === "SAVINGS_ACC" ? "text-emerald-400" : "text-sky-400"}`}>
                                {asset.asset_type === "RD" ? `${inr(asset.fi_holding.principal)}/mo` : inr(asset.fi_holding.principal)}
                              </span>
                              <span className="mx-1.5 text-slate-700">·</span>
                              <span>{asset.fi_holding.annual_rate}% p.a. {asset.fi_holding.compounding_frequency.toLowerCase()}</span>
                              <span className="mx-1.5 text-slate-700">·</span>
                              <span className={asset.asset_type === "SAVINGS_ACC" ? "text-emerald-400" : "text-orange-400"}>
                                {asset.asset_type === "SAVINGS_ACC" ? "Liquid" : "Locked"}
                              </span>
                            </p>
                          )}
                          {asset.mf_holding && (
                            <p className="mt-0.5 text-[10px] text-slate-500">
                              <span className="font-semibold text-violet-400">{inr(asset.mf_holding.amount_invested)}</span>
                              <span className="mx-1.5 text-slate-700">·</span>
                              <span>{fmtQty(asset.mf_holding.units)} units @ ₹{asset.mf_holding.nav_at_purchase.toFixed(2)}</span>
                              {asset.mf_holding.monthly_sip && (
                                <>
                                  <span className="mx-1.5 text-slate-700">·</span>
                                  <span className="text-violet-400">SIP {inr(asset.mf_holding.monthly_sip)}/mo</span>
                                </>
                              )}
                            </p>
                          )}
                          {!asset.holding && !asset.fi_holding && !asset.mf_holding && (
                            <p className="text-[10px] text-slate-600 capitalize">{asset.category} · {asset.liquidity_tier === "LIQUID" ? <span className="text-emerald-400">Liquid</span> : <span className="text-orange-400">Locked</span>}</p>
                          )}
                        </div>
                      </div>

                      {/* Type */}
                      <div>
                        <span className={`inline-block rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${cfg.badge}`}>{asset.asset_type.replace("_", " ")}</span>
                      </div>

                      {/* Invested */}
                      <span className="text-xs text-slate-400">{val ? inr(val.invested_amount) : <span className="text-slate-700">—</span>}</span>

                      {/* Current */}
                      <span className="text-xs font-medium text-slate-100">{val ? inr(val.current_value) : <span className="text-slate-700">—</span>}</span>

                      {/* P&L */}
                      {val ? (
                        <div>
                          <p className={`text-xs font-semibold ${pnlPos ? "text-emerald-400" : "text-red-400"}`}>
                            {pnlPos ? "+" : "−"}{inr(val.pnl)}
                          </p>
                          {val.invested_amount > 0 && (
                            <p className={`text-[9px] ${pnlPos ? "text-emerald-600" : "text-red-600"}`}>
                              {pnlPos ? "+" : "−"}{Math.abs((val.pnl / val.invested_amount) * 100).toFixed(2)}%
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-700 text-xs">—</span>
                      )}

                      {/* Actions */}
                      <div className="flex items-center gap-1.5">
                        {asset.asset_type === "CRYPTO" && (
                          <>
                            <input
                              value={sellQuantities[asset.id] ?? ""}
                              onChange={(e) => setSellQuantities((c) => ({ ...c, [asset.id]: e.target.value }))}
                              placeholder="qty"
                              inputMode="decimal"
                              className="w-14 rounded-md px-2 py-1 text-[11px] text-slate-300 outline-none"
                              style={{ background: "rgba(255,255,255,0.055)", border: "1px solid rgba(255,255,255,0.11)" }}
                            />
                            <button type="button" onClick={() => sellExistingCrypto(asset.id)}
                              className="rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors hover:bg-amber-400/25"
                              style={{ background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.28)", color: "#fbbf24" }}>
                              Sell
                            </button>
                          </>
                        )}
                        {asset.asset_type === "MUTUAL_FUND" && (
                          <>
                            <input
                              value={redeemUnits[asset.id] ?? ""}
                              onChange={(e) => setRedeemUnits((c) => ({ ...c, [asset.id]: e.target.value }))}
                              placeholder="units"
                              inputMode="decimal"
                              className="w-16 rounded-md px-2 py-1 text-[11px] text-slate-300 outline-none"
                              style={{ background: "rgba(255,255,255,0.055)", border: "1px solid rgba(255,255,255,0.11)" }}
                            />
                            <button type="button" onClick={() => redeemExistingMF(asset.id)}
                              className="rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors hover:bg-violet-400/25"
                              style={{ background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.28)", color: "#c4b5fd" }}>
                              Redeem
                            </button>
                          </>
                        )}
                        {(asset.asset_type === "SAVINGS_ACC" || asset.asset_type === "PPF") && (
                          <>
                            <input
                              value={depositAmounts[asset.id] ?? ""}
                              onChange={(e) => setDepositAmounts((c) => ({ ...c, [asset.id]: e.target.value }))}
                              placeholder="₹ add"
                              inputMode="decimal"
                              className="w-16 rounded-md px-2 py-1 text-[11px] text-slate-300 outline-none"
                              style={{ background: "rgba(255,255,255,0.055)", border: "1px solid rgba(255,255,255,0.11)" }}
                            />
                            <button type="button" onClick={() => topUpExistingSavings(asset.id)}
                              className="rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors hover:bg-emerald-400/25"
                              style={{ background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.28)", color: "#6ee7b7" }}>
                              {asset.asset_type === "PPF" ? "Deposit" : "Top Up"}
                            </button>
                          </>
                        )}
                        <button type="button" onClick={() => removeAsset(asset.id)}
                          className="rounded-md px-2.5 py-1 text-[11px] font-medium opacity-0 transition-all group-hover:opacity-100 hover:bg-red-400/25"
                          style={{ background: "rgba(248,113,113,0.09)", border: "1px solid rgba(248,113,113,0.22)", color: "#f87171" }}>
                          Remove
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Add Position */}
          <section className="rounded-xl p-5" style={{ background: "linear-gradient(160deg, rgba(245,158,11,0.08) 0%, var(--bg-surface) 35%)", border: "1px solid rgba(245,158,11,0.2)", boxShadow: "0 1px 40px rgba(0,0,0,0.4)" }}>
            <div className="pb-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
              <h2 className="text-sm font-semibold text-slate-100">Add Position</h2>
              <p className="mt-0.5 text-[11px] text-slate-500">Record a new holding in your portfolio</p>
            </div>

            <div className="mt-4 space-y-3.5">
              <Field label="Asset Name">
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Bitcoin, PPFAS Flexi Cap, SBI FD…" className="field-input"/>
              </Field>

              <Field label="Asset Type">
                <select value={assetType} onChange={(e) => { setAssetType(e.target.value); if (e.target.value === "SAVINGS_ACC") setCompFrequency("QUARTERLY"); }} className="field-input appearance-none">
                  <option value="MUTUAL_FUND">Mutual Fund</option>
                  <option value="CRYPTO">Crypto</option>
                  <option value="FD">Fixed Deposit (FD)</option>
                  <option value="RD">Recurring Deposit (RD)</option>
                  <option value="PPF">PPF</option>
                  <option value="SAVINGS_ACC">Savings Account</option>
                </select>
              </Field>

              {assetType === "CRYPTO" && (
                <>
                  <Field label="Coin"><CryptoSelector selected={selectedCrypto} onSelect={handleCryptoSelect}/></Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Quantity"><input value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="0.05" inputMode="decimal" className="field-input"/></Field>
                    <Field label="Avg Buy Price (₹)"><input value={avgBuyPrice} onChange={(e) => setAvgBuyPrice(e.target.value)} placeholder="9200000" inputMode="decimal" disabled={boughtAtCurrentPrice} className="field-input"/></Field>
                  </div>
                  <label className="flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2.5" style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.18)" }}>
                    <input type="checkbox" checked={boughtAtCurrentPrice} onChange={(e) => handleBoughtAtCurrentPrice(e.target.checked)} className="h-3.5 w-3.5 accent-amber-400"/>
                    <span className="text-xs text-slate-400">Bought at current market price</span>
                    {selectedCrypto && boughtAtCurrentPrice && <span className="ml-auto text-xs font-semibold text-amber-400">₹{selectedCrypto.current_price.toLocaleString("en-IN")}</span>}
                  </label>
                </>
              )}

              {assetType === "MUTUAL_FUND" && (
                <>
                  <Field label="Fund">
                    <MutualFundSelector selected={selectedFund} onSelect={setSelectedFund} />
                  </Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Total Amount Invested (₹)">
                      <input value={mfAmount} onChange={(e) => setMfAmount(e.target.value)} placeholder="50000" inputMode="decimal" className="field-input"/>
                    </Field>
                    <Field label="NAV at Purchase (₹)">
                      <input value={mfNav} onChange={(e) => setMfNav(e.target.value)} placeholder="45.23" inputMode="decimal" className="field-input"/>
                    </Field>
                  </div>
                  {mfAmount && mfNav && Number(mfNav) > 0 && (
                    <p className="text-[10px] text-slate-500">
                      Units: <span className="font-semibold text-violet-400">{(Number(mfAmount) / Number(mfNav)).toFixed(4)}</span>
                    </p>
                  )}
                  <Field label="Monthly SIP Amount (₹) — optional">
                    <input value={mfSip} onChange={(e) => setMfSip(e.target.value)} placeholder="5000 — auto-added every month" inputMode="decimal" className="field-input"/>
                  </Field>
                  {selectedFund && (
                    <div className="rounded-lg px-3 py-2" style={{ background: "rgba(167,139,250,0.07)", border: "1px solid rgba(167,139,250,0.18)" }}>
                      <p className="text-[10px] text-violet-300/80 truncate">{selectedFund.name}</p>
                      <p className="mt-0.5 text-[9px] text-slate-600">Scheme Code: {selectedFund.scheme_code}</p>
                    </div>
                  )}
                </>
              )}

              {["FD","RD","PPF","SAVINGS_ACC"].includes(assetType) && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label={assetType === "RD" ? "Monthly Deposit (₹)" : assetType === "SAVINGS_ACC" ? "Current Balance (₹)" : "Principal (₹)"}>
                      <input value={principal} onChange={(e) => setPrincipal(e.target.value)}
                        placeholder={assetType === "RD" ? "5000" : assetType === "SAVINGS_ACC" ? "50000" : "100000"}
                        inputMode="decimal" className="field-input"/>
                    </Field>
                    <Field label="Annual Rate (%)"><input value={annualRate} onChange={(e) => setAnnualRate(e.target.value)} placeholder={assetType === "SAVINGS_ACC" ? "3.5" : "7.5"} inputMode="decimal" className="field-input"/></Field>
                  </div>
                  {assetType === "RD" && (
                    <Field label="Amount already invested (₹) — optional">
                      <input value={rdTotalInvested} onChange={(e) => handleRdTotalInvested(e.target.value)}
                        placeholder="e.g. 60000 — auto-fills start date"
                        inputMode="decimal" className="field-input"/>
                      {rdTotalInvested && principal && Number(principal) > 0 && (
                        <p className="mt-1 text-[10px] text-slate-500">
                          ≈ <span className="text-sky-400 font-semibold">{Math.floor(Number(rdTotalInvested)/Number(principal))} months</span> — start date auto-filled below
                        </p>
                      )}
                    </Field>
                  )}
                  <div className={assetType === "SAVINGS_ACC" ? "" : "grid grid-cols-2 gap-3"}>
                    <Field label={assetType === "SAVINGS_ACC" ? "Date Opened" : "Start Date"}>
                      <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="field-input"/>
                    </Field>
                    {assetType !== "SAVINGS_ACC" && (
                      <Field label="Maturity Date (opt)"><input type="date" value={maturityDate} onChange={(e) => setMaturityDate(e.target.value)} className="field-input"/></Field>
                    )}
                  </div>
                  <Field label="Compounding">
                    <select value={compFrequency} onChange={(e) => setCompFrequency(e.target.value)} className="field-input appearance-none">
                      <option value="MONTHLY">Monthly</option>
                      <option value="QUARTERLY">Quarterly</option>
                      <option value="YEARLY">Yearly</option>
                    </select>
                  </Field>
                  {assetType === "SAVINGS_ACC" && (
                    <div className="rounded-lg px-3 py-2" style={{ background: "rgba(52,211,153,0.07)", border: "1px solid rgba(52,211,153,0.18)" }}>
                      <p className="text-[10px] text-emerald-300/80">Savings account — always liquid. Use Top Up to add deposits later.</p>
                    </div>
                  )}
                </>
              )}
            </div>

            <button type="button" onClick={addAsset} disabled={loading}
              className="mt-5 w-full rounded-lg py-2.5 text-sm font-semibold tracking-wide transition-all disabled:opacity-50 hover:brightness-110"
              style={{ background: "linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)", color: "#1c1000", boxShadow: "0 0 28px rgba(245,158,11,0.28), 0 2px 8px rgba(0,0,0,0.4)" }}>
              {loading ? "Adding…" : "Add Position"}
            </button>
          </section>
        </div>

        {/* Transaction History */}
        {transactions.length > 0 && (
          <section className="overflow-hidden rounded-xl" style={{ background: "linear-gradient(160deg, rgba(129,140,248,0.05) 0%, var(--bg-surface) 30%)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 1px 40px rgba(0,0,0,0.4)" }}>
            <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", background: "rgba(255,255,255,0.02)" }}>
              <div>
                <h2 className="text-sm font-semibold text-slate-100">Transaction History</h2>
                <p className="mt-0.5 text-[11px] text-slate-500">All recorded portfolio activity</p>
              </div>
              <span className="rounded-full px-2.5 py-1 text-[10px] font-semibold" style={{ background: "rgba(129,140,248,0.12)", border: "1px solid rgba(129,140,248,0.3)", color: "#818cf8" }}>
                {transactions.length} records
              </span>
            </div>

            <div className="overflow-x-auto">
              <div className="grid min-w-[560px] px-5 py-2.5 text-[9px] font-bold uppercase tracking-[0.13em] text-slate-600"
                style={{ gridTemplateColumns: "100px 1fr 70px 90px 110px 110px", borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.015)" }}>
                <span>Date</span><span>Asset</span><span>Type</span><span>Units</span><span>Price/Unit</span><span>Amount</span>
              </div>

              {transactions.slice(0, 50).map((tx, idx) => {
                const tCfg = TX_CFG[tx.transaction_type] ?? TX_CFG.BUY;
                const assetCfg = TYPE_CFG[tx.asset_type] ?? TYPE_CFG.MUTUAL_FUND;
                return (
                  <div key={tx.id}
                    className="grid min-w-[560px] items-center px-5 py-2.5 text-xs transition-colors hover:bg-white/[0.025]"
                    style={{ gridTemplateColumns: "100px 1fr 70px 90px 110px 110px", borderBottom: idx < Math.min(transactions.length, 50) - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
                    <span className="font-mono text-[10px] text-slate-500">{tx.transaction_date}</span>
                    <div className="flex min-w-0 items-center gap-2">
                      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${assetCfg.dot}`}/>
                      <span className="truncate text-slate-300">{tx.asset_name}</span>
                    </div>
                    <span>
                      <span className="rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase" style={{ background: tCfg.bg, borderColor: tCfg.border, color: tCfg.color }}>{tx.transaction_type}</span>
                    </span>
                    <span className="font-mono text-[11px] text-slate-400">{tx.units != null ? fmtQty(tx.units) : "—"}</span>
                    <span className="font-mono text-[11px] text-slate-400">{tx.price_per_unit != null ? inr(tx.price_per_unit) : "—"}</span>
                    <span className="font-mono text-[11px] text-slate-100">{tx.amount > 0 ? inr(tx.amount) : "—"}</span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-600">{label}</p>
      {children}
    </div>
  );
}

const ACCENT = {
  amber: {
    bg: "linear-gradient(135deg, rgba(245,158,11,0.22) 0%, rgba(245,158,11,0.08) 45%, var(--bg-surface) 100%)",
    border: "rgba(245,158,11,0.35)",
    bar: "linear-gradient(90deg, #f59e0b 0%, rgba(245,158,11,0.4) 60%, transparent 100%)",
    glow: "0 0 50px rgba(245,158,11,0.12), 0 1px 40px rgba(0,0,0,0.5)",
    label: "#fbbf24",
  },
  violet: {
    bg: "linear-gradient(135deg, rgba(167,139,250,0.2) 0%, rgba(167,139,250,0.07) 45%, var(--bg-surface) 100%)",
    border: "rgba(167,139,250,0.3)",
    bar: "linear-gradient(90deg, #a78bfa 0%, rgba(167,139,250,0.4) 60%, transparent 100%)",
    glow: "0 0 50px rgba(167,139,250,0.1), 0 1px 40px rgba(0,0,0,0.5)",
    label: "#c4b5fd",
  },
  emerald: {
    bg: "linear-gradient(135deg, rgba(52,211,153,0.18) 0%, rgba(52,211,153,0.06) 45%, var(--bg-surface) 100%)",
    border: "rgba(52,211,153,0.28)",
    bar: "linear-gradient(90deg, #34d399 0%, rgba(52,211,153,0.4) 60%, transparent 100%)",
    glow: "0 0 50px rgba(52,211,153,0.1), 0 1px 40px rgba(0,0,0,0.5)",
    label: "#6ee7b7",
  },
  red: {
    bg: "linear-gradient(135deg, rgba(248,113,113,0.18) 0%, rgba(248,113,113,0.06) 45%, var(--bg-surface) 100%)",
    border: "rgba(248,113,113,0.28)",
    bar: "linear-gradient(90deg, #f87171 0%, rgba(248,113,113,0.4) 60%, transparent 100%)",
    glow: "0 0 50px rgba(248,113,113,0.1), 0 1px 40px rgba(0,0,0,0.5)",
    label: "#fca5a5",
  },
};

function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub: string; accent: keyof typeof ACCENT }) {
  const a = ACCENT[accent];
  return (
    <div className="relative overflow-hidden rounded-xl p-5" style={{ background: a.bg, border: `1px solid ${a.border}`, boxShadow: a.glow }}>
      <div className="absolute inset-x-0 top-0 h-[2px]" style={{ background: a.bar }} />
      <p className="text-[9px] font-bold uppercase tracking-[0.18em]" style={{ color: a.label }}>{label}</p>
      <p className="mt-3 text-[28px] font-bold leading-none tracking-tight text-white">{value}</p>
      <p className="mt-2 text-[11px] text-slate-500">{sub}</p>
    </div>
  );
}
