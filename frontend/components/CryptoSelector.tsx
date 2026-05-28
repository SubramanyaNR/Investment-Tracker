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
      .catch(() => setError("Failed to load cryptos"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
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
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none hover:border-cyan-400/60 focus:border-cyan-400"
      >
        {selected ? (
          <span className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={selected.image} alt={selected.name} className="h-4 w-4 rounded-full" />
            <span>{selected.name}</span>
            <span className="text-zinc-500">({selected.symbol})</span>
          </span>
        ) : loading ? (
          <span className="text-zinc-500">Loading cryptos…</span>
        ) : (
          <span className="text-zinc-500">Select crypto…</span>
        )}
        <svg
          className={`ml-2 h-3 w-3 shrink-0 text-zinc-500 transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 10 6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M1 1l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 shadow-lg">
          <div className="border-b border-zinc-800 p-2">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search…"
              className="w-full rounded bg-black px-2 py-1.5 text-sm text-zinc-100 outline-none placeholder:text-zinc-600"
            />
          </div>

          {error ? (
            <p className="px-3 py-3 text-xs text-red-400">{error}</p>
          ) : filtered.length === 0 ? (
            <p className="px-3 py-3 text-xs text-zinc-500">No results</p>
          ) : (
            <ul className="max-h-56 overflow-y-auto py-1">
              {filtered.map((coin) => (
                <li key={coin.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(coin)}
                    className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-zinc-900"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={coin.image} alt={coin.name} className="h-5 w-5 shrink-0 rounded-full" />
                    <span className="flex-1 font-medium text-zinc-100">{coin.name}</span>
                    <span className="text-xs text-zinc-500">{coin.symbol}</span>
                    <span className="text-xs text-cyan-300">
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
