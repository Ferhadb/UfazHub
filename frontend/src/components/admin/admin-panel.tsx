"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSession } from "@/lib/auth/use-session";
import { AppealsTab } from "./appeals-tab";
import { AuditTab } from "./audit-tab";
import { QueueTab } from "./queue-tab";
import { UsersTab } from "./users-tab";

/** Middleware bounces signed-out visitors; this checks the role the server reported. The API enforces it again. */
export function AdminPanel() {
  const router = useRouter();
  const { user, status } = useSession();

  useEffect(() => {
    if (status === "anonymous") router.replace("/signin?next=/admin");
  }, [status, router]);

  if (!user)
    return (
      <Shell>
        <Skeleton />
      </Shell>
    );
  if (user.role !== "admin")
    return (
      <Shell>
        <EmptyState title="Admins only">This desk is not open to the public.</EmptyState>
      </Shell>
    );

  return (
    <Shell>
      <Tabs defaultValue="queue">
        <TabsList aria-label="Admin sections">
          <TabsTrigger value="queue">Queue</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="appeals">Appeals</TabsTrigger>
          <TabsTrigger value="audit">Audit log</TabsTrigger>
        </TabsList>
        <TabsContent value="queue">
          <QueueTab />
        </TabsContent>
        <TabsContent value="users">
          <UsersTab selfId={user.id} />
        </TabsContent>
        <TabsContent value="appeals">
          <AppealsTab />
        </TabsContent>
        <TabsContent value="audit">
          <AuditTab />
        </TabsContent>
      </Tabs>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main
      id="main"
      className="relative z-10 mx-auto flex max-w-4xl flex-col gap-6 px-4 py-10 sm:px-8"
    >
      <h1 className="font-display text-step-4">Admin</h1>
      {children}
    </main>
  );
}
