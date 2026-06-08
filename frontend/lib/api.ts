import { supabase } from "./supabase";

// Same-origin proxy: next.config.ts rewrites /api/* to the backend server-side.
// Never default to localhost:8000 or a baked host IP — see CLAUDE.md "How the app is accessed".
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

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

export type ManualHoldingDetail = {
  cost_basis: number;
  current_value: number;
  notes: string | null;
  value_updated_at: string;
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
  manual_holding?: ManualHoldingDetail;
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

export type TxPage = {
  items: TxRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type MarketFreshness = {
  crypto_updated_at: number | null;  // Unix epoch seconds, null if no fetch yet
  mf_updated_at: number | null;
};

export type XirrAsset = {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  xirr: number | null;        // decimal e.g. 0.143 for 14.3%; null = insufficient data
  start_date: string | null;  // ISO date of first transaction
  total_invested: number;
  current_value: number;
};

export type XirrResult = {
  portfolio_xirr: number | null;
  portfolio_start_date: string | null;
  manual_assets_excluded: boolean;
  assets: XirrAsset[];
};

export type PerformanceEntry = {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  pct_change: number;     // e.g. 6.3 for +6.3%
  start_value: number;
  end_value: number;
};

export type PerformanceResult = {
  top: PerformanceEntry[];
  bottom: PerformanceEntry[];
  has_data: boolean;
  period: "monthly" | "daily";
  period_label: string;   // "Jun 2026" (monthly) or ISO date (daily)
};

export type ImportPreviewRow = {
  row_num: number;
  transaction_date: string;
  asset_type: string;
  asset_name: string;
  transaction_type: string;
  amount: number;
  units: number | null;
  price_per_unit: number | null;
  coingecko_id: string | null;
  scheme_code: string | null;
};

export type ImportError = {
  row_num: number;
  errors: string[];
  raw: Record<string, string>;
};

export type ImportDryRunResult = {
  dry_run: true;
  valid_count: number;
  error_count: number;
  preview: ImportPreviewRow[];
  errors: ImportError[];
};

export type ImportConfirmResult = {
  dry_run: false;
  transactions_imported: number;
  assets_created: number;
  assets_merged: number;
  error_count: number;
  errors: ImportError[];
};

// ── Helpers ────────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(await authHeaders()),
    },
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
export const getTransactions = () => get<TxPage>("/transactions");
export const getTopCryptos = () => get<CryptoMarket[]>("/market/crypto/top");
export const getMarketFreshness = () => get<MarketFreshness>("/market/freshness");
export const getXirr = () => get<XirrResult>("/xirr");
export const getMonthlyPerformance = () => get<PerformanceResult>("/performance/monthly");
export const getDailyPerformance = () => get<PerformanceResult>("/performance/daily");

export async function importCsvDryRun(file: File): Promise<ImportDryRunResult> {
  const form = new FormData();
  form.append("file", file);
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/import/csv?dry_run=true`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Import preview failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function importCsvConfirm(file: File): Promise<ImportConfirmResult> {
  const form = new FormData();
  form.append("file", file);
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/import/csv?dry_run=false`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Import failed: ${res.status} ${text}`);
  }
  return res.json();
}
export const recalculateValuations = () => post<unknown>("/valuations/recalculate");

export const searchMutualFunds = (q: string) =>
  get<MutualFundScheme[]>(`/market/mutual-funds/search?q=${encodeURIComponent(q)}`);

export const getMfCurrentNav = (schemeCode: string) =>
  get<{ scheme_code: string; nav: number; date: string }>(`/market/mutual-funds/${schemeCode}/nav`);

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
  const res = await fetch(`${API_BASE_URL}/assets/${assetId}`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
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

export async function topUpSavings(assetId: string, amount: number) {
  return post<{ asset_id: string; new_principal: number }>(
    `/assets/${assetId}/top-up`,
    { amount },
  );
}
