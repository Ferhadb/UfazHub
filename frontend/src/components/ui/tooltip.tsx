"use client";

import * as T from "@radix-ui/react-tooltip";
import type { ReactElement } from "react";

export const TooltipProvider = ({ children }: { children: React.ReactNode }) => (
  <T.Provider delayDuration={300}>{children}</T.Provider>
);

/** Shows on hover and keyboard focus; the trigger keeps its own accessible name. */
export function Tooltip({ content, children }: { content: string; children: ReactElement }) {
  return (
    <T.Root>
      <T.Trigger asChild>{children}</T.Trigger>
      <T.Portal>
        <T.Content
          sideOffset={6}
          className="anim-fade bg-ink text-paper text-step--1 z-(--z-tooltip) rounded-sm px-2 py-1 font-mono"
        >
          {content}
          <T.Arrow className="fill-ink" />
        </T.Content>
      </T.Portal>
    </T.Root>
  );
}
