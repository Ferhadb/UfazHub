"use client";

import { useCallback, useEffect, useState, type RefObject } from "react";

const key = (id: string) => `ufazhub:reading:${id}`;
const read = (id: string): number => {
  try {
    return Number(localStorage.getItem(key(id))) || 0;
  } catch {
    return 0; // storage can be blocked; reading still works
  }
};

/** Progress through the article (0-1), the heading currently being read, and a resume point. */
export function useReading(
  ref: RefObject<HTMLElement | null>,
  itemId: string,
  headingIds: string[],
) {
  const [progress, setProgress] = useState(0);
  const [active, setActive] = useState<string | null>(null);
  const [resume, setResume] = useState(0);

  useEffect(() => {
    const saved = read(itemId);
    if (saved > 0.05 && saved < 0.95) setResume(saved);
  }, [itemId]);

  useEffect(() => {
    let frame = 0;
    let timer: ReturnType<typeof setTimeout>;
    const update = () => {
      frame = 0;
      const el = ref.current;
      if (!el) return;
      const { top, height } = el.getBoundingClientRect();
      const span = Math.max(height - window.innerHeight, 1);
      const p = Math.min(Math.max(-top / span, 0), 1);
      setProgress(p);
      let current: string | null = null;
      for (const id of headingIds) {
        const h = document.getElementById(id);
        if (h && h.getBoundingClientRect().top <= 120) current = id;
      }
      setActive(current);
      clearTimeout(timer);
      timer = setTimeout(() => {
        try {
          // Remember where you stopped; a finished article forgets its place.
          if (p >= 0.95) localStorage.removeItem(key(itemId));
          else if (p > 0.02) localStorage.setItem(key(itemId), String(p));
        } catch {
          /* private mode: no memory, no problem */
        }
      }, 400);
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(frame);
      clearTimeout(timer);
    };
  }, [ref, itemId, headingIds]);

  const jumpToResume = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const span = Math.max(el.offsetHeight - window.innerHeight, 1);
    window.scrollTo({ top: el.offsetTop + resume * span, behavior: "smooth" });
  }, [ref, resume]);

  return { progress, active, resume, jumpToResume };
}
