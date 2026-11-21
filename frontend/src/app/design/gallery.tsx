"use client";

import { useState, type ReactNode } from "react";
import {
  Avatar,
  Badge,
  Button,
  Callout,
  Card,
  Checkbox,
  Combobox,
  Compass,
  Drawer,
  EmptyDrawer,
  EmptyState,
  Footprints,
  Icon,
  IconButton,
  Inkwell,
  Input,
  LostCard,
  Marginalia,
  Modal,
  Ornament,
  OrnamentDivider,
  Pagination,
  Select,
  Skeleton,
  Stamp,
  Switch,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
  Tooltip,
  iconNames,
  ornamentVariants,
  useToast,
} from "@/components/ui";

/* Every specimen is rendered twice, once per theme, using the scoped [data-theme-preview] tokens.
 * Portalled layers (modal, drawer, toast, tooltip) follow the page theme, not the preview. */
function Specimen({
  id,
  title,
  note,
  children,
}: {
  id: string;
  title: string;
  note?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-20">
      <h2 id={`${id}-h`} className="font-display text-step-3">
        {title}
      </h2>
      {note && <p className="text-muted mt-1 max-w-2xl">{note}</p>}
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {(["light", "dark"] as const).map((theme) => (
          <div
            key={theme}
            data-theme-preview={theme}
            className="bg-paper text-ink border-rule relative rounded-lg border p-5"
          >
            <p className="text-step--1 text-muted mb-4 font-mono tracking-widest uppercase">
              {theme}
            </p>
            <div className="flex flex-col gap-4">{children}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

const sections = [
  ["buttons", "Buttons"],
  ["fields", "Fields"],
  ["choices", "Checkbox and switch"],
  ["overlays", "Modal, drawer, toast"],
  ["tabs", "Tabs"],
  ["labels", "Badge, stamp, avatar"],
  ["cards", "Card"],
  ["notes", "Callout and marginalia"],
  ["states", "Skeleton and empty state"],
  ["paging", "Pagination"],
  ["icons", "Icons"],
  ["ornaments", "Ornaments"],
  ["art", "Illustrations"],
] as const;

const courses = [
  { value: "algo", label: "Algorithms L2" },
  { value: "analysis", label: "Analysis L1" },
  { value: "thermo", label: "Thermodynamics M1" },
  { value: "geo", label: "Géométrie différentielle" },
  { value: "ceb", label: "Çoxdəyişənli analiz" },
];

function ComboDemo() {
  const [v, setV] = useState<string | null>(null);
  return (
    <Combobox
      label="Course"
      options={courses}
      value={v}
      onChange={setV}
      placeholder="Type to search"
    />
  );
}

function ToastDemo() {
  const toast = useToast();
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        variant="secondary"
        onClick={() => toast({ title: "Saved to your shelf", tone: "success" })}
      >
        Success toast
      </Button>
      <Button
        variant="secondary"
        onClick={() =>
          toast({ title: "Could not save", description: "Try again in a moment.", tone: "danger" })
        }
      >
        Error toast
      </Button>
    </div>
  );
}

function PagingDemo() {
  const [page, setPage] = useState(1);
  return (
    <>
      <p className="num">Page {page} of the drawer</p>
      <Pagination
        hasPrev={page > 1}
        hasNext={page < 3}
        onPrev={() => setPage(page - 1)}
        onNext={() => setPage(page + 1)}
      />
    </>
  );
}

export function DesignGallery() {
  return (
    <main
      id="main"
      className="relative z-10 mx-auto grid max-w-7xl gap-10 px-4 py-10 sm:px-8 lg:grid-cols-[12rem_1fr]"
    >
      <nav aria-label="Design system sections" className="hidden lg:block">
        <ul className="sticky top-6 flex flex-col gap-1">
          {sections.map(([id, label], i) => (
            <li key={id}>
              <a
                href={`#${id}`}
                className="text-step--1 text-muted hover:text-ink flex min-h-11 items-center gap-2 font-mono"
              >
                <span className="num text-flame-text">{String(i + 1).padStart(2, "0")}</span>
                {label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex min-w-0 flex-col gap-14">
        <header>
          <p className="text-step--1 text-muted font-mono tracking-widest uppercase">
            The Living Archive
          </p>
          <h1 className="font-display text-step-5">Design system</h1>
          <p className="text-step-1 text-muted mt-3 max-w-2xl">
            22 primitives, a hand-drawn icon set and original geometric ornaments. Each specimen is
            shown on paper and in the night reading room.
          </p>
        </header>

        <Specimen
          id="buttons"
          title="Buttons"
          note="44px minimum target, accent focus ring. IconButton needs a label: it becomes the tooltip."
        >
          <div className="flex flex-wrap gap-2">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Delete</Button>
            <Button disabled>Disabled</Button>
            <Button loading>Saving</Button>
          </div>
          <div className="flex gap-2">
            <IconButton label="Bookmark" icon="bookmark" variant="secondary" />
            <IconButton label="Search" icon="search" variant="secondary" />
            <IconButton label="Report" icon="flag" />
          </div>
        </Specimen>

        <Specimen
          id="fields"
          title="Fields"
          note="Label, hint and error are wired with aria-describedby. Select is the native element on purpose."
        >
          <Input
            label="Title"
            placeholder="Linear algebra, cheat sheet"
            hint="Shown on the card."
          />
          <Input label="Link" defaultValue="not a url" error="That does not look like a link." />
          <Textarea label="Why it helped" />
          <Select label="Difficulty" defaultValue="med">
            <option value="easy">Gentle</option>
            <option value="med">Medium</option>
            <option value="hard">Steep</option>
          </Select>
          <ComboDemo />
        </Specimen>

        <Specimen id="choices" title="Checkbox and switch">
          <Checkbox label="I read it end to end" />
          <Checkbox label="Checked by default" defaultChecked />
          <Switch label="Email me replies" />
          <Switch label="Weekly digest" defaultChecked />
        </Specimen>

        <Specimen
          id="overlays"
          title="Modal, drawer, toast"
          note="Focus is trapped and returned to the trigger; Escape closes. Layers use the page theme."
        >
          <div className="flex flex-wrap gap-2">
            <Modal
              title="Report this resource"
              description="Tell the editors what is wrong."
              trigger={<Button variant="secondary">Open modal</Button>}
            >
              <Textarea label="What happened?" />
              <Button>Send report</Button>
            </Modal>
            <Drawer title="Filters" trigger={<Button variant="secondary">Open drawer</Button>}>
              <Checkbox label="Only verified" />
              <Checkbox label="Has attachments" />
            </Drawer>
          </div>
          <ToastDemo />
        </Specimen>

        <Specimen
          id="tabs"
          title="Tabs"
          note="Index-card tabs, tinted by content type. Arrow keys move between tabs."
        >
          <Tabs defaultValue="res">
            <TabsList aria-label="Content types">
              <TabsTrigger value="res" tint="resource">
                Resources
              </TabsTrigger>
              <TabsTrigger value="art" tint="article">
                Articles
              </TabsTrigger>
              <TabsTrigger value="col" tint="collection">
                Shelves
              </TabsTrigger>
              <TabsTrigger value="q" tint="question">
                Questions
              </TabsTrigger>
            </TabsList>
            <TabsContent value="res">Teal tab: lecture notes, links, files.</TabsContent>
            <TabsContent value="art">Vermilion tab: long reads.</TabsContent>
            <TabsContent value="col">Ochre tab: curated shelves.</TabsContent>
            <TabsContent value="q">Plum tab: questions and answers.</TabsContent>
          </Tabs>
        </Specimen>

        <Specimen id="labels" title="Badge, stamp, avatar">
          <div className="flex flex-wrap gap-2">
            <Badge>Neutral</Badge>
            <Badge tone="resource">Resource</Badge>
            <Badge tone="article">Article</Badge>
            <Badge tone="collection">Collection</Badge>
            <Badge tone="question">Question</Badge>
            <Badge tone="research">Research</Badge>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <Stamp>New</Stamp>
            <Stamp tone="resource" tilt={-3}>
              Verified
            </Stamp>
            <Stamp tone="collection" tilt={2}>
              Editor&rsquo;s pick
            </Stamp>
            <Stamp tone="neutral" tilt={-2}>
              Dead link
            </Stamp>
          </div>
          <div className="flex items-center gap-3">
            <Avatar name="Aygün Həsənova" />
            <Avatar name="Émile Zola" />
            <Avatar name="Ёлка Щукина" />
            <Avatar name="Nigar" size={56} />
          </div>
        </Specimen>

        <Specimen
          id="cards"
          title="Card"
          note="Catalogue card. Hover or focus: it lifts and straightens."
        >
          <Card
            callNumber="RES-0421"
            tint="resource"
            title="Əlgəbr və həndəsə: konspekt"
            href="#cards"
            stamp={<Stamp>New</Stamp>}
          >
            Linear algebra notes in Azerbaijani, with worked exercises.
          </Card>
          <Card
            callNumber="ART-0087"
            tint="article"
            title="Surviving the January exam week"
            tilt={0.8}
            href="#cards"
          >
            A field guide, written the night before.
          </Card>
          <Card
            callNumber="QST-0112"
            tint="question"
            title="Which proof technique for convergence?"
            tilt={-0.4}
          />
        </Specimen>

        <Specimen
          id="notes"
          title="Callout and marginalia"
          note="Marginalia is the only place the script face appears."
        >
          <Callout title="Heads up">Plain information, set like a margin note.</Callout>
          <Callout tone="success">Saved to your shelf.</Callout>
          <Callout tone="warning">This link may be dead.</Callout>
          <Callout tone="danger" title="Could not publish">
            Fix the highlighted fields.
          </Callout>
          <div className="relative">
            <p>
              The proof only works when the sequence is bounded, which the textbook forgets to say.
            </p>
            <Marginalia>exam tip: they always ask this one!</Marginalia>
          </div>
        </Specimen>

        <Specimen id="states" title="Skeleton and empty state">
          <Skeleton />
          <EmptyState
            title="Nothing here yet"
            action={<Button variant="secondary">Leave a footprint</Button>}
          >
            Be the first to leave a footprint.
          </EmptyState>
        </Specimen>

        <Specimen
          id="paging"
          title="Pagination"
          note="Cursor based: previous and next only. No page numbers, no unbounded lists."
        >
          <PagingDemo />
        </Specimen>

        <Specimen
          id="icons"
          title="Icons"
          note="Hand-drawn 24px set. Decorative unless given a title."
        >
          <ul className="grid grid-cols-4 gap-3 sm:grid-cols-6">
            {iconNames.map((n) => (
              <li key={n} className="flex flex-col items-center gap-1">
                <Tooltip content={n}>
                  <span
                    tabIndex={0}
                    className="border-rule grid size-11 place-items-center rounded-md border"
                  >
                    <Icon name={n} size={24} title={n} />
                  </span>
                </Tooltip>
              </li>
            ))}
          </ul>
        </Specimen>

        <Specimen
          id="ornaments"
          title="Ornaments"
          note="Original geometric patterns for dividers, empty states and backgrounds at 4 to 8% opacity."
        >
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {ornamentVariants.map((v) => (
              <figure key={v}>
                <div className="border-rule h-24 rounded-md border">
                  <Ornament variant={v} strength={0.35} />
                </div>
                <figcaption className="text-step--1 text-muted font-mono">{v}</figcaption>
              </figure>
            ))}
          </div>
          <OrnamentDivider />
        </Specimen>

        <Specimen
          id="art"
          title="Illustrations"
          note="Loose line art for empty, 404 and error states."
        >
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {[EmptyDrawer, Footprints, LostCard, Inkwell, Compass].map((Art, i) => (
              <Art key={i} className="size-full max-w-40" />
            ))}
          </div>
        </Specimen>
      </div>
    </main>
  );
}
