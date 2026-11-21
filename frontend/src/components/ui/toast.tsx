"use client";

import * as T from "@radix-ui/react-toast";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { cn } from "./cn";
import { IconButton } from "./button";

type Tone = "info" | "success" | "danger";
type ToastItem = { id: number; title: string; description?: string; tone: Tone };
type Push = (t: { title: string; description?: string; tone?: Tone }) => void;

const Ctx = createContext<Push | null>(null);
const tones: Record<Tone, string> = {
  info: "border-l-accent",
  success: "border-l-success",
  danger: "border-l-danger",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback<Push>(
    (t) => setItems((all) => [...all, { id: Date.now() + all.length, tone: "info", ...t }]),
    [],
  );
  return (
    <Ctx.Provider value={push}>
      <T.Provider swipeDirection="right" duration={5000} label="Notifications">
        {children}
        {items.map((t) => (
          <T.Root
            key={t.id}
            type={t.tone === "danger" ? "foreground" : "background"}
            onOpenChange={(open) => !open && setItems((all) => all.filter((x) => x.id !== t.id))}
            className={cn(
              "bg-card text-ink shadow-lift border-rule anim-pop flex items-start gap-3 rounded-md border border-l-4 p-3",
              tones[t.tone],
            )}
          >
            <div className="flex-1">
              <T.Title className="font-semibold">{t.title}</T.Title>
              {t.description && (
                <T.Description className="text-muted text-step--1">{t.description}</T.Description>
              )}
            </div>
            <T.Close asChild>
              <IconButton label="Dismiss" icon="close" />
            </T.Close>
          </T.Root>
        ))}
        <T.Viewport className="fixed right-0 bottom-0 z-(--z-toast) m-0 flex w-[min(24rem,100vw)] list-none flex-col gap-2 p-4 outline-none" />
      </T.Provider>
    </Ctx.Provider>
  );
}

export function useToast(): Push {
  const push = useContext(Ctx);
  if (!push) throw new Error("useToast needs <ToastProvider>");
  return push;
}
