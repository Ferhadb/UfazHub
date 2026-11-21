import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { BookmarksView } from "./bookmarks-view";
import { SharedListView } from "./shared-list-view";

vi.mock("@/lib/auth/use-session", () => ({
  useSession: () => ({ status: "authenticated", user: { id: "u1", role: "user" } }),
}));
afterEach(() => vi.unstubAllGlobals());

const card = (n: number) => ({
  id: `i${n}`,
  type: "resource",
  call_number: `RES-000${n}`,
  title: `Item ${n}`,
  description: "d",
  is_research: n === 2,
  author: { id: "u2", display_name: "Leyla", reputation: 0 },
  tags: ["algebra"],
  vote_score: 1,
  comment_count: 0,
  created_at: "2026-01-01T00:00:00Z",
});
const list = (over: Record<string, unknown> = {}) => ({
  id: "l1",
  name: "Exam week",
  share_token: null,
  item_count: 1,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
});

describe("BookmarksView", () => {
  it("lists saved cards and adds one to a reading list", async () => {
    let added: string | undefined;
    stubApi({
      "GET /api/me/bookmarks": () => page([card(1), card(2)]),
      "GET /api/me/reading-lists": () => page([list()]),
      "PUT /api/reading-lists/l1/items/i1": () => {
        added = "i1";
        return Response.json(list({ item_count: 2 }));
      },
    });
    renderWithProviders(<BookmarksView />);
    expect(await screen.findByRole("link", { name: "Item 1" })).toHaveAttribute(
      "href",
      "/resources/RES-0001",
    );
    // research cards take the research tint
    expect(screen.getAllByText("research")).toHaveLength(1);
    const selects = await screen.findAllByLabelText("Add to a list");
    await userEvent.selectOptions(selects[0]!, "l1");
    await waitFor(() => expect(added).toBe("i1"));
  });

  it("is friendly when nothing is saved", async () => {
    stubApi({
      "GET /api/me/bookmarks": () => page([]),
      "GET /api/me/reading-lists": () => page([]),
    });
    renderWithProviders(<BookmarksView />);
    expect(await screen.findByText("Nothing saved")).toBeInTheDocument();
  });

  it("creates, shares and deletes a list", async () => {
    let lists = [list()];
    const calls: string[] = [];
    stubApi({
      "GET /api/me/bookmarks": () => page([]),
      "GET /api/me/reading-lists": () => page(lists),
      "POST /api/me/reading-lists": async (req) => {
        const { name } = await req.json();
        calls.push(`create ${name}`);
        lists = [...lists, list({ id: "l2", name, item_count: 0 })];
        return Response.json(lists[1], { status: 201 });
      },
      "GET /api/reading-lists/l1/items": () => page([card(1)]),
      "PUT /api/reading-lists/l1/share": () => {
        calls.push("share");
        lists = [list({ share_token: "tok123" })];
        return Response.json(lists[0]);
      },
      "DELETE /api/reading-lists/l1": () => {
        calls.push("delete");
        lists = [];
        return new Response(null, { status: 204 });
      },
    });
    renderWithProviders(<BookmarksView />);
    await userEvent.click(await screen.findByRole("tab", { name: "Reading lists" }));
    await userEvent.type(await screen.findByLabelText("New list"), "Finals");
    await userEvent.click(screen.getByRole("button", { name: "Create list" }));
    await waitFor(() => expect(calls).toContain("create Finals"));

    await userEvent.click((await screen.findAllByRole("button", { name: /^Open/ }))[0]!);
    expect(await screen.findByRole("link", { name: "Item 1" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("switch", { name: /Anyone with the link/ }));
    const link = await screen.findByLabelText("Share link");
    expect((link as HTMLInputElement).value).toMatch(/\/lists\/tok123$/);

    await userEvent.click(screen.getByRole("button", { name: "Delete list" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Delete Exam week" }));
    await waitFor(() => expect(calls).toContain("delete"));
    expect(await screen.findByLabelText("New list")).toBeInTheDocument(); // back on the lists tab
  });
});

describe("SharedListView", () => {
  it("renders a shared list with its owner", async () => {
    stubApi({
      "GET /api/shared/lists/tok": () =>
        Response.json({
          name: "Exam week",
          owner: { id: "u2", display_name: "Leyla", reputation: 0 },
          items: [card(1)],
          next_cursor: null,
        }),
    });
    renderWithProviders(<SharedListView token="tok" />);
    expect(await screen.findByRole("heading", { name: "Exam week" })).toBeInTheDocument();
    expect(screen.getByText(/by Leyla/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Item 1" })).toBeInTheDocument();
  });

  it("treats an unshared list as private", async () => {
    stubApi({
      "GET /api/shared/lists/tok": () => Response.json({ message: "Private" }, { status: 404 }),
    });
    renderWithProviders(<SharedListView token="tok" />);
    expect(await screen.findByText("This list is private")).toBeInTheDocument();
  });
});
