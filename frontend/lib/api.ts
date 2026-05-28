const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://172.23.80.6:8000";

export type CryptoHoldingDetail = {
  symbol: string;
  coingecko_id: string;
  quantity: number;
  avg_buy_price: number;
};

export type Asset = {
  id: string;
  name: string;
  asset_type: string;
  category: string;
  liquidity_tier: string;
  created_at: string;
  holding?: CryptoHoldingDetail;
};

export type CryptoMarket = {
  id: string;
  name: string;
  symbol: string;
  image: string;
  current_price: number;
  market_cap_rank: number;
};

export async function getDashboard() {
  const res = await fetch(`${API_BASE_URL}/dashboard`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to load dashboard");
  }

  return res.json();
}

export async function getAssets(): Promise<Asset[]> {
  const res = await fetch(`${API_BASE_URL}/assets`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to load assets");
  }

  return res.json();
}


export async function createAsset(payload: {
  name: string;
  asset_type: string;
  category: string;
  liquidity_tier: string;
  coingecko_id?: string;
  symbol?: string;
  quantity?: number;
  avg_buy_price?: number;
}) {
  const res = await fetch(`${API_BASE_URL}/assets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to create asset: ${res.status} ${text}`);
  }

  return res.json();
}

export async function recalculateValuations() {
  const res = await fetch(`${API_BASE_URL}/valuations/recalculate`, {
    method: "POST",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to recalculate valuations: ${res.status} ${text}`);
  }

  return res.json();
}

export async function deleteAsset(assetId: string) {
  const res = await fetch(`${API_BASE_URL}/assets/${assetId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to delete asset: ${res.status} ${text}`);
  }

  return res.json();
}

export async function getTopCryptos(): Promise<CryptoMarket[]> {
  const res = await fetch(`${API_BASE_URL}/market/crypto/top`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to load top cryptos");
  }

  return res.json();
}

export async function sellCrypto(assetId: string, quantity: number) {
  const res = await fetch(`${API_BASE_URL}/assets/${assetId}/sell-crypto`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ quantity }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to sell crypto: ${res.status} ${text}`);
  }

  return res.json();
}
