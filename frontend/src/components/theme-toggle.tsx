"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icons";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const root = document.documentElement;
    const preference = window.matchMedia("(prefers-color-scheme: dark)");
    const sync = () =>
      setDark(root.dataset.theme === "dark" || (!root.dataset.theme && preference.matches));
    sync();
    preference.addEventListener("change", sync);
    return () => preference.removeEventListener("change", sync);
  }, []);
  const toggle = () => {
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("theme", next);
    setDark(!dark);
  };
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${dark ? "light" : "dark"} theme`}
      aria-pressed={dark}
      className="text-ink hover:bg-ink/5 inline-flex min-h-11 min-w-11 items-center justify-center rounded-md"
    >
      <Icon name={dark ? "sun" : "moon"} />
    </button>
  );
}
