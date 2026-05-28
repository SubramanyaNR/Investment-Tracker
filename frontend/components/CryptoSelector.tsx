"use client";

import { useEffect, useRef, useState } from "react";
import { getTopCryptos, type CryptoMarket } from "@/lib/api";

interface Props {
  selected: CryptoMarket | null;
  onSelect: (coin: CryptoMarket) => void;
}

export default function CryptoSelector({ selected, onSelect }: Props) {
  const [coins, setCoins] = useState<CryptoMarket[]>([]);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    getTopCryptos()
      .then(setCoins)
      .catch(() => setError("Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  const filtered = coins.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.symbol.toLowerCase().includes(search.toLowerCase()),
  );

  function handleSelect(coin: CryptoMarket) {
    onSelect(coin);
    setOpen(false);
    setSearch("");
  }

  return (
    <div ref={ref} className="relative">
      {/* Trigger button styled like field-input */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-lg px-3 py-[0.5625rem] text-[0.8125rem] leading-6 outline-none transition-colors"
        style={{
          background: "rgba(255,255,255,0.035)",
          border: open
            ? "1px solid rgba(245,158,11,0.45)"
            : "1px solid rgba(255,255,255,0.08)",
          color: selected ? "#cbd5e1" : "rgba(255,255,255,0.18)",
        }}
      >
        {selected ? (
          <span className="flex items-center gap-2 truncate">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={selected.image} alt={selected.name} className="h-4 w-4 shrink-0 rounded-full" />
            <span className="truncate">{selected.name}</span>
            <span className="shrink-0 text-slate-600">({selected.symbol})</span>
          </span>
        ) : loading ? (
          <span>Loading coins…</span>
        ) : (
          <span>Select a coin…</span>
        )}
        <svg
          className={`ml-2 h-3 w-3 shrink-0 text-slate-600 transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 10 6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M1 1l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl"
          style={{
            background: "#0e0e18",
            border: "1px solid rgba(255,255,255,0.09)",
            boxShadow: "0 16px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(34,211,238,0.06)",
          }}
        >
          {/* Search */}
          <div style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }} className="p-2">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search coins…"
              className="w-full rounded-lg bg-white/[0.04] px-2.5 py-1.5 text-xs text-slate-300 outline-none placeholder:text-slate-700 focus:bg-white/[0.06]"
            />
          </div>

          {/* List */}
          {error ? (
            <p className="px-3 py-3 text-[11px] text-red-400">{error}</p>
          ) : filtered.length === 0 ? (
            <p className="px-3 py-3 text-[11px] text-slate-600">No results</p>
          ) : (
            <ul className="max-h-52 overflow-y-auto py-1">
              {filtered.map((coin) => (
                <li key={coin.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(coin)}
                    className="flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-white/[0.04]"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={coin.image}
                      alt={coin.name}
                      className="h-5 w-5 shrink-0 rounded-full"
                    />
                    <span className="flex-1 text-xs font-medium text-slate-200">
                      {coin.name}
                    </span>
                    <span className="text-[10px] text-slate-600">{coin.symbol}</span>
                    <span className="text-[10px] font-semibold text-amber-400">
                      ₹{coin.current_price.toLocaleString("en-IN")}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
