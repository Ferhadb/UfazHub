"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/icons";
import { useUnreadCount } from "@/lib/api/notifications";

/** Header bell; a flame dot marks unread notifications (the count is spoken, not only coloured). */
export function NotificationBell() {
  const { data = 0 } = useUnreadCount();
  return (
    <Link
      href="/notifications"
      aria-label={data > 0 ? `Notifications, ${data} unread` : "Notifications"}
      className="relative inline-flex min-h-11 min-w-11 items-center justify-center"
    >
      <Icon name="bell" />
      {data > 0 && (
        <span
          aria-hidden="true"
          className="bg-flame absolute end-2 top-2 size-2.5 rounded-full ring-2 ring-[var(--paper)]"
        />
      )}
    </Link>
  );
}
