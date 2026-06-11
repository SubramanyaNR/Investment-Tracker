"use client";

import { useTheme } from "./ThemeProvider";

const MODES = [
  { key: "dark"  as const, icon: "◐", label: "Dark mode"  },
  { key: "light" as const, icon: "○", label: "Light mode" },
  { key: "mono"  as const, icon: "◉", label: "Mono mode"  },
];

export default function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="theme-switcher" role="group" aria-label="Select colour theme">
      {MODES.map((m) => (
        <button
          key={m.key}
          type="button"
          title={m.label}
          aria-label={m.label}
          aria-pressed={theme === m.key}
          className={`theme-btn ${theme === m.key ? "active" : ""}`}
          onClick={() => setTheme(m.key)}
        >
          {m.icon}
        </button>
      ))}
    </div>
  );
}
