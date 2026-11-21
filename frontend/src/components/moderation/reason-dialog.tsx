"use client";

import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Textarea } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";

/** A dialog that asks for a written reason (or note, or message) before doing something. */
export function ReasonDialog({
  open,
  onOpenChange,
  title,
  description,
  label = "Reason",
  minLength = 3,
  maxLength = 500,
  confirmLabel,
  danger,
  children,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  label?: string;
  minLength?: number;
  maxLength?: number;
  confirmLabel: string;
  danger?: boolean;
  children?: ReactNode;
  onConfirm: (text: string) => Promise<unknown>;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const tooShort = text.trim().length < minLength;

  const submit = async () => {
    setBusy(true);
    setProblem(null);
    try {
      await onConfirm(text.trim());
      setText("");
      onOpenChange(false);
    } catch (e) {
      setProblem(e instanceof Error ? e.message : "That did not go through.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={title} description={description}>
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!tooShort) void submit();
        }}
      >
        {problem && <Callout tone="danger">{problem}</Callout>}
        {children}
        <Textarea
          label={label}
          value={text}
          maxLength={maxLength}
          hint={minLength > 0 ? `At least ${minLength} characters.` : undefined}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant={danger ? "danger" : "primary"}
            loading={busy}
            disabled={tooShort}
          >
            {confirmLabel}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
