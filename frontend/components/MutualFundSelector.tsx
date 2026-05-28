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
    if (query.length < 3) { setResults([]); return; }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        setResults(await searchMutualFunds(query));
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
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
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
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={`selector-trigger ${selected ? "has-value" : ""} ${open ? "open" : ""}`}
      >
        {selected ? (
          <span className="flex items-center gap-2 truncate">
            <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded text-[8px] font-bold"
              style={{ background: "rgba(167,139,250,0.18)", color: "#c4b5fd" }}>MF</span>
            <span className="truncate text-xs">{selected.name}</span>
          </span>
        ) : (
          <span>Search fund by name…</span>
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
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type 3+ chars — e.g. HDFC Flexi, Mirae…"
              aria-label="Search mutual funds"
              className="dropdown-inner-search"
            />
          </div>

          {query.length < 3 ? (
            <p className="px-3 py-3 text-[11px]" style={{ color: "var(--text-muted)" }}>Type at least 3 characters</p>
          ) : searching ? (
            <p className="px-3 py-3 text-[11px]" style={{ color: "var(--text-muted)" }}>Searching…</p>
          ) : results.length === 0 ? (
            <p className="px-3 py-3 text-[11px]" style={{ color: "var(--text-muted)" }}>No funds found</p>
          ) : (
            <ul className="max-h-60 overflow-y-auto py-1">
              {results.map((scheme) => (
                <li key={scheme.scheme_code}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={selected?.scheme_code === scheme.scheme_code}
                    onClick={() => handleSelect(scheme)}
                    className="dropdown-item flex w-full items-start gap-3 px-3 py-2.5 text-left"
                  >
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded text-[8px] font-bold"
                      style={{ background: "rgba(167,139,250,0.14)", color: "#c4b5fd" }}>MF</span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium leading-snug" style={{ color: "var(--text-primary)" }}>{scheme.name}</p>
                      <p className="mt-0.5 text-[10px]" style={{ color: "var(--text-muted)" }}>Code: {scheme.scheme_code}</p>
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
