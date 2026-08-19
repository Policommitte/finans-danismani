"use client";

import { useEffect, useState } from "react";

type ThemeMode = "light" | "dark";

function getInitialTheme(): ThemeMode {
  if (typeof window === "undefined") {
    return "light";
  }

  const savedTheme = window.localStorage.getItem("app-theme");
  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  const [theme, setTheme] = useState<ThemeMode>("light");

  useEffect(() => {
    setTheme(getInitialTheme());
  }, []);

  function toggleTheme() {
    setTheme((current) => {
      const nextTheme = current === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = nextTheme;
      window.localStorage.setItem("app-theme", nextTheme);
      return nextTheme;
    });
  }

  const isDark = theme === "dark";

  return (
    <button
      type="button"
      aria-label={isDark ? "Aydınlık moda geç" : "Karanlık moda geç"}
      onClick={toggleTheme}
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md border app-border app-surface app-muted transition hover:opacity-80 ${className}`}
    >
      <span className="text-lg leading-none">{isDark ? "☀" : "☾"}</span>
    </button>
  );
}
