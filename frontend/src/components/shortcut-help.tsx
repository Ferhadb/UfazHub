"use client";

import { useEffect, useState } from "react";
import { Modal } from "@/components/ui/modal";

const sequence = [
  "ArrowUp",
  "ArrowUp",
  "ArrowDown",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "ArrowLeft",
  "ArrowRight",
  "b",
  "a",
];

export function ShortcutHelp() {
  const [open, setOpen] = useState(false);
  const [secret, setSecret] = useState(false);
  useEffect(() => {
    let index = 0;
    const keydown = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
      )
        return;
      if (event.key === "?" && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        setOpen(true);
      }
      index = event.key === sequence[index] ? index + 1 : event.key === sequence[0] ? 1 : 0;
      if (index === sequence.length) {
        index = 0;
        setSecret(true);
      }
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, []);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Keyboard shortcuts"
        aria-keyshortcuts="?"
        className="text-muted hover:bg-ink/5 inline-flex min-h-11 min-w-11 items-center justify-center rounded-md font-mono"
      >
        ?
      </button>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Keys to the catalogue"
        description="A few shortcuts for a faster visit."
      >
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3">
          <dt className="font-mono">⌘ / Ctrl + K</dt>
          <dd>Search the archive</dd>
          <dt className="font-mono">?</dt>
          <dd>Open this guide</dd>
          <dt className="font-mono">Esc</dt>
          <dd>Close a drawer</dd>
        </dl>
      </Modal>
      {secret && (
        <div
          role="status"
          className="bg-highlighter text-on-highlighter shadow-lift fixed right-4 bottom-4 z-(--z-toast) rounded-md px-5 py-3"
          onClick={() => setSecret(false)}
        >
          Secret shelf unlocked. Happy reading.
        </div>
      )}
    </>
  );
}
