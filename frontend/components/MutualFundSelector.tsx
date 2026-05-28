"use client";

import { useEffect, useRef, useState } from "react";
import { searchMutualFunds, type MutualFundScheme } from "@/lib/api";

interface Props {
  selected: MutualFundScheme | null;
  onSelect: (scheme: MutualFundScheme) => void;
}

export default function MutualFundSelector({ selected, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MutualFundScheme[]>([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.length < 3) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await searchMutualFunds(query);
        setResults(data);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  function handleSelect(scheme: MutualFundScheme) {
    onSelect(scheme);
    setOpen(false);
    setQuery("");
    setResults([]);
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-lg px-3 py-[0.5625rem] text-[0.8125rem] leading-6 outline-none transition-colors text-left"
        style={{
          background: "rgba(255,255,255,0.055)",
          border: open
            ? "1px solid rgba(167,139,250,0.55)"
            : "1px solid rgba(255,255,255,0.11)",
          color: selected ? "#cbd5e1" : "rgba(255,255,255,0.2)",
        }}
      >
        {selected ? (
          <span className="flex items-center gap-2 truncate">
            <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded bg-violet-400/20 text-[8px] font-bold text-violet-300">MF</span>
            <span className="truncate text-xs">{selected.name}</span>
          </span>
        ) : (
          <span>Search fund by name…</span>
        )}
        <svg
          className={`ml-2 h-3 w-3 shrink-0 text-slate-600 transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 10 6" fill="none" stroke="currentColor" strokeWidth="1.5"
        >
          <path d="M1 1l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl"
          style={{
            background: "#111128",
            border: "1px solid rgba(167,139,250,0.2)",
            boxShadow: "0 16px 40px rgba(0,0,0,0.7)",
          }}
        >
          {/* Search input */}
          <div style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }} className="p-2">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type 3+ chars — e.g. HDFC Flexi, Mirae, Parag…"
              className="w-full rounded-lg bg-white/[0.04] px-2.5 py-1.5 text-xs text-slate-300 outline-none placeholder:text-slate-700 focus:bg-white/[0.06]"
            />
          </div>

          {/* Results */}
          {query.length < 3 ? (
            <p className="px-3 py-3 text-[11px] text-slate-600">Type at least 3 characters to search</p>
          ) : searching ? (
            <p className="px-3 py-3 text-[11px] text-slate-600">Searching…</p>
          ) : results.length === 0 ? (
            <p className="px-3 py-3 text-[11px] text-slate-600">No funds found</p>
          ) : (
            <ul className="max-h-60 overflow-y-auto py-1">
              {results.map((scheme) => (
                <li key={scheme.scheme_code}>
                  <button
                    type="button"
                    onClick={() => handleSelect(scheme)}
                    className="flex w-full items-start gap-3 px-3 py-2.5 text-left transition-colors hover:bg-white/[0.04]"
                  >
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-violet-400/15 text-[8px] font-bold text-violet-300">MF</span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium leading-snug text-slate-200">{scheme.name}</p>
                      <p className="mt-0.5 text-[10px] text-slate-600">Code: {scheme.scheme_code}</p>
                    </div>
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
