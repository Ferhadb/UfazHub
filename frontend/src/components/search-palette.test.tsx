import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { SearchPalette } from "./search-palette";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const hit = (over = {}) => ({
  id: "1",
  type: "resource",
  call_number: "RES-0421",
  title: "Linear Algebra Done Right",
  title_hl: "Linear \u0002Algebra\u0003 Done Right",
  snippet: "A proof-first \u0002algebra\u0003 textbook.",
  is_research: false,
  vote_score: 2,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
});

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
});

async function openPalette() {
  renderWithProviders(<SearchPalette />);
  await userEvent.keyboard("{Control>}k{/Control}");
  return screen.findByRole("dialog");
}

describe("SearchPalette", () => {
  it("opens with Ctrl+K, focuses the field and closes with Escape, returning focus", async () => {
    stubApi({});
    renderWithProviders(<SearchPalette />);
    const trigger = screen.getByRole("button", { name: /Search/ });
    await userEvent.keyboard("{Control>}k{/Control}");
    expect(await screen.findByRole("dialog", { name: "Search the catalogue" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Search" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("keeps Tab focus inside the dialog", async () => {
    stubApi({});
    const dialog = await openPalette();
    for (let i = 0; i < 12; i++) {
      await userEvent.tab();
      expect(dialog).toContainElement(document.activeElement as HTMLElement);
    }
    await userEvent.tab({ shift: true });
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
  });

  it("searches, groups by type, highlights matches without HTML and navigates with the keyboard", async () => {
    const urls: string[] = [];
    stubApi({
      "GET /api/search": (req) => {
        urls.push(req.url);
        return page([
          hit(),
          hit({
            id: "2",
            call_number: "RES-0422",
            title: "CS50",
            title_hl: "CS50",
            snippet: "<b>x</b>",
          }),
        ]);
      },
    });
    await openPalette();
    await userEvent.type(screen.getByRole("combobox"), "algebra");

    const marks = await screen.findAllByText("Algebra", { selector: "mark" });
    expect(marks.length).toBeGreaterThan(0);
    expect(screen.getByRole("group", { name: "resources" })).toBeInTheDocument();
    expect(screen.getByText("<b>x</b>")).toBeInTheDocument(); // text, not an element
    expect(new URL(urls.at(-1)!).searchParams.get("q")).toBe("algebra");
    expect(screen.getByRole("status")).toHaveTextContent("2 results");

    const combo = screen.getByRole("combobox");
    const options = screen.getAllByRole("option");
    expect(combo).toHaveAttribute("aria-activedescendant", options[0]!.id);
    await userEvent.keyboard("{ArrowDown}");
    expect(combo).toHaveAttribute("aria-activedescendant", options[1]!.id);
    await userEvent.keyboard("{Enter}");
    expect(push).toHaveBeenCalledWith("/resources/RES-0422");
  });

  it("filters by type tab", async () => {
    const urls: string[] = [];
    stubApi({ "GET /api/search": (req) => (urls.push(req.url), page([hit()])) });
    await openPalette();
    await userEvent.type(screen.getByRole("combobox"), "algebra");
    await screen.findAllByRole("option");
    await userEvent.click(screen.getByRole("tab", { name: "Questions" }));
    await waitFor(() => expect(new URL(urls.at(-1)!).searchParams.get("type")).toBe("question"));
  });

  it("explains empty results and errors with a retry", async () => {
    let fail = true;
    stubApi({
      "GET /api/search": () =>
        fail
          ? Response.json({ code: "rate_limited", message: "Too many requests." }, { status: 429 })
          : page([]),
    });
    await openPalette();
    await userEvent.type(screen.getByRole("combobox"), "zzzz");
    expect(await screen.findByText("Too many requests.")).toBeInTheDocument();
    fail = false;
    await act(async () => screen.getByRole("button", { name: "Try again" }).click());
    expect(await screen.findByText("Nothing under that heading")).toBeInTheDocument();
  });

  it("asks for two letters before searching", async () => {
    const fetchMock = stubApi({});
    await openPalette();
    await userEvent.type(screen.getByRole("combobox"), "a");
    expect(screen.getByText(/at least two letters/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
