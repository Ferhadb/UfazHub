import { useId, type ComponentProps, type ReactNode } from "react";
import { cn } from "./cn";

type FieldProps = { label: string; hint?: string; error?: string };

const control =
  "min-h-11 w-full rounded-md border border-ink/40 bg-card px-3 py-2 text-step-0 text-ink placeholder:text-muted aria-[invalid=true]:border-danger aria-[invalid=true]:border-2 disabled:opacity-50";

function Shell({
  id,
  label,
  hint,
  error,
  children,
}: FieldProps & { id: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-step--1 text-ink font-mono tracking-wide uppercase">
        {label}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-desc`} className="text-step--1 text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-desc`} role="alert" className="text-step--1 text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

const aria = (id: string, p: FieldProps) => ({
  id,
  "aria-invalid": p.error ? true : undefined,
  "aria-describedby": p.hint || p.error ? `${id}-desc` : undefined,
});

export function Input({
  label,
  hint,
  error,
  className,
  ...rest
}: FieldProps & ComponentProps<"input">) {
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error}>
      <input {...aria(id, { label, hint, error })} className={cn(control, className)} {...rest} />
    </Shell>
  );
}

export function Textarea({
  label,
  hint,
  error,
  className,
  rows = 4,
  ...rest
}: FieldProps & ComponentProps<"textarea">) {
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error}>
      <textarea
        {...aria(id, { label, hint, error })}
        rows={rows}
        className={cn(control, "resize-y", className)}
        {...rest}
      />
    </Shell>
  );
}

/** Native select: the best mobile picker and fully keyboard/screen-reader accessible for free. */
export function Select({
  label,
  hint,
  error,
  className,
  children,
  ...rest
}: FieldProps & ComponentProps<"select">) {
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error}>
      <select {...aria(id, { label, hint, error })} className={cn(control, className)} {...rest}>
        {children}
      </select>
    </Shell>
  );
}
