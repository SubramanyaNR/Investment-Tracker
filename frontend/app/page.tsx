"use client";

import { useEffect, useState } from "react";
import {
  createAsset, deleteAsset, getAssets, getDashboard, getLatestValuations,
  getSnapshots, getTransactions, getMfCurrentNav, recalculateValuations, redeemMutualFund,
  sellCrypto, topUpSavings,
  type Asset, type CryptoMarket, type MutualFundScheme,
  type Snapshot, type TxRecord, type Valuation,
} from "@/lib/api";
import CryptoSelector    from "@/components/CryptoSelector";
import MutualFundSelector from "@/components/MutualFundSelector";
import NetWorthChart     from "@/components/NetWorthChart";
import AllocationCharts  from "@/components/AllocationCharts";
import ThemeSwitcher     from "@/components/ThemeSwitcher";
import { useAuth }       from "@/components/AuthProvider";

// ── Types ──────────────────────────────────────────────────────────────────

type Dashboard = { total_value: number; total_invested: number; total_pnl: number; pnl_percent?: number };
type Tab = "overview" | "holdings" | "transactions";

// ── Config ─────────────────────────────────────────────────────────────────

const TYPE_CFG: Record<string, { dot: string; badge: string; rowAccent: string }> = {
  CRYPTO:      { dot: "bg-amber-400",   badge: "type-badge type-badge--amber",   rowAccent: "rgba(245,158,11,0.04)"  },
  MUTUAL_FUND: { dot: "bg-violet-400",  badge: "type-badge type-badge--violet",  rowAccent: "rgba(167,139,250,0.03)" },
  FD:          { dot: "bg-sky-400",     badge: "type-badge type-badge--sky",      rowAccent: "rgba(56,189,248,0.03)"  },
  RD:          { dot: "bg-sky-400",     badge: "type-badge type-badge--sky",      rowAccent: "rgba(56,189,248,0.03)"  },
  PPF:         { dot: "bg-emerald-400", badge: "type-badge type-badge--emerald",  rowAccent: "rgba(52,211,153,0.03)"  },
  SAVINGS_ACC: { dot: "bg-emerald-400", badge: "type-badge type-badge--emerald",  rowAccent: "rgba(52,211,153,0.03)"  },
};

const TX_CLASS: Record<string, string> = {
  BUY:     "tx-badge tx-badge--buy",
  SELL:    "tx-badge tx-badge--sell",
  DEPOSIT: "tx-badge tx-badge--deposit",
};

// ── Helpers ────────────────────────────────────────────────────────────────

