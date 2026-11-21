"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { Checkbox } from "@/components/ui/toggles";
import { api, errorInfo } from "@/lib/api/client";
import { useItemCourses, usePrograms } from "@/lib/api/courses";

/** The courses an item is filed under; its author (or an admin) can change them. */
export function CourseFiling({ itemId, canEdit }: { itemId: string; canEdit: boolean }) {
  const mine = useItemCourses(itemId);
  const programs = usePrograms();
  const qc = useQueryClient();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  const courses = mine.data ?? [];
  if (!canEdit && courses.length === 0) return null;

  const save = async () => {
    setSaving(true);
    const { data, error } = await api.PUT("/api/content/{item_id}/courses", {
      params: { path: { item_id: itemId } },
      body: { course_slugs: [...picked] },
    });
    setSaving(false);
    if (!data) {
      toast({ title: "Not filed", description: errorInfo(error).message, tone: "danger" });
      return;
    }
    qc.setQueryData(["item-courses", itemId], data);
    void qc.invalidateQueries({ queryKey: ["cards", "course"] });
    setOpen(false);
  };

  return (
    <div className="mt-6 flex flex-wrap items-center gap-2">
      <span className="text-step--1 text-muted font-mono tracking-widest uppercase">
        Filed under
      </span>
      {courses.length === 0 && <span className="text-muted">no course yet</span>}
      {courses.map((c) => (
        <Link
          key={c.slug}
          href={`/courses/${c.slug}`}
          className="inline-flex min-h-11 items-center"
        >
          <Badge tone="resource">
            {c.name} {c.level}
          </Badge>
        </Link>
      ))}
      {canEdit && (
        <Modal
          open={open}
          onOpenChange={(o) => {
            if (o) setPicked(new Set(courses.map((c) => c.slug)));
            setOpen(o);
          }}
          trigger={<Button variant="secondary">File under a course</Button>}
          title="File under a course"
          description="Pick up to five courses."
        >
          <div className="flex flex-col">
            {(programs.data ?? []).flatMap((p) =>
              p.courses.map((c) => (
                <Checkbox
                  key={c.slug}
                  label={`${c.name} ${c.level} (${p.name})`}
                  checked={picked.has(c.slug)}
                  disabled={!picked.has(c.slug) && picked.size >= 5}
                  onCheckedChange={(v) =>
                    setPicked((s) => {
                      const next = new Set(s);
                      if (v) next.add(c.slug);
                      else next.delete(c.slug);
                      return next;
                    })
                  }
                />
              )),
            )}
          </div>
          <Button onClick={save} loading={saving}>
            Save
          </Button>
        </Modal>
      )}
    </div>
  );
}
