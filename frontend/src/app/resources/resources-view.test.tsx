import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, resource, stubApi } from "@/test/utils";
import { ResourcesView } from "./resources-view";

const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => "/resources",
  useSearchParams: () => new URLSearchParams(search),
}));
vi.mock("@/lib/auth/use-session", () => ({ useSession: () => ({ status: "authenticated" }) }));

const tags = () =>
  Response.json({ items: [{ name: "algebra", slug: "algebra", count: 4 }], next_cursor: null });

afterEach(() => {
  vi.unstubAllGlobals();
  replace.mockReset();
  search = "";
});

describe("ResourcesView", () => {
  it("shows skeletons, then cards", async () => {
    stubApi({
      "GET /api/resources": () =>
        page([resource(), resource({ id: "2", call_number: "RES-0422", title: "CS50" })]),
      "GET /api/tags": tags,
    });
    renderWithProviders(<ResourcesView />);
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
    expect(
      await screen.findByRole("heading", { name: "Linear Algebra Done Right" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "CS50" })).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("explains an empty shelf with a way forward", async () => {
    stubApi({ "GET /api/resources": () => page([]), "GET /api/tags": tags });
    renderWithProviders(<ResourcesView />);
    expect(await screen.findByText(/Be the first to leave a footprint/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Submit the first one" })).toHaveAttribute(
      "href",
      "/submit",
    );
  });

  it("shows the error envelope's message and retries", async () => {
    let fail = true;
    stubApi({
      "GET /api/resources": () =>
        fail
          ? Response.json({ code: "internal_error", message: "Something broke" }, { status: 500 })
          : page([resource()]),
      "GET /api/tags": tags,
    });
    renderWithProviders(<ResourcesView />);
    expect(await screen.findByText("Something broke")).toBeInTheDocument();
    fail = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByRole("heading", { name: "Linear Algebra Done Right" }),
    ).toBeInTheDocument();
  });

  it("follows the cursor for 'Load more'", async () => {
    const cursors: (string | null)[] = [];
    stubApi({
      "GET /api/resources": (req) => {
        const c = new URL(req.url).searchParams.get("cursor");
        cursors.push(c);
        return c
          ? page([resource({ id: "2", call_number: "RES-0002", title: "Second page card" })])
          : page([resource()], "next-1");
      },
      "GET /api/tags": tags,
    });
    renderWithProviders(<ResourcesView />);
    await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByRole("heading", { name: "Second page card" })).toBeInTheDocument();
    expect(cursors).toEqual([null, "next-1"]);
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("passes URL filters to the API and writes changes back to the URL", async () => {
    search = "tag=algebra&difficulty=advanced&research=1&sort=top";
    const urls: string[] = [];
    stubApi({
      "GET /api/resources": (req) => (urls.push(req.url), page([resource()])),
      "GET /api/tags": tags,
    });
    renderWithProviders(<ResourcesView />);
    await screen.findByRole("heading", { name: "Linear Algebra Done Right" });
    const q = new URL(urls[0]!).searchParams;
    expect(Object.fromEntries(q)).toMatchObject({
      tag: "algebra",
      difficulty: "advanced",
      research: "true",
      sort: "top",
    });

    await userEvent.selectOptions(screen.getByLabelText("Difficulty"), "beginner");
    expect(replace).toHaveBeenCalledWith(expect.stringContaining("difficulty=beginner"), {
      scroll: false,
    });
  });

  it("switches between list, grid and shelf", async () => {
    search = "view=shelf";
    stubApi({ "GET /api/resources": () => page([resource()]), "GET /api/tags": tags });
    renderWithProviders(<ResourcesView />);
    const shelf = await screen.findByRole("list", { name: "Shelf of resources" });
    expect(
      within(shelf).getByRole("link", { name: /Linear Algebra Done Right, RES-0421/ }),
    ).toHaveAttribute("href", "/resources/RES-0421");
    expect(screen.getByRole("button", { name: "Shelf" })).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(screen.getByRole("button", { name: "Grid" }));
    expect(replace).toHaveBeenCalledWith("/resources?view=grid", { scroll: false });
    await waitFor(() => expect(replace).toHaveBeenCalled());
  });
});
