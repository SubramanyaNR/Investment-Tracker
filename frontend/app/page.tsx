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
} from "@/lib/api";

type Dashboard = {
  total_value: number;
  total_invested: number;
  total_pnl: number;
  pnl_percent?: number;
};

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard>({
    total_value: 0,
    total_invested: 0,
    total_pnl: 0,
  });

  const [assets, setAssets] = useState<Asset[]>([]);
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState("MUTUAL_FUND");
  const [coingeckoId, setCoingeckoId] = useState("bitcoin");
  const [symbol, setSymbol] = useState("BTC");
  const [quantity, setQuantity] = useState("");
  const [avgBuyPrice, setAvgBuyPrice] = useState("");
  const [sellQuantities, setSellQuantities] = useState<Record<string, string>>(
    {},
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  async function loadData() {
    const [dashboardData, assetData] = await Promise.all([
      getDashboard(),
      getAssets(),
    ]);

    setDashboard(dashboardData);
    setAssets(assetData);
  }

  useEffect(() => {
    loadData().catch((err) => {
      console.error(err);
      setError("Failed to load dashboard data.");
    });
  }, []);

  async function addAsset() {
    if (!name.trim()) {
      setError("Enter an asset name first.");
      return;
    }

    if (assetType === "CRYPTO") {
      if (!coingeckoId.trim() || !symbol.trim() || !quantity || !avgBuyPrice) {
        setError("Crypto requires CoinGecko ID, symbol, quantity, and buy price.");
        return;
      }
    }

    try {
      setLoading(true);
      setError("");

      await createAsset({
        name,
        asset_type: assetType,
        category:
          assetType === "CRYPTO"
            ? "crypto"
            : assetType === "FD" || assetType === "RD" || assetType === "PPF"
            ? "debt"
            : "equity",
        liquidity_tier:
          assetType === "FD" || assetType === "PPF" ? "LOCKED" : "LIQUID",
        ...(assetType === "CRYPTO"
          ? {
              coingecko_id: coingeckoId,
              symbol,
              quantity: Number(quantity),
              avg_buy_price: Number(avgBuyPrice),
            }
          : {}),
      });

      setName("");
      setQuantity("");
      setAvgBuyPrice("");
      await loadData();
    } catch (err) {
      console.error(err);
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
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to refresh prices.");
    } finally {
      setRefreshing(false);
    }
  }

  async function removeAsset(assetId: string) {
    const confirmed = confirm("Delete this asset? This cannot be undone.");
    if (!confirmed) return;

    try {
      setError("");
      await deleteAsset(assetId);
      await loadData();
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to delete asset.");
    }
  }

  async function sellExistingCrypto(assetId: string) {
    const sellQuantity = Number(sellQuantities[assetId]);

    if (!sellQuantity || sellQuantity <= 0) {
      setError("Enter a valid sell quantity.");
      return;
    }

    try {
      setError("");
      await sellCrypto(assetId, sellQuantity);
      setSellQuantities((current) => ({ ...current, [assetId]: "" }));
      await recalculateValuations();
      await loadData();
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to sell crypto.");
    }
  }

  return (
    <main className="min-h-screen bg-black px-6 py-6 text-zinc-100">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col justify-between gap-4 border-b border-zinc-900 pb-5 md:flex-row md:items-end">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">
              Portfolio Observability
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-white">
              Investment Command Center
            </h1>
          </div>

          <button
            type="button"
            onClick={refreshValuations}
            disabled={refreshing}
            className="w-fit rounded-lg border border-cyan-400/30 px-4 py-2 text-sm text-cyan-300 hover:bg-cyan-400/10 disabled:opacity-50"
          >
            {refreshing ? "Refreshing" : "Refresh Prices"}
          </button>
        </header>

        {error ? (
          <div className="rounded-lg border border-red-400/30 bg-red-950/30 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        ) : null}

        <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Metric title="Net Worth" value={dashboard.total_value} tone="cyan" />
          <Metric
            title="Invested"
            value={dashboard.total_invested}
            tone="violet"
          />
          <Metric
            title="Profit / Loss"
            value={dashboard.total_pnl}
            tone="emerald"
          />
        </section>

        <section className="rounded-xl border border-cyan-400/20 bg-zinc-950 p-5 shadow-[0_0_40px_rgba(34,211,238,0.08)]">
          <h2 className="text-sm font-medium text-cyan-300">Add Asset</h2>

          <div className="mt-4 grid gap-3 md:grid-cols-[1fr_180px_120px]">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Bitcoin, FD 2026, Parag Parikh Flexi Cap..."
              className="rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none focus:border-cyan-400"
            />

            <select
              value={assetType}
              onChange={(e) => setAssetType(e.target.value)}
              className="rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none focus:border-cyan-400"
            >
              <option value="MUTUAL_FUND">Mutual Fund</option>
              <option value="CRYPTO">Crypto</option>
              <option value="FD">FD</option>
              <option value="RD">RD</option>
              <option value="PPF">PPF</option>
            </select>

            <button
              type="button"
              onClick={addAsset}
              disabled={loading}
              className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-black hover:bg-cyan-300 disabled:opacity-50"
            >
              {loading ? "Adding" : "Add"}
            </button>
          </div>

          {assetType === "CRYPTO" ? (
            <div className="mt-3 grid gap-3 md:grid-cols-4">
              <input
                value={coingeckoId}
                onChange={(e) => setCoingeckoId(e.target.value)}
                placeholder="coingecko id: bitcoin"
                className="rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none focus:border-cyan-400"
              />

              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="symbol: BTC"
                className="rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none focus:border-cyan-400"
              />

              <input
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="quantity: 0.05"
                inputMode="decimal"
                className="rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none focus:border-cyan-400"
              />

              <input
                value={avgBuyPrice}
                onChange={(e) => setAvgBuyPrice(e.target.value)}
                placeholder="avg buy price INR"
                inputMode="decimal"
                className="rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none focus:border-cyan-400"
              />
            </div>
          ) : null}
        </section>

        <section className="rounded-xl border border-zinc-800 bg-zinc-950">
          <div className="flex items-center justify-between border-b border-zinc-900 px-5 py-4">
            <div>
              <h2 className="font-medium text-white">Assets</h2>
              <p className="text-sm text-zinc-500">
                Manually tracked holdings across debt, equity, and crypto.
              </p>
            </div>

            <span className="text-sm text-cyan-300">{assets.length} assets</span>
          </div>

          {assets.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-zinc-500">
              No assets yet. Add your first FD, mutual fund, or crypto holding.
            </div>
          ) : (
            <div className="divide-y divide-zinc-900">
              {assets.map((asset) => (
                <div
                  key={asset.id}
                  className="grid gap-3 px-5 py-4 text-sm md:grid-cols-[1fr_160px_120px_120px_260px]"
                >
                  <div>
                    <p className="font-medium text-zinc-100">{asset.name}</p>
                    <p className="text-xs text-zinc-500">{asset.id}</p>
                  </div>

                  <Badge>{asset.asset_type}</Badge>
                  <span className="text-zinc-400">{asset.category}</span>
                  <span className="text-zinc-400">{asset.liquidity_tier}</span>

                  <div className="flex flex-wrap items-center gap-2">
                    {asset.asset_type === "CRYPTO" ? (
                      <>
                        <input
                          value={sellQuantities[asset.id] ?? ""}
                          onChange={(e) =>
                            setSellQuantities((current) => ({
                              ...current,
                              [asset.id]: e.target.value,
                            }))
                          }
                          placeholder="sell qty"
                          inputMode="decimal"
                          className="w-24 rounded-lg border border-zinc-800 bg-black px-2 py-1 text-xs text-zinc-100 outline-none focus:border-cyan-400"
                        />

                        <button
                          type="button"
                          onClick={() => sellExistingCrypto(asset.id)}
                          className="rounded-lg border border-amber-400/30 px-3 py-1 text-xs text-amber-300 hover:bg-amber-400/10"
                        >
                          Sell
                        </button>
                      </>
                    ) : null}

                    <button
                      type="button"
                      onClick={() => removeAsset(asset.id)}
                      className="rounded-lg border border-red-400/30 px-3 py-1 text-xs text-red-300 hover:bg-red-400/10"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function Metric({
  title,
  value,
  tone,
}: {
  title: string;
  value: number;
  tone: "cyan" | "violet" | "emerald";
}) {
  const glow = {
    cyan: "border-cyan-400/30 text-cyan-300 shadow-[0_0_40px_rgba(34,211,238,0.08)]",
    violet:
      "border-violet-400/30 text-violet-300 shadow-[0_0_40px_rgba(167,139,250,0.08)]",
    emerald:
      "border-emerald-400/30 text-emerald-300 shadow-[0_0_40px_rgba(52,211,153,0.08)]",
  }[tone];

  return (
    <div className={`rounded-xl border bg-zinc-950 p-5 ${glow}`}>
      <p className="text-sm text-zinc-500">{title}</p>
      <p className="mt-3 text-3xl font-semibold text-white">
        ₹{Number(value).toLocaleString("en-IN")}
      </p>
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="w-fit rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-300">
      {children}
    </span>
  );
}
