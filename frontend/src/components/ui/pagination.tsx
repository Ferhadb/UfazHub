import { Button } from "./button";
import { Icon } from "./icons";

/* Cursor pagination: the API gives `next_cursor` only, so there are no page numbers or "last". */
export function Pagination({
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  loading,
  label = "Pagination",
}: {
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  loading?: boolean;
  label?: string;
}) {
  return (
    <nav aria-label={label} className="flex items-center justify-between gap-3">
      <Button variant="secondary" onClick={onPrev} disabled={!hasPrev || loading}>
        <Icon name="chevron-left" /> Previous
      </Button>
      <Button variant="secondary" onClick={onNext} disabled={!hasNext} loading={loading}>
        Next <Icon name="chevron-right" />
      </Button>
    </nav>
  );
}
