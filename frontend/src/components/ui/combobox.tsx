"use client";

import { useId, useMemo, useState } from "react";
import { cn } from "./cn";

export type ComboOption = { value: string; label: string };

/* ARIA 1.2 editable combobox with list autocomplete: focus stays in the input,
 * the active option is announced via aria-activedescendant. */
export function Combobox({
  label,
  options,
  value,
  onChange,
  placeholder,
  emptyText = "Nothing matches that.",
}: {
  label: string;
  options: ComboOption[];
  value: string | null;
  onChange: (value: string | null) => void;
  placeholder?: string;
  emptyText?: string;
}) {
  const id = useId();
  const selected = options.find((o) => o.value === value);
  const [text, setText] = useState(selected?.label ?? "");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const shown = useMemo(() => {
    const q = text.trim().toLowerCase();
    return !q || q === selected?.label.toLowerCase()
      ? options
      : options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, text, selected]);

  const choose = (o: ComboOption) => {
    onChange(o.value);
    setText(o.label);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) return setOpen(true);
      const n = shown.length || 1;
      setActive((a) => (a + (e.key === "ArrowDown" ? 1 : n - 1)) % n);
    } else if (e.key === "Enter" && open && shown[active]) {
      e.preventDefault();
      choose(shown[active]);
    } else if (e.key === "Escape" && open) {
      e.stopPropagation();
      setOpen(false);
      setText(selected?.label ?? "");
    }
  };

  return (
    <div className="relative flex flex-col gap-1.5">
      <label htmlFor={id} className="text-step--1 text-ink font-mono tracking-wide uppercase">
        {label}
      </label>
      <input
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-autocomplete="list"
        aria-activedescendant={open && shown[active] ? `${id}-o${active}` : undefined}
        autoComplete="off"
        placeholder={placeholder}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setActive(0);
          setOpen(true);
          if (!e.target.value) onChange(null);
        }}
        onKeyDown={onKeyDown}
        onBlur={() => {
          setOpen(false);
          setText(selected?.label ?? "");
        }}
        className="border-ink/40 bg-card text-step-0 text-ink placeholder:text-muted min-h-11 w-full rounded-md border px-3 py-2"
      />
      <ul
        id={`${id}-list`}
        role="listbox"
        aria-label={label}
        hidden={!open}
        className="bg-card shadow-lift border-rule anim-pop absolute top-full z-(--z-overlay) mt-1 max-h-60 w-full overflow-auto rounded-md border py-1"
      >
        {shown.length === 0 && <li className="text-muted px-3 py-2">{emptyText}</li>}
        {shown.map((o, i) => (
          <li
            key={o.value}
            id={`${id}-o${i}`}
            role="option"
            aria-selected={o.value === value}
            // mousedown beats the input's blur, so the click still lands
            onMouseDown={(e) => {
              e.preventDefault();
              choose(o);
            }}
            className={cn(
              "min-h-11 cursor-pointer px-3 py-2.5",
              i === active && "bg-accent text-accent-fg",
              o.value === value && i !== active && "font-semibold",
            )}
          >
            {o.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
