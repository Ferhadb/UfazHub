import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import {
  Avatar,
  Badge,
  Button,
  Callout,
  Card,
  Checkbox,
  Combobox,
  Drawer,
  EmptyState,
  IconButton,
  Input,
  Marginalia,
  Modal,
  Pagination,
  Select,
  Skeleton,
  Stamp,
  Textarea,
  Switch,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  TooltipProvider,
  ToastProvider,
  iconNames,
  useToast,
} from "@/components/ui";

const wrap = (ui: React.ReactNode) =>
  render(
    <TooltipProvider>
      <ToastProvider>{ui}</ToastProvider>
    </TooltipProvider>,
  );

describe("Button", () => {
  it("activates with Enter and Space", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    wrap(<Button onClick={onClick}>Save</Button>);
    await user.tab();
    expect(screen.getByRole("button", { name: "Save" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await user.keyboard(" ");
    expect(onClick).toHaveBeenCalledTimes(2);
  });

  it("loading disables the button and says it is busy", async () => {
    const onClick = vi.fn();
    wrap(
      <Button loading onClick={onClick}>
        Save
      </Button>,
    );
    const b = screen.getByRole("button");
    expect(b).toBeDisabled();
    expect(b).toHaveAttribute("aria-busy", "true");
    await userEvent.click(b);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("IconButton is named by its label and shows a tooltip on focus", async () => {
    const user = userEvent.setup();
    wrap(<IconButton label="Bookmark" icon="bookmark" />);
    await user.tab();
    expect(screen.getByRole("button", { name: "Bookmark" })).toHaveFocus();
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Bookmark");
  });
});

describe("fields", () => {
  it("label is associated and errors are announced and linked", () => {
    wrap(<Input label="Email" error="Enter a valid email" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Enter a valid email");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email");
  });

  it("hint becomes the description when there is no error", () => {
    wrap(<Input label="Password" hint="At least 8 characters." />);
    expect(screen.getByLabelText("Password")).toHaveAccessibleDescription("At least 8 characters.");
    expect(screen.getByLabelText("Password")).not.toHaveAttribute("aria-invalid");
  });

  it("Select is a labelled native combobox", async () => {
    const user = userEvent.setup();
    wrap(
      <Select label="Difficulty">
        <option value="a">Gentle</option>
        <option value="b">Steep</option>
      </Select>,
    );
    await user.selectOptions(screen.getByLabelText("Difficulty"), "Steep");
    expect(screen.getByLabelText("Difficulty")).toHaveValue("b");
  });
});

describe("Combobox", () => {
  const options = [
    { value: "algo", label: "Algorithms" },
    { value: "analysis", label: "Analysis" },
    { value: "thermo", label: "Thermodynamics" },
  ];
  function Demo({ onChange }: { onChange: (v: string | null) => void }) {
    const [v, setV] = useState<string | null>(null);
    return (
      <Combobox
        label="Course"
        options={options}
        value={v}
        onChange={(x) => {
          setV(x);
          onChange(x);
        }}
      />
    );
  }

  it("filters, navigates with arrows, selects with Enter, closes with Escape", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    wrap(<Demo onChange={onChange} />);
    const box = screen.getByRole("combobox", { name: "Course" });
    expect(box).toHaveAttribute("aria-expanded", "false");

    await user.type(box, "m");
    expect(box).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Algorithms",
      "Thermodynamics",
    ]);
    await user.keyboard("{ArrowDown}");
    expect(box).toHaveAttribute("aria-activedescendant", screen.getAllByRole("option")[1]!.id);
    await user.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith("thermo");
    expect(box).toHaveValue("Thermodynamics");
    expect(box).toHaveAttribute("aria-expanded", "false");

    await user.clear(box);
    await user.type(box, "al");
    await user.keyboard("{Escape}");
    expect(box).toHaveAttribute("aria-expanded", "false");
  });

  it("says so when nothing matches", async () => {
    const user = userEvent.setup();
    wrap(<Demo onChange={() => {}} />);
    await user.type(screen.getByRole("combobox"), "zzz");
    expect(screen.getByText("Nothing matches that.")).toBeInTheDocument();
  });
});

describe("toggles", () => {
  it("Checkbox toggles with Space and is labelled", async () => {
    const user = userEvent.setup();
    wrap(<Checkbox label="Read it" />);
    const box = screen.getByRole("checkbox", { name: "Read it" });
    await user.tab();
    await user.keyboard(" ");
    expect(box).toBeChecked();
  });

  it("Switch has role switch and toggles with Space", async () => {
    const user = userEvent.setup();
    wrap(<Switch label="Digest" />);
    const sw = screen.getByRole("switch", { name: "Digest" });
    expect(sw).toHaveAttribute("aria-checked", "false");
    await user.tab();
    await user.keyboard(" ");
    expect(sw).toHaveAttribute("aria-checked", "true");
  });
});

describe("Modal", () => {
  it("traps focus, closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    wrap(
      <Modal title="Report" description="Tell us why" trigger={<Button>Open</Button>}>
        <Input label="Reason" />
      </Modal>,
    );
    const trigger = screen.getByRole("button", { name: "Open" });
    await user.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "Report" });
    expect(dialog).toHaveAccessibleDescription("Tell us why");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    await user.tab();
    await user.tab();
    await user.tab();
    expect(dialog).toContainElement(document.activeElement as HTMLElement); // still inside
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });
});

