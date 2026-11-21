"use client";

import { useState } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useResearch, type CardType } from "@/lib/api/cards";
import { CardList, NothingYet } from "./item-card";

const FILTERS = ["all", "resource", "article", "collection", "question"] as const;

export function ResearchView() {
  const [type, setType] = useState<(typeof FILTERS)[number]>("all");
  const q = useResearch(type === "all" ? undefined : (type as CardType));
  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <p className="text-step--1 text-research font-mono tracking-widest uppercase">
        Catalogue · Research
      </p>
      <h1 className="font-display text-step-4 mt-1">The reading room</h1>
      <p className="text-muted mt-2 max-w-prose">
        Papers, surveys and student research, whatever shape they take. Authors flag their own work
        as research; it stays on its original shelf too.
      </p>
      <Tabs value={type} onValueChange={(v) => setType(v as typeof type)} className="mt-6">
        <TabsList aria-label="Type">
          {FILTERS.map((f) => (
            <TabsTrigger key={f} tint="research" value={f}>
              {f === "all" ? "All" : f[0]!.toUpperCase() + f.slice(1) + "s"}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="mt-6">
        <CardList
          query={q}
          errorTitle="The reading room is closed"
          empty={
            <NothingYet>No research filed here yet. Be the first to leave a footprint.</NothingYet>
          }
        />
      </div>
    </main>
  );
}