function inr(n: number) {
  return "₹" + Math.abs(n).toLocaleString("en-IN");
}
function fmtQty(n: number) {
  return parseFloat(n.toFixed(8)).toString();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// PAGE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export default function DashboardPage() {

  const { signOut } = useAuth();

  // ── Data ──
  const [dashboard,    setDashboard]    = useState<Dashboard>({ total_value: 0, total_invested: 0, total_pnl: 0 });
  const [assets,       setAssets]       = useState<Asset[]>([]);
  const [valuations,   setValuations]   = useState<Record<string, Valuation>>({});
  const [snapshots,    setSnapshots]    = useState<Snapshot[]>([]);
  const [transactions, setTransactions] = useState<TxRecord[]>([]);

  // ── UI state ──
  const [tab, setTab] = useState<Tab>("overview");
  const [error,         setError]         = useState("");
  const [loading,       setLoading]       = useState(false);
  const [refreshing,    setRefreshing]    = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // ── Form — shared ──
  const [name,      setName]      = useState("");
  const [assetType, setAssetType] = useState("MUTUAL_FUND");

  // ── Form — Crypto ──
  const [selectedCrypto,       setSelectedCrypto]       = useState<CryptoMarket | null>(null);
  const [quantity,             setQuantity]             = useState("");
  const [avgBuyPrice,          setAvgBuyPrice]          = useState("");
  const [boughtAtCurrentPrice, setBoughtAtCurrentPrice] = useState(false);

  // ── Form — Fixed income ──
  const [principal,    setPrincipal]    = useState("");
  const [annualRate,   setAnnualRate]   = useState("");
  const [startDate,    setStartDate]    = useState("");
  const [maturityDate, setMaturityDate] = useState("");
  const [compFrequency,setCompFrequency]= useState("YEARLY");
  const [rdTotalInvested, setRdTotalInvested] = useState("");

  // ── Form — Mutual fund ──
  const [selectedFund,  setSelectedFund]  = useState<MutualFundScheme | null>(null);
  const [mfAmount,      setMfAmount]      = useState("");
  const [mfNav,         setMfNav]         = useState("");
  const [mfNavDate,     setMfNavDate]     = useState("");
  const [mfNavLoading,  setMfNavLoading]  = useState(false);
  const [mfSip,         setMfSip]         = useState("");

  // ── Action inputs ──
  const [sellQuantities, setSellQuantities] = useState<Record<string, string>>({});
  const [redeemUnits,    setRedeemUnits]    = useState<Record<string, string>>({});
  const [depositAmounts, setDepositAmounts] = useState<Record<string, string>>({});

  // ── Data loading ──

  async function loadData() {
    const [d, a, v, s, tx] = await Promise.all([
      getDashboard(), getAssets(), getLatestValuations(), getSnapshots(), getTransactions(),
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

  // Auto-fetch current NAV when a fund is selected so the NAV field is pre-filled
  // and doesn't immediately diverge from the live price on the first refresh.
  useEffect(() => {
    if (!selectedFund) { setMfNav(""); setMfNavDate(""); return; }
    setMfNavLoading(true);
    getMfCurrentNav(selectedFund.scheme_code)
      .then((data) => { setMfNav(String(data.nav)); setMfNavDate(data.date); })
      .catch(() => {})
      .finally(() => setMfNavLoading(false));
  }, [selectedFund]);

  // ── Form helpers ──

  function resetForm() {
    setName(""); setQuantity(""); setAvgBuyPrice(""); setSelectedCrypto(null);
    setBoughtAtCurrentPrice(false); setPrincipal(""); setAnnualRate("");
    setStartDate(""); setMaturityDate(""); setCompFrequency("YEARLY");
    setSelectedFund(null); setMfAmount(""); setMfNav(""); setMfNavDate(""); setMfSip("");
    setRdTotalInvested("");
  }

  function handleCryptoSelect(coin: CryptoMarket) {
    setSelectedCrypto(coin);
    if (boughtAtCurrentPrice) setAvgBuyPrice(String(coin.current_price));
  }

  function handleBoughtAtCurrentPrice(checked: boolean) {
    setBoughtAtCurrentPrice(checked);
    if (checked && selectedCrypto) setAvgBuyPrice(String(selectedCrypto.current_price));
  }

  function handleRdTotalInvested(total: string) {
    setRdTotalInvested(total);
    const monthly = Number(principal), totalNum = Number(total);
    if (monthly > 0 && totalNum > 0) {
      const months = Math.floor(totalNum / monthly);
      if (months > 0) {
        const d = new Date();
        d.setMonth(d.getMonth() - (months - 1));
        setStartDate(d.toISOString().slice(0, 10));
      }
    }
  }

  // ── Actions ──

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
          coingecko_id: selectedCrypto.id, symbol: selectedCrypto.symbol,
          quantity: Number(quantity), avg_buy_price: Number(avgBuyPrice),
        } : {}),
        ...(FI.includes(assetType) ? {
          principal: Number(principal), annual_rate: Number(annualRate),
          start_date: startDate, maturity_date: maturityDate || undefined,
          compounding_frequency: compFrequency,
        } : {}),
        ...(assetType === "MUTUAL_FUND" && selectedFund ? {
          scheme_code: selectedFund.scheme_code,
          amount_invested: Number(mfAmount), nav_at_purchase: Number(mfNav),
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

  // ── Derived ──

  const pnlPositive = dashboard.total_pnl >= 0;
  const pnlPct = dashboard.pnl_percent ??
    (dashboard.total_invested > 0 ? (dashboard.total_pnl / dashboard.total_invested) * 100 : 0);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // RENDER
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-base)" }}>

      {/* ── Background layers ── */}
      <div className="ambient-layer ambient-dot-grid" />
      <div className="ambient-layer ambient-amber" />
      <div className="ambient-layer ambient-violet" />
      <div className="ambient-layer ambient-header-line" style={{ height: "1px", bottom: "auto" }} />

      {/* ── Sticky header ── */}
      <header className="sticky-header">
        <div className="mx-auto flex max-w-screen-xl items-center justify-between gap-4 px-6 py-3.5">

          {/* Logo + title */}
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
              style={{ background: "linear-gradient(135deg,rgba(245,158,11,0.22) 0%,rgba(251,191,36,0.10) 100%)", border: "1px solid rgba(245,158,11,0.32)", boxShadow: "0 0 20px rgba(245,158,11,0.12)" }}>
              <svg className="h-3.5 w-3.5 text-amber-400" viewBox="0 0 16 16" fill="none">
                <polyline points="1,13 5,8 9,10.5 15,3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="15" cy="3" r="1.5" fill="currentColor"/>
              </svg>
            </div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Investment Tracker</h1>
              <span className="live-badge">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />Live
              </span>
            </div>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-3">
            {lastRefreshed && (
              <p className="hidden text-[11px] sm:block" style={{ color: "var(--text-muted)" }}>
                Updated {lastRefreshed.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
              </p>
            )}
            <button type="button" onClick={refreshValuations} disabled={refreshing}
              aria-label="Refresh live prices" className="btn-refresh">
              <svg className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} viewBox="0 0 16 16" fill="none">
                <path d="M14 8A6 6 0 1 1 8 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M13.5 2v3.5H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
            <ThemeSwitcher />
            <button type="button" onClick={signOut} className="btn-refresh" aria-label="Sign out">
              Sign out
            </button>
          </div>

        </div>
      </header>

      {/* ── Main content ── */}
      <main className="relative z-10 mx-auto max-w-screen-xl px-6 py-6 space-y-6">

        {/* Error banner */}
        {error && (
          <div className="error-banner" role="alert">
            <svg className="h-3.5 w-3.5 shrink-0 text-red-400" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M8 5v3.5M8 10.8h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <span className="error-text text-sm">{error}</span>
            <button onClick={() => setError("")} aria-label="Dismiss error"
              className="ml-auto text-base leading-none" style={{ color: "var(--text-muted)" }}>×</button>
          </div>
        )}

        {/* ── KPI Strip (always visible) ── */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3" aria-label="Portfolio summary">
          <KpiCard label="Net Worth"    value={inr(dashboard.total_value)}   sub="Total portfolio value" accent="amber" />
          <KpiCard label="Total Invested" value={inr(dashboard.total_invested)} sub={`${assets.length} position${assets.length !== 1 ? "s" : ""} tracked`} accent="violet" />
          <KpiCard label="Profit / Loss"
            value={(pnlPositive ? "+" : "−") + inr(dashboard.total_pnl)}
            sub={`${pnlPositive ? "+" : "−"}${Math.abs(pnlPct).toFixed(2)}% overall return`}
            accent={pnlPositive ? "emerald" : "red"} />
        </section>

        {/* ── Tab navigation ── */}
        <div className="card overflow-visible" style={{ overflow: "visible" }}>
          <nav className="tab-nav" role="tablist" aria-label="Portfolio sections">
            {(["overview", "holdings", "transactions"] as Tab[]).map((t) => (
              <button key={t} type="button" role="tab" aria-selected={tab === t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => setTab(t)}>
                {t === "overview" ? "Overview" : t === "holdings" ? `Holdings${assets.length > 0 ? ` · ${assets.length}` : ""}` : `Transactions${transactions.length > 0 ? ` · ${transactions.length}` : ""}`}
              </button>
            ))}
          </nav>

          {/* ── Overview tab ── */}
          {tab === "overview" && (
            <div className="p-5 space-y-5" role="tabpanel">
              <AllocationCharts assets={assets} valuations={valuations} />
              {snapshots.length > 0 && <NetWorthChart snapshots={snapshots} />}
              {snapshots.length === 0 && assets.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl"
                    style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
                    <svg className="h-6 w-6" style={{ color: "var(--text-muted)" }} viewBox="0 0 20 20" fill="none">
                      <path d="M10 3v14M3 10h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    </svg>
                  </div>
                  <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>Nothing here yet</p>
                  <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Add your first holding in the Holdings tab to get started</p>
                  <button type="button" onClick={() => setTab("holdings")}
                    className="mt-4 rounded-lg px-4 py-2 text-xs font-medium transition-colors"
                    style={{ background: "rgba(245,158,11,0.10)", border: "1px solid rgba(245,158,11,0.25)", color: "#f59e0b" }}>
                    Go to Holdings →
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── Holdings tab ── */}
          {tab === "holdings" && (
            <div className="p-0" role="tabpanel">
              <div className="grid grid-cols-1 gap-0 lg:grid-cols-[1fr_380px]">

                {/* Holdings table */}
                <div style={{ borderRight: "1px solid var(--border-subtle)" }}>
                  <div className="card-header px-5 py-4">
                    <div>
                      <h2 className="section-title">Active Positions</h2>
                      <p className="section-sub">Click Refresh to update live values</p>
                    </div>
                    <span className="type-badge type-badge--amber">{assets.length} {assets.length === 1 ? "position" : "positions"}</span>
                  </div>

                  {assets.length > 0 && (
                    <div className="grid min-w-[640px] px-5 py-2 text-[9px] font-bold uppercase tracking-[0.13em]"
                      style={{
                        gridTemplateColumns: "minmax(0,1fr) 100px 110px 110px 110px minmax(130px,160px)",
                        borderBottom: "1px solid var(--border-subtle)",
                        background: "rgba(255,255,255,0.012)",
                        color: "var(--text-muted)",
                      }}>
                      <span>Asset</span><span>Type</span><span>Invested</span><span>Current</span><span>P&L</span><span>Actions</span>
                    </div>
                  )}

                  {assets.length === 0 ? (
                    <div className="flex flex-col items-center justify-center px-5 py-16 text-center">
                      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl"
                        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
                        <svg className="h-5 w-5" style={{ color: "var(--text-muted)" }} viewBox="0 0 20 20" fill="none">
                          <rect x="3" y="7" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                          <path d="M7 7V5a3 3 0 0 1 6 0v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                        </svg>
                      </div>
                      <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>No positions yet</p>
                      <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Use the form on the right to record your first holding</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      {assets.map((asset, idx) => {
                        const cfg    = TYPE_CFG[asset.asset_type] ?? TYPE_CFG.MUTUAL_FUND;
                        const val    = valuations[asset.id];
                        const pnlPos = val ? val.pnl >= 0 : true;

                        return (
                          <div key={asset.id}
                            className="group holdings-row grid min-w-[640px] items-center px-5 py-3"
                            style={{
                              gridTemplateColumns: "minmax(0,1fr) 100px 110px 110px 110px minmax(130px,160px)",
                              borderBottom: idx < assets.length - 1 ? "1px solid var(--border-subtle)" : "none",
                              background: `linear-gradient(90deg, ${cfg.rowAccent} 0%, transparent 40%)`,
                            }}>

                            {/* Name + sub-line */}
                            <div className="flex min-w-0 items-center gap-2.5">
                              <span className={`h-2 w-2 shrink-0 rounded-full ${cfg.dot}`} />
                              <div className="min-w-0">
                                <p className="truncate text-sm font-medium" style={{ color: "var(--text-primary)" }}>{asset.name}</p>

                                {asset.holding && (
                                  <p className="mt-0.5 text-[10px]" style={{ color: "var(--text-secondary)" }}>
                                    <span className="font-semibold text-amber-400">{fmtQty(asset.holding.quantity)} {asset.holding.symbol.toUpperCase()}</span>
                                    <span className="mx-1.5" style={{ color: "var(--text-muted)" }}>·</span>
                                    <span>Avg {inr(asset.holding.avg_buy_price)}</span>
                                    <span className="mx-1.5" style={{ color: "var(--text-muted)" }}>·</span>
                                    <span className={asset.liquidity_tier === "LIQUID" ? "text-emerald-400" : "text-orange-400"}>
                                      {asset.liquidity_tier === "LIQUID" ? "Liquid" : "Locked"}
                                    </span>
                                  </p>
                                )}
                                {asset.fi_holding && (
                                  <p className="mt-0.5 text-[10px]" style={{ color: "var(--text-secondary)" }}>
                                    <span className={`font-semibold ${asset.asset_type === "SAVINGS_ACC" ? "text-emerald-400" : "text-sky-400"}`}>
                                      {asset.asset_type === "RD" ? `${inr(asset.fi_holding.principal)}/mo` : inr(asset.fi_holding.principal)}
                                    </span>
                                    <span className="mx-1.5" style={{ color: "var(--text-muted)" }}>·</span>
                                    <span>{asset.fi_holding.annual_rate}% p.a. {asset.fi_holding.compounding_frequency.toLowerCase()}</span>
                                    <span className="mx-1.5" style={{ color: "var(--text-muted)" }}>·</span>
                                    <span className={asset.asset_type === "SAVINGS_ACC" ? "text-emerald-400" : "text-orange-400"}>
                                      {asset.asset_type === "SAVINGS_ACC" ? "Liquid" : "Locked"}
                                    </span>
                                  </p>
                                )}
                                {asset.mf_holding && (
                                  <p className="mt-0.5 text-[10px]" style={{ color: "var(--text-secondary)" }}>
                                    <span className="font-semibold text-violet-400">{inr(asset.mf_holding.amount_invested)}</span>
                                    <span className="mx-1.5" style={{ color: "var(--text-muted)" }}>·</span>
                                    <span>{fmtQty(asset.mf_holding.units)} units @ ₹{asset.mf_holding.nav_at_purchase.toFixed(2)}</span>
                                    {asset.mf_holding.monthly_sip && (
                                      <>
                                        <span className="mx-1.5" style={{ color: "var(--text-muted)" }}>·</span>
                                        <span className="text-violet-400">SIP {inr(asset.mf_holding.monthly_sip)}/mo</span>
                                      </>
                                    )}
                                  </p>
                                )}
                                {!asset.holding && !asset.fi_holding && !asset.mf_holding && (
                                  <p className="text-[10px] capitalize" style={{ color: "var(--text-muted)" }}>
                                    {asset.category} ·{" "}
                                    <span className={asset.liquidity_tier === "LIQUID" ? "text-emerald-400" : "text-orange-400"}>
                                      {asset.liquidity_tier === "LIQUID" ? "Liquid" : "Locked"}
                                    </span>
                                  </p>
                                )}
                              </div>
                            </div>

                            {/* Type */}
                            <div><span className={cfg.badge}>{asset.asset_type.replace("_", " ")}</span></div>

                            {/* Invested */}
                            <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                              {val ? inr(val.invested_amount) : <span style={{ color: "var(--text-muted)" }}>—</span>}
                            </span>

                            {/* Current */}
                            <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                              {val ? inr(val.current_value) : <span style={{ color: "var(--text-muted)" }}>—</span>}
                            </span>

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
                              <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>
                            )}

                            {/* Actions */}
                            <div className="flex items-center gap-1.5">
                              {asset.asset_type === "CRYPTO" && (
                                <>
                                  <input value={sellQuantities[asset.id] ?? ""} aria-label="Sell quantity"
                                    onChange={(e) => setSellQuantities((c) => ({ ...c, [asset.id]: e.target.value }))}
                                    placeholder="qty" inputMode="decimal"
                                    className="w-14 rounded-md px-2 py-1 text-[11px] outline-none"
                                    style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--input-color)" }}/>
                                  <button type="button" onClick={() => sellExistingCrypto(asset.id)}
                                    className="rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors"
                                    style={{ background: "rgba(251,191,36,0.10)", border: "1px solid rgba(251,191,36,0.28)", color: "#fbbf24" }}>
                                    Sell
                                  </button>
                                </>
                              )}
                              {asset.asset_type === "MUTUAL_FUND" && (
                                <>
                                  <input value={redeemUnits[asset.id] ?? ""} aria-label="Redeem units"
                                    onChange={(e) => setRedeemUnits((c) => ({ ...c, [asset.id]: e.target.value }))}
                                    placeholder="units" inputMode="decimal"
                                    className="w-16 rounded-md px-2 py-1 text-[11px] outline-none"
                                    style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--input-color)" }}/>
                                  <button type="button" onClick={() => redeemExistingMF(asset.id)}
                                    className="rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors"
                                    style={{ background: "rgba(167,139,250,0.10)", border: "1px solid rgba(167,139,250,0.28)", color: "#c4b5fd" }}>
                                    Redeem
                                  </button>
                                </>
                              )}
                              {(asset.asset_type === "SAVINGS_ACC" || asset.asset_type === "PPF") && (
                                <>
                                  <input value={depositAmounts[asset.id] ?? ""} aria-label="Deposit amount"
                                    onChange={(e) => setDepositAmounts((c) => ({ ...c, [asset.id]: e.target.value }))}
                                    placeholder="₹ add" inputMode="decimal"
                                    className="w-16 rounded-md px-2 py-1 text-[11px] outline-none"
                                    style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--input-color)" }}/>
                                  <button type="button" onClick={() => topUpExistingSavings(asset.id)}
                                    className="rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors"
                                    style={{ background: "rgba(52,211,153,0.10)", border: "1px solid rgba(52,211,153,0.28)", color: "#6ee7b7" }}>
                                    {asset.asset_type === "PPF" ? "Deposit" : "Top Up"}
                                  </button>
                                </>
                              )}
                              <button type="button" onClick={() => removeAsset(asset.id)}
                                aria-label={`Remove ${asset.name}`}
                                className="rounded-md px-2.5 py-1 text-[11px] font-medium opacity-0 transition-all group-hover:opacity-100"
                                style={{ background: "rgba(248,113,113,0.09)", border: "1px solid rgba(248,113,113,0.22)", color: "#f87171" }}>
                                Remove
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* ── Add Position form ── */}
                <div className="p-5" style={{ borderTop: "1px solid var(--border-subtle)" }}>
                  <h2 className="section-title">Add Position</h2>
                  <p className="section-sub mb-5">Record a new holding in your portfolio</p>

                  <div className="space-y-3.5">
                    <Field label="Asset Name">
                      <input value={name} onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Bitcoin, PPFAS Flexi Cap, SBI FD…" className="field-input"/>
                    </Field>

                    <Field label="Asset Type">
                      <select value={assetType}
                        onChange={(e) => { setAssetType(e.target.value); if (e.target.value === "SAVINGS_ACC") setCompFrequency("QUARTERLY"); }}
                        className="field-input appearance-none">
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
                          <Field label="Quantity">
                            <input value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="0.05" inputMode="decimal" className="field-input"/>
                          </Field>
                          <Field label="Avg Buy Price (₹)">
                            <input value={avgBuyPrice} onChange={(e) => setAvgBuyPrice(e.target.value)} placeholder="9200000" inputMode="decimal" disabled={boughtAtCurrentPrice} className="field-input"/>
                          </Field>
                        </div>
                        <label className="flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2.5"
                          style={{ background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.16)" }}>
                          <input type="checkbox" checked={boughtAtCurrentPrice}
                            onChange={(e) => handleBoughtAtCurrentPrice(e.target.checked)}
                            className="h-3.5 w-3.5 accent-amber-400"/>
                          <span className="text-xs" style={{ color: "var(--text-secondary)" }}>Bought at current market price</span>
                          {selectedCrypto && boughtAtCurrentPrice && (
                            <span className="ml-auto text-xs font-semibold text-amber-400">
                              ₹{selectedCrypto.current_price.toLocaleString("en-IN")}
                            </span>
                          )}
                        </label>
                      </>
                    )}

                    {assetType === "MUTUAL_FUND" && (
                      <>
                        <Field label="Fund"><MutualFundSelector selected={selectedFund} onSelect={setSelectedFund}/></Field>
                        <div className="grid grid-cols-2 gap-3">
                          <Field label="Total Amount Invested (₹)">
                            <input value={mfAmount} onChange={(e) => setMfAmount(e.target.value)} placeholder="50000" inputMode="decimal" className="field-input"/>
                          </Field>
                          <Field label={mfNavLoading ? "NAV at Purchase (₹) — fetching…" : mfNavDate ? `NAV at Purchase (₹) · as of ${mfNavDate}` : "NAV at Purchase (₹)"}>
                            <input value={mfNav} onChange={(e) => setMfNav(e.target.value)} placeholder="45.23" inputMode="decimal" className="field-input" disabled={mfNavLoading}/>
                          </Field>
                        </div>
                        {mfAmount && mfNav && Number(mfNav) > 0 && (
                          <p className="text-[10px]" style={{ color: "var(--text-secondary)" }}>
                            Units: <span className="font-semibold text-violet-400">{(Number(mfAmount) / Number(mfNav)).toFixed(4)}</span>
                          </p>
                        )}
                        {mfNavDate && (
                          <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                            NAV auto-filled from live data · override if your avg purchase NAV differs
                          </p>
                        )}
                        <Field label="Monthly SIP Amount (₹) — optional">
                          <input value={mfSip} onChange={(e) => setMfSip(e.target.value)} placeholder="5000 — auto-added every month" inputMode="decimal" className="field-input"/>
                        </Field>
                        {selectedFund && (
                          <div className="rounded-lg px-3 py-2"
                            style={{ background: "rgba(167,139,250,0.07)", border: "1px solid rgba(167,139,250,0.18)" }}>
                            <p className="truncate text-[10px] text-violet-300/80">{selectedFund.name}</p>
                            <p className="mt-0.5 text-[9px]" style={{ color: "var(--text-muted)" }}>Scheme Code: {selectedFund.scheme_code}</p>
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
                          <Field label="Annual Rate (%)">
                            <input value={annualRate} onChange={(e) => setAnnualRate(e.target.value)}
                              placeholder={assetType === "SAVINGS_ACC" ? "3.5" : "7.5"} inputMode="decimal" className="field-input"/>
                          </Field>
                        </div>
                        {assetType === "RD" && (
                          <Field label="Amount already invested (₹) — optional">
                            <input value={rdTotalInvested} onChange={(e) => handleRdTotalInvested(e.target.value)}
                              placeholder="e.g. 60000 — auto-fills start date" inputMode="decimal" className="field-input"/>
                            {rdTotalInvested && principal && Number(principal) > 0 && (
                              <p className="mt-1 text-[10px]" style={{ color: "var(--text-secondary)" }}>
                                ≈ <span className="font-semibold text-sky-400">{Math.floor(Number(rdTotalInvested)/Number(principal))} months</span>
                                {" "}— start date auto-filled below
                              </p>
                            )}
                          </Field>
                        )}
                        <div className={assetType === "SAVINGS_ACC" ? "" : "grid grid-cols-2 gap-3"}>
                          <Field label={assetType === "SAVINGS_ACC" ? "Date Opened" : "Start Date"}>
                            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="field-input"/>
                          </Field>
                          {assetType !== "SAVINGS_ACC" && (
                            <Field label="Maturity Date (opt)">
                              <input type="date" value={maturityDate} onChange={(e) => setMaturityDate(e.target.value)} className="field-input"/>
                            </Field>
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
                          <div className="rounded-lg px-3 py-2"
                            style={{ background: "rgba(52,211,153,0.06)", border: "1px solid rgba(52,211,153,0.16)" }}>
                            <p className="text-[10px] text-emerald-400/80">Always liquid · use Top Up to add deposits later</p>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  <button type="button" onClick={addAsset} disabled={loading} className="btn-primary mt-5">
                    {loading ? "Adding…" : "Add Position"}
                  </button>
                </div>

              </div>
            </div>
          )}

          {/* ── Transactions tab ── */}
          {tab === "transactions" && (
            <div role="tabpanel">
              {transactions.length === 0 ? (
                <div className="flex flex-col items-center justify-center px-5 py-16 text-center">
                  <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>No transactions yet</p>
                  <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>They will appear here once you add holdings</p>
                </div>
              ) : (
                <>
                  <div className="card-header px-5 py-3">
                    <div>
                      <h2 className="section-title">Transaction History</h2>
                      <p className="section-sub">All recorded portfolio activity</p>
                    </div>
                    <span className="type-badge type-badge--violet">{transactions.length} records</span>
                  </div>

                  <div className="overflow-x-auto">
                    <div className="grid min-w-[560px] px-5 py-2 text-[9px] font-bold uppercase tracking-[0.13em]"
                      style={{
                        gridTemplateColumns: "100px 1fr 80px 90px 110px 110px",
                        borderBottom: "1px solid var(--border-subtle)",
                        background: "rgba(255,255,255,0.012)",
                        color: "var(--text-muted)",
                      }}>
                      <span>Date</span><span>Asset</span><span>Type</span><span>Units</span><span>Price/Unit</span><span>Amount</span>
                    </div>
                    {transactions.slice(0, 50).map((tx, idx) => {
                      const assetCfg = TYPE_CFG[tx.asset_type] ?? TYPE_CFG.MUTUAL_FUND;
                      return (
                        <div key={tx.id}
                          className="holdings-row grid min-w-[560px] items-center px-5 py-2.5 text-xs"
                          style={{
                            gridTemplateColumns: "100px 1fr 80px 90px 110px 110px",
                            borderBottom: idx < Math.min(transactions.length, 50) - 1 ? "1px solid var(--border-subtle)" : "none",
                          }}>
                          <span className="font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>{tx.transaction_date}</span>
                          <div className="flex min-w-0 items-center gap-2">
                            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${assetCfg.dot}`}/>
                            <span className="truncate" style={{ color: "var(--text-secondary)" }}>{tx.asset_name}</span>
                          </div>
                          <span>
                            <span className={TX_CLASS[tx.transaction_type] ?? "tx-badge tx-badge--buy"}>{tx.transaction_type}</span>
                          </span>
                          <span className="font-mono text-[11px]" style={{ color: "var(--text-secondary)" }}>{tx.units != null ? fmtQty(tx.units) : "—"}</span>
                          <span className="font-mono text-[11px]" style={{ color: "var(--text-secondary)" }}>{tx.price_per_unit != null ? inr(tx.price_per_unit) : "—"}</span>
                          <span className="font-mono text-[11px] font-medium" style={{ color: "var(--text-primary)" }}>{tx.amount > 0 ? inr(tx.amount) : "—"}</span>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

      </main>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SUB-COMPONENTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="text-[9px] font-bold uppercase tracking-[0.15em]" style={{ color: "var(--text-muted)" }}>{label}</p>
      {children}
    </div>
  );
}

const ACCENT_CFG = {
  amber:   { bg: "linear-gradient(135deg, rgba(245,158,11,0.22) 0%, rgba(245,158,11,0.07) 45%, var(--bg-surface) 100%)", border: "rgba(245,158,11,0.32)",  bar: "linear-gradient(90deg, #f59e0b 0%, rgba(245,158,11,0.35) 60%, transparent 100%)", glow: "0 0 50px rgba(245,158,11,0.10), 0 1px 32px rgba(0,0,0,0.45)" },
  violet:  { bg: "linear-gradient(135deg, rgba(167,139,250,0.20) 0%, rgba(167,139,250,0.06) 45%, var(--bg-surface) 100%)", border: "rgba(167,139,250,0.28)", bar: "linear-gradient(90deg, #a78bfa 0%, rgba(167,139,250,0.35) 60%, transparent 100%)", glow: "0 0 50px rgba(167,139,250,0.09), 0 1px 32px rgba(0,0,0,0.45)" },
  emerald: { bg: "linear-gradient(135deg, rgba(52,211,153,0.18) 0%, rgba(52,211,153,0.05) 45%, var(--bg-surface) 100%)",  border: "rgba(52,211,153,0.26)",  bar: "linear-gradient(90deg, #34d399 0%, rgba(52,211,153,0.35) 60%, transparent 100%)", glow: "0 0 50px rgba(52,211,153,0.08), 0 1px 32px rgba(0,0,0,0.45)" },
  red:     { bg: "linear-gradient(135deg, rgba(248,113,113,0.18) 0%, rgba(248,113,113,0.05) 45%, var(--bg-surface) 100%)", border: "rgba(248,113,113,0.26)", bar: "linear-gradient(90deg, #f87171 0%, rgba(248,113,113,0.35) 60%, transparent 100%)", glow: "0 0 50px rgba(248,113,113,0.08), 0 1px 32px rgba(0,0,0,0.45)" },
};

function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub: string; accent: keyof typeof ACCENT_CFG }) {
  const a = ACCENT_CFG[accent];
  return (
    <div className={`kpi-${accent} relative overflow-hidden rounded-xl p-5`}
      style={{ background: a.bg, border: `1px solid ${a.border}`, boxShadow: a.glow }}>
      <div className="kpi-bar absolute inset-x-0 top-0 h-[2px]" style={{ background: a.bar }} />
      <p className={`kpi-label--${accent} text-[9px] font-bold uppercase tracking-[0.18em]`}>{label}</p>
      <p className="kpi-value mt-3 text-[28px] font-bold leading-none tracking-tight">{value}</p>
      <p className="kpi-sub mt-2 text-[11px]">{sub}</p>
    </div>
  );
}
