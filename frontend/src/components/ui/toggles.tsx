"use client";

import * as C from "@radix-ui/react-checkbox";
import * as S from "@radix-ui/react-switch";
import { useId, type ComponentProps } from "react";
import { Icon } from "./icons";

const row = "flex min-h-11 items-center gap-3 text-step-0 text-ink";

export function Checkbox({ label, ...rest }: { label: string } & ComponentProps<typeof C.Root>) {
  const id = useId();
  return (
    <div className={row}>
      <C.Root
        id={id}
        className="border-ink bg-card data-[state=checked]:bg-accent data-[state=checked]:text-accent-fg grid size-6 shrink-0 place-items-center rounded-sm border-2"
        {...rest}
      >
        <C.Indicator>
          <Icon name="check" size={16} strokeWidth={3} />
        </C.Indicator>
      </C.Root>
      <label htmlFor={id} className="cursor-pointer py-2">
        {label}
      </label>
    </div>
  );
}

export function Switch({ label, ...rest }: { label: string } & ComponentProps<typeof S.Root>) {
  const id = useId();
  return (
    <div className={row}>
      <S.Root
        id={id}
        className="border-ink bg-card data-[state=checked]:bg-accent relative h-7 w-12 shrink-0 rounded-full border-2"
        {...rest}
      >
        <S.Thumb className="bg-ink data-[state=checked]:bg-accent-fg block size-4 translate-x-1 rounded-full transition-transform duration-(--duration-base) ease-(--ease-spring) data-[state=checked]:translate-x-6" />
      </S.Root>
      <label htmlFor={id} className="cursor-pointer py-2">
        {label}
      </label>
    </div>
  );
}