describe("Toast", () => {
  function Trigger() {
    const toast = useToast();
    return (
      <Button onClick={() => toast({ title: "Saved", description: "On your shelf" })}>Go</Button>
    );
  }
  it("announces a toast and lets you dismiss it", async () => {
    const user = userEvent.setup();
    wrap(<Trigger />);
    await user.click(screen.getByRole("button", { name: "Go" }));
    expect(await screen.findByText("On your shelf")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Dismiss" })).toBeNull());
  });
});

describe("Tabs", () => {
  it("exposes tablist semantics and moves with arrow keys", async () => {
    const user = userEvent.setup();
    wrap(
      <Tabs defaultValue="a">
        <TabsList aria-label="Types">
          <TabsTrigger value="a">Resources</TabsTrigger>
          <TabsTrigger value="b" tint="article">
            Articles
          </TabsTrigger>
        </TabsList>
        <TabsContent value="a">First</TabsContent>
        <TabsContent value="b">Second</TabsContent>
      </Tabs>,
    );
    expect(screen.getByRole("tablist", { name: "Types" })).toBeInTheDocument();
    const [a, b] = screen.getAllByRole("tab");
    expect(a).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("First");
    await user.tab();
    await user.keyboard("{ArrowRight}");
    expect(b).toHaveFocus();
    expect(b).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Second");
  });
});

describe("static primitives", () => {
  it("Pagination is a landmark and respects disabled edges", async () => {
    const onNext = vi.fn();
    wrap(<Pagination hasPrev={false} hasNext onPrev={() => {}} onNext={onNext} />);
    expect(screen.getByRole("navigation", { name: "Pagination" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(onNext).toHaveBeenCalled();
  });

  it("Skeleton announces loading politely once", () => {
    wrap(<Skeleton />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading…");
  });

  it("EmptyState has a heading and its witty line", () => {
    wrap(<EmptyState title="Nothing here yet">Be the first to leave a footprint.</EmptyState>);
    expect(screen.getByRole("heading", { name: "Nothing here yet" })).toBeInTheDocument();
    expect(screen.getByText(/footprint/)).toBeInTheDocument();
  });

  it("Callout uses alert only for danger", () => {
    wrap(
      <>
        <Callout>Info</Callout>
        <Callout tone="danger">Broken</Callout>
      </>,
    );
    expect(screen.getAllByRole("note")).toHaveLength(1);
    expect(screen.getByRole("alert")).toHaveTextContent("Broken");
  });

  it("Avatar is named and shows initials", () => {
    wrap(<Avatar name="Aygün Həsənova" />);
    expect(screen.getByRole("img", { name: "Aygün Həsənova" })).toHaveTextContent("AH");
  });

  it("Card is an article whose title is the link, with its call number", () => {
    wrap(
      <Card callNumber="RES-0421" title="Linear algebra" href="/r/1" stamp={<Stamp>New</Stamp>} />,
    );
    expect(screen.getByRole("link", { name: "Linear algebra" })).toHaveAttribute("href", "/r/1");
    expect(screen.getByText("RES-0421")).toBeInTheDocument();
    expect(screen.getByText("New")).toBeInTheDocument();
  });

  it("Marginalia is a labelled aside", () => {
    wrap(<Marginalia>nice!</Marginalia>);
    expect(screen.getByRole("complementary", { name: "Margin note" })).toHaveTextContent("nice!");
  });

  it("ships at least 15 icons", () => {
    expect(iconNames.length).toBeGreaterThanOrEqual(15);
  });
});

describe("Drawer, Textarea, Badge, Stamp", () => {
  it("Drawer is a labelled dialog with a working Close button", async () => {
    const user = userEvent.setup();
    wrap(
      <Drawer title="Filters" description="Narrow it down" trigger={<Button>Open</Button>}>
        <Textarea label="Notes" />
      </Drawer>,
    );
    await user.click(screen.getByRole("button", { name: "Open" }));
    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    expect(dialog).toHaveAccessibleDescription("Narrow it down");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    await user.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("Textarea is labelled and takes typing", async () => {
    const user = userEvent.setup();
    wrap(<Textarea label="Bio" />);
    const box = screen.getByRole("textbox", { name: "Bio" });
    await user.type(box, "hello");
    expect(box).toHaveValue("hello");
  });

  it("Badge and Stamp render their text", () => {
    wrap(
      <>
        <Badge>Draft</Badge>
        <Stamp>Verified</Stamp>
      </>,
    );
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
  });
});
