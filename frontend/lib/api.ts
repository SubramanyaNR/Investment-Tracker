// Same-origin proxy: next.config.ts rewrites /api/* to the backend server-side.
// Never default to localhost:8000 or a baked host IP — see CLAUDE.md "How the app is accessed".
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

// Session identity now lives in an httpOnly cookie set by the backend (architecture-002
// Phase 2) — the browser attaches it automatically on same-origin requests, no header
// needed. Only the CSRF double-submit cookie needs to be read and echoed back manually,
// since it must be JS-readable (not httpOnly) for that to work.
function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function csrfHeaders(): Record<string, string> {
  const token = readCookie("csrf_token");
  return token ? { "X-CSRF-Token": token } : {};
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

export type AssetPage = {
  items: Asset[];
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
  const res = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...csrfHeaders(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

// ── Auth ───────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Login failed: ${res.status} ${text}`);
  }
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", headers: csrfHeaders() });
}

export async function getMe(): Promise<{ user_id: string } | null> {
  const res = await fetch(`${API_BASE_URL}/auth/me`, { cache: "no-store" });
  return res.ok ? res.json() : null;
}

export async function refreshSession(): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, { method: "POST", headers: csrfHeaders() });
  return res.ok;
}

export type AuthStatus = { auth_enabled: boolean };

// Unauthenticated by design — must work pre-login so the disabled-auth banner
// can render even when there's no session yet.
export async function getAuthStatus(): Promise<AuthStatus | null> {
  const res = await fetch(`${API_BASE_URL}/auth/status`, { cache: "no-store" });
  return res.ok ? res.json() : null;
}

// ── API functions ──────────────────────────────────────────────────────────

export const getDashboard = () => get<{
  total_value: number;
  total_invested: number;
  total_pnl: number;
  pnl_percent: number;
  is_onboarding_eligible: boolean;
}>("/dashboard");
export const getAssets = async (): Promise<Asset[]> => {
  const firstPage = await get<AssetPage>("/assets?limit=200");
  let allAssets = [...firstPage.items];
  let offset = 200;

  // CEO: Cap at 5 pages × 200 = 1000 assets. Keeps existing UX identical.
  while (allAssets.length < firstPage.total && offset < 1000) {
    const nextPage = await get<AssetPage>(`/assets?limit=200&offset=${offset}`);
    if (nextPage.items.length === 0) break;
    allAssets = [...allAssets, ...nextPage.items];
    offset += 200;
  }
  return allAssets;
};
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
  const res = await fetch(`${API_BASE_URL}/import/csv?dry_run=true`, {
    method: "POST",
    headers: csrfHeaders(),
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
  const res = await fetch(`${API_BASE_URL}/import/csv?dry_run=false`, {
    method: "POST",
    headers: csrfHeaders(),
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
    headers: csrfHeaders(),
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

export async function exportHoldings() {
  const res = await fetch(`${API_BASE_URL}/export/holdings`);
  if (!res.ok) throw new Error(`Export holdings failed: ${res.status}`);
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const disposition = res.headers.get("Content-Disposition");
  let filename = "wealthsignal_holdings.csv";
  if (disposition && disposition.includes("filename=")) {
    filename = disposition.split("filename=")[1].replace(/"/g, "");
  }
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function exportTransactions() {
  const res = await fetch(`${API_BASE_URL}/export/transactions`);
  if (!res.ok) throw new Error(`Export transactions failed: ${res.status}`);
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const disposition = res.headers.get("Content-Disposition");
  let filename = "wealthsignal_transactions.csv";
  if (disposition && disposition.includes("filename=")) {
    filename = disposition.split("filename=")[1].replace(/"/g, "");
  }
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
