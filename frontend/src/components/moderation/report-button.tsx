"use client";

import { useState } from "react";
import { IconButton } from "@/components/ui/button";
import { Select } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { REPORT_REASONS, useReport, type ReportReason } from "@/lib/api/moderation";
import { useSession } from "@/lib/auth/use-session";
import { ReasonDialog } from "./reason-dialog";

/** Flag button for any content item. Hidden for guests and for the item's own author. */
export function ReportButton({ itemId, authorId }: { itemId: string; authorId: string }) {
  const { user, status } = useSession();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<ReportReason>("spam");
  const report = useReport(itemId);
  const toast = useToast();
  if (status !== "authenticated" || !user || user.id === authorId) return null;

  return (
    <>
      <IconButton label="Report" icon="flag" onClick={() => setOpen(true)} />
      <ReasonDialog
        open={open}
        onOpenChange={setOpen}
        title="Report this post"
        description="A moderator will take a look. The author is not told who reported."
        label="Note (optional)"
        minLength={0}
        maxLength={1000}
        confirmLabel="Send report"
        onConfirm={async (note) => {
          await report.mutateAsync({ reason, note });
          toast({ title: "Report sent", description: "Thank you.", tone: "success" });
        }}
      >
        <Select
          label="What is wrong?"
          value={reason}
          onChange={(e) => setReason(e.target.value as ReportReason)}
        >
          {REPORT_REASONS.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </Select>
      </ReasonDialog>
    </>
  );
}
