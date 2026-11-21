"use client";

import { useState } from "react";
import { CardList, NothingYet } from "@/components/cards/item-card";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input, Select } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { Switch } from "@/components/ui/toggles";
import { useBookmarks, useListItems } from "@/lib/api/cards";
import { errorInfo } from "@/lib/api/client";
import { useListActions, useReadingLists, type ReadingList } from "@/lib/api/lists";

const shareUrl = (token: string) => `${window.location.origin}/lists/${token}`;

function ListPanel({ list, onClose }: { list: ReadingList; onClose: () => void }) {
  const toast = useToast();
  const { rename, remove, removeItem, share } = useListActions();
  const items = useListItems(list.id);
  const [name, setName] = useState(list.name);
  const [confirm, setConfirm] = useState(false);
  const fail = (e: Error) =>
    toast({ title: "Could not do that", description: e.message, tone: "danger" });

  return (
    <section aria-labelledby={`l-${list.id}`} className="mt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id={`l-${list.id}`} className="font-display text-step-2">
          {list.name}
        </h2>
        <Button variant="ghost" onClick={onClose}>
          Back to lists
        </Button>
      </div>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <Input label="Name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
        <Button
          variant="secondary"
          loading={rename.isPending}
          disabled={!name.trim() || name.trim() === list.name}
          onClick={() => rename.mutate({ id: list.id, name: name.trim() }, { onError: fail })}
        >
          Rename
        </Button>
        <Modal
          open={confirm}
          onOpenChange={setConfirm}
          trigger={<Button variant="danger">Delete list</Button>}
          title="Delete this list?"
          description="The items stay in the catalogue; only the list goes. Shared links stop working."
        >
          <Button
            variant="danger"
            loading={remove.isPending}
            onClick={() =>
              remove.mutate(list.id, {
                onSuccess: () => {
                  setConfirm(false);
                  onClose();
                },
                onError: fail,
              })
            }
          >
            Delete {list.name}
          </Button>
        </Modal>
      </div>
      <div className="mt-4">
        <Switch
          label="Anyone with the link can read this list"
          checked={Boolean(list.share_token)}
          disabled={share.isPending}
          onCheckedChange={(on) =>
            share.mutate({ id: list.id, on: Boolean(on) }, { onError: fail })
          }
        />
        {list.share_token && (
          <div className="mt-2 flex flex-wrap items-end gap-3">
            <Input
              label="Share link"
              readOnly
              value={shareUrl(list.share_token)}
              className="min-w-64"
            />
            <Button
              variant="secondary"
              onClick={() =>
                navigator.clipboard
                  ?.writeText(shareUrl(list.share_token!))
                  .then(() => toast({ title: "Link copied", tone: "success" }))
                  .catch(() => toast({ title: "Copy it by hand", tone: "danger" }))
              }
            >
              Copy link
            </Button>
          </div>
        )}
      </div>
      <div className="mt-6">
        <CardList
          query={items}
          empty={<NothingYet title="An empty list">Add items from your saved tab.</NothingYet>}
          renderFooter={(i) => (
            <Button
              variant="ghost"
              onClick={() => removeItem.mutate({ id: list.id, itemId: i.id }, { onError: fail })}
            >
              Remove from list
              <span className="sr-only"> {i.title}</span>
            </Button>
          )}
        />
      </div>
    </section>
  );
}

function Lists() {
  const toast = useToast();
  const lists = useReadingLists();
  const { create } = useListActions();
  const [name, setName] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const open = lists.data?.find((l) => l.id === openId);

  if (open) return <ListPanel list={open} onClose={() => setOpenId(null)} />;
  return (
    <section aria-label="Reading lists" className="mt-4">
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          create.mutate(name.trim(), {
            onSuccess: () => setName(""),
            onError: (err) =>
              toast({ title: "Could not create it", description: err.message, tone: "danger" }),
          });
        }}
      >
        <Input
          label="New list"
          hint="Private until you share it."
          value={name}
          maxLength={80}
          onChange={(e) => setName(e.target.value)}
        />
        <Button type="submit" loading={create.isPending} disabled={!name.trim()}>
          Create list
        </Button>
      </form>
      <div className="mt-6" aria-live="polite">
        {lists.isPending ? (
          <Skeleton lines={3} />
        ) : lists.isError ? (
          <Callout tone="danger" title="The shelves are stuck">
            <p>{errorInfo(lists.error).message}</p>
            <Button className="mt-3" variant="secondary" onClick={() => lists.refetch()}>
              Try again
            </Button>
          </Callout>
        ) : lists.data.length === 0 ? (
          <NothingYet title="No lists yet">
            Group what you are reading for an exam, a project or a friend.
          </NothingYet>
        ) : (
          <ul className="flex flex-col gap-3">
            {lists.data.map((l) => (
              <li
                key={l.id}
                className="bg-card shadow-paper border-rule flex flex-wrap items-center justify-between gap-3 rounded-md border p-4"
              >
                <div>
                  <p className="font-display text-step-1">{l.name}</p>
                  <p className="text-step--1 text-muted font-mono tabular-nums">
                    {l.item_count} {l.item_count === 1 ? "item" : "items"} ·{" "}
                    {l.share_token ? "shared by link" : "private"}
                  </p>
                </div>
                <Button variant="secondary" onClick={() => setOpenId(l.id)}>
                  Open
                  <span className="sr-only"> {l.name}</span>
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function Saved() {
  const toast = useToast();
  const saved = useBookmarks();
  const lists = useReadingLists();
  const { addItem } = useListActions();
  return (
    <div className="mt-6">
      <CardList
        query={saved}
        errorTitle="The bookmarks fell out"
        empty={
          <NothingYet title="Nothing saved">Tap the ribbon on anything worth keeping.</NothingYet>
        }
        renderFooter={(i) =>
          lists.data && lists.data.length > 0 ? (
            <Select
              label={`Add to a list`}
              value=""
              onChange={(e) => {
                const id = e.target.value;
                if (id)
                  addItem.mutate(
                    { id, itemId: i.id },
                    {
                      onSuccess: () => toast({ title: "Added to list", tone: "success" }),
                      onError: (err) =>
                        toast({ title: "Not added", description: err.message, tone: "danger" }),
                    },
                  );
              }}
            >
              <option value="">Choose a list</option>
              {lists.data.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </Select>
          ) : null
        }
      />
    </div>
  );
}

export function BookmarksView() {
  const [tab, setTab] = useState<"saved" | "lists">("saved");
  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <h1 className="font-display text-step-4">Your shelf</h1>
      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)} className="mt-6">
        <TabsList aria-label="Shelf">
          <TabsTrigger tint="collection" value="saved">
            Saved
          </TabsTrigger>
          <TabsTrigger tint="collection" value="lists">
            Reading lists
          </TabsTrigger>
        </TabsList>
      </Tabs>
      {tab === "saved" ? <Saved /> : <Lists />}
    </main>
  );
}
