import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, resource, stubApi } from "@/test/utils";
import { ResourceDetail } from "./detail";

let session: { status: string; user: { id: string; role: string } | null };
vi.mock("@/lib/auth/use-session", () => ({ useSession: () => session }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/resources/RES-0421",
}));
afterEach(() => vi.unstubAllGlobals());
beforeEach(() => {
  session = { status: "authenticated", user: { id: "u9", role: "user" } };
});

const link = (id: string, health: "ok" | "dead" | "reported") => ({
  id,
  url: `https://example.org/${id}`,
  label: id,
  health,
});
const base = {
  "GET /api/content/11111111-1111-1111-1111-111111111111/courses": () => Response.json([]),
  "GET /api/programs": () => Response.json([]),
  "GET /api/resources/RES-0421/comments": () => Response.json({ items: [], next_cursor: null }),
  "GET /api/items/11111111-1111-1111-1111-111111111111/comments": () =>
    Response.json({ items: [], next_cursor: null }),
};

describe("link health on a resource", () => {
  it("stamps dead links, marks reported ones and lets a reader report a healthy one", async () => {
    let reported: string | null = null;
    const fn = stubApi({
      ...base,
      "GET /api/resources/RES-0421": () =>
        Response.json(
          resource({ links: [link("dead", "dead"), link("rep", "reported"), link("fine", "ok")] }),
        ),
      "PUT /api/links/fine/broken": () => {
        reported = "fine";
        return Response.json(link("fine", "reported"));
      },
    });
    void fn;
    renderWithProviders(<ResourceDetail callNumber="RES-0421" />);
    expect(await screen.findByText("Dead link")).toBeInTheDocument();
    expect(screen.getByText("Reported broken")).toBeInTheDocument();
    // only the healthy link offers the report button
    const buttons = screen.getAllByRole("button", { name: /Report broken/ });
    expect(buttons).toHaveLength(1);
    await userEvent.click(buttons[0]!);
    await waitFor(() => expect(reported).toBe("fine"));
  });
});
