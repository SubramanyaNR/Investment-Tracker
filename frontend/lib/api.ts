const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://172.23.80.6:8000";

// ── Types ──────────────────────────────────────────────────────────────────

export type CryptoHoldingDetail = {
  symbol: string;
  coingecko_id: string;
  quantity: number;
  avg_buy_price: number;
};

export type FixedIncomeHoldingDetail = {
  principal: number;
  annual_rate: number;
  start_date: string;
  maturity_date: string | null;
  compounding_frequency: string;
};

export type MutualFundHoldingDetail = {
  scheme_code: string;
  units: number;
  nav_at_purchase: number;
  amount_invested: number;
  monthly_sip: number | null;
};

export type Asset = {
  id: string;
  name: string;
  asset_type: string;
  category: string;
  liquidity_tier: string;
  created_at: string;
  holding?: CryptoHoldingDetail;
  fi_holding?: FixedIncomeHoldingDetail;
  mf_holding?: MutualFundHoldingDetail;
};

export type CryptoMarket = {
  id: string;
  name: string;
  symbol: string;
  image: string;
  current_price: number;
  market_cap_rank: number;
};

export type MutualFundScheme = {
  scheme_code: string;
  name: string;
};

export type Valuation = {
  asset_id: string;
  valuation_date: string;
  invested_amount: number;
  current_value: number;
  pnl: number;
  source: string;
};

export type Snapshot = {
  snapshot_date: string;
  total_invested: number;
  total_value: number;
  total_pnl: number;
};

export type TxRecord = {
  id: string;
  asset_id: string;
  asset_name: string;
  asset_type: string;
  transaction_type: string;
  transaction_date: string;
  amount: number;
  units: number | null;
  price_per_unit: number | null;
};

// ── Helpers ────────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

// ── API functions ──────────────────────────────────────────────────────────

export const getDashboard = () => get<Record<string, number>>("/dashboard");
export const getAssets = () => get<Asset[]>("/assets");
export const getLatestValuations = () => get<Valuation[]>("/valuations/latest");
export const getSnapshots = () => get<Snapshot[]>("/snapshots");
export const getTransactions = () => get<TxRecord[]>("/transactions");
export const getTopCryptos = () => get<CryptoMarket[]>("/market/crypto/top");
export const recalculateValuations = () => post<unknown>("/valuations/recalculate");

export const searchMutualFunds = (q: string) =>
  get<MutualFundScheme[]>(`/market/mutual-funds/search?q=${encodeURIComponent(q)}`);

export async function createAsset(payload: {
  name: string;
  asset_type: string;
  category: string;
  liquidity_tier: string;
  // crypto
  coingecko_id?: string;
  symbol?: string;
  quantity?: number;
  avg_buy_price?: number;
  // fixed income
  principal?: number;
  annual_rate?: number;
  start_date?: string;
  maturity_date?: string;
  compounding_frequency?: string;
  // mutual fund
  scheme_code?: string;
  amount_invested?: number;
  nav_at_purchase?: number;
  monthly_sip?: number;
}) {
  return post<Asset>("/assets", payload);
}

export async function deleteAsset(assetId: string) {
  const res = await fetch(`${API_BASE_URL}/assets/${assetId}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`DELETE /assets/${assetId} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function sellCrypto(assetId: string, quantity: number) {
  return post<{ asset_id: string; remaining_quantity: number }>(
    `/assets/${assetId}/sell-crypto`,
    { quantity },
  );
}

export async function redeemMutualFund(assetId: string, units: number) {
  return post<{ asset_id: string; remaining_units: number }>(
    `/assets/${assetId}/redeem-mf`,
    { units },
  );
}
