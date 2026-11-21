"use client";

import * as D from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { cn } from "./cn";
import { IconButton } from "./button";

type Props = {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: ReactNode;
  title: string;
  description?: string;
  children?: ReactNode;
};

/* Radix Dialog gives the focus trap, Escape, aria-modal and focus return to the trigger. */
function Sheet({
  position,
  trigger,
  title,
  description,
  children,
  ...root
}: Props & { position: "center" | "right" | "bottom" }) {
  return (
    <D.Root {...root}>
      {trigger && <D.Trigger asChild>{trigger}</D.Trigger>}
      <D.Portal>
        <D.Overlay className="bg-ink/50 anim-fade fixed inset-0 z-(--z-overlay)" />
        <D.Content
          className={cn(
            "bg-card text-ink shadow-lift border-rule fixed z-(--z-modal) flex flex-col gap-4 border p-6",
            position === "center" &&
              "anim-pop top-1/2 left-1/2 max-h-[90dvh] w-[min(32rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-lg",
            position === "right" &&
              "anim-slide-right inset-y-0 right-0 w-[min(26rem,100vw)] overflow-auto rounded-l-lg",
            position === "bottom" &&
              "anim-slide-up inset-x-0 bottom-0 max-h-[85dvh] overflow-auto rounded-t-lg",
          )}
        >
          <div className="flex items-start justify-between gap-4">
            <D.Title className="font-display text-step-2">{title}</D.Title>
            <D.Close asChild>
              <IconButton label="Close" icon="close" />
            </D.Close>
          </div>
          {description ? (
            <D.Description className="text-muted">{description}</D.Description>
          ) : (
            <D.Description className="sr-only">{title}</D.Description>
          )}
          {children}
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}

export const Modal = (p: Props) => <Sheet position="center" {...p} />;

/** Side drawer on wide screens, bottom sheet on phones. */
export function Drawer(p: Props & { side?: "right" | "bottom" }) {
  const { side = "right", ...rest } = p;
  return <Sheet position={side} {...rest} />;
}
