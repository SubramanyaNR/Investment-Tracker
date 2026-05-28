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
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={`selector-trigger ${selected ? "has-value" : ""} ${open ? "open" : ""}`}
      >
        {selected ? (
          <span className="flex items-center gap-2 truncate">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={selected.image} alt={selected.name} className="h-4 w-4 shrink-0 rounded-full" />
            <span className="truncate">{selected.name}</span>
            <span className="shrink-0" style={{ color: "var(--text-muted)" }}>({selected.symbol})</span>
          </span>
        ) : loading ? (
          <span>Loading coins…</span>
        ) : (
          <span>Select a coin…</span>
        )}
        <svg
          className={`ml-2 h-3 w-3 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
          style={{ color: "var(--text-muted)" }}
          viewBox="0 0 10 6" fill="none" stroke="currentColor" strokeWidth="1.5"
        >
          <path d="M1 1l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="dropdown-popup absolute z-50 mt-1 w-full" role="listbox">
          <div className="dropdown-search p-2">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search coins…"
              aria-label="Search coins"
              className="dropdown-inner-search"
            />
          </div>

          {error ? (
            <p className="px-3 py-3 text-[11px]" style={{ color: "var(--text-secondary)" }}>{error}</p>
          ) : filtered.length === 0 ? (
            <p className="px-3 py-3 text-[11px]" style={{ color: "var(--text-muted)" }}>No results</p>
          ) : (
            <ul className="max-h-52 overflow-y-auto py-1">
              {filtered.map((coin) => (
                <li key={coin.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={selected?.id === coin.id}
                    onClick={() => handleSelect(coin)}
                    className="dropdown-item flex w-full items-center gap-3 px-3 py-2 text-left"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={coin.image} alt={coin.name} className="h-5 w-5 shrink-0 rounded-full" />
                    <span className="flex-1 text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                      {coin.name}
                    </span>
                    <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{coin.symbol}</span>
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
