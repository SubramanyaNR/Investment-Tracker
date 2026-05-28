"use client";

import { useState } from "react";
import { createAsset } from "@/lib/api";

export function AddAssetForm() {
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState("MUTUAL_FUND");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    console.log("Add clicked");

    if (!name.trim()) {
      setError("Enter an asset name first.");
      return;
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
      });

      window.location.reload();
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to add asset.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-cyan-400/20 bg-zinc-950/80 p-5 shadow-[0_0_40px_rgba(34,211,238,0.08)]">
      <h2 className="text-sm font-medium text-cyan-300">Add Asset</h2>

      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_180px_120px]">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Parag Parikh Flexi Cap, Bitcoin, FD 2026..."
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
          onClick={() => {
            alert("clicked");
            console.log("Add clicked");
          }}
          className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-black"
        >
          Add
        </button>
      </div>

      {error ? <p className="mt-3 text-sm text-red-400">{error}</p> : null}
    </div>
  );
}

