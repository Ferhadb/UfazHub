import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useResource } from "@/lib/api/content";
import { page, renderWithProviders, resource, stubApi } from "@/test/utils";
import { ResourceActions } from "./actions";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/resources/RES-0421",
}));
let status = "authenticated";
vi.mock("@/lib/auth/use-session", () => ({ useSession: () => ({ status }) }));

// Reads the resource from the query cache like the detail page does.
function Harness() {
  const q = useResource("RES-0421");
  return q.data ? <ResourceActions resource={q.data} /> : <p>loading</p>;
}

const item = resource();
const detail = () => Response.json(item);

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
  status = "authenticated";
});

describe("ResourceActions", () => {
  it("moves the score before the server answers, then adopts the server's number", async () => {
    let release!: (r: Response) => void;
    stubApi({
      "GET /api/resources/RES-0421": detail,
      [`PUT /api/content/${item.id}/vote`]: () => new Promise<Response>((r) => (release = r)),
    });
    renderWithProviders(<Harness />);
    await userEvent.click(await screen.findByRole("button", { name: "Upvote" }));

    expect(screen.getByLabelText("Score 4")).toBeInTheDocument(); // optimistic
    expect(screen.getByRole("button", { name: "Upvote" })).toHaveAttribute("aria-pressed", "true");

    release(Response.json({ vote_score: 9, my_vote: 1 }));
    await waitFor(() => expect(screen.getByLabelText("Score 9")).toBeInTheDocument());
  });

  it("rolls back and tells the person when the vote is refused", async () => {
    stubApi({
      "GET /api/resources/RES-0421": detail,
      [`PUT /api/content/${item.id}/vote`]: () =>
        Response.json(
          { code: "self_vote", message: "You cannot vote on your own post." },
          { status: 403 },
        ),
    });
    renderWithProviders(<Harness />);
    await userEvent.click(await screen.findByRole("button", { name: "Upvote" }));

    await waitFor(() => expect(screen.getByLabelText("Score 3")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Upvote" })).toHaveAttribute("aria-pressed", "false");
    expect(await screen.findByText("You cannot vote on your own post.")).toBeInTheDocument();
  });

  it("clicking the chosen arrow again takes the vote back", async () => {
    const calls: unknown[] = [];
    stubApi({
      "GET /api/resources/RES-0421": () => Response.json(resource({ my_vote: 1, vote_score: 4 })),
      [`PUT /api/content/${item.id}/vote`]: async (req) => {
        const body = await req.json();
        calls.push(body);
        return Response.json({ vote_score: 3, my_vote: 0 });
      },
    });
    renderWithProviders(<Harness />);
    await userEvent.click(await screen.findByRole("button", { name: "Upvote" }));
    await waitFor(() => expect(calls).toEqual([{ value: 0 }]));
  });

  it("bookmarks optimistically and rolls back on failure", async () => {
    stubApi({
      "GET /api/resources/RES-0421": detail,
      [`PUT /api/content/${item.id}/bookmark`]: () =>
        Response.json({ code: "not_found", message: "Not found." }, { status: 404 }),
    });
    renderWithProviders(<Harness />);
    await userEvent.click(await screen.findByRole("button", { name: "Bookmark" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Bookmark" })).toBeInTheDocument(),
    );
    expect(screen.getByText("1 saved")).toBeInTheDocument();
  });

  it("sends guests to sign in instead of calling the API", async () => {
    status = "anonymous";
    const fetchMock = stubApi({ "GET /api/resources/RES-0421": detail });
    renderWithProviders(<Harness />);
    await userEvent.click(await screen.findByRole("button", { name: "Upvote" }));
    expect(push).toHaveBeenCalledWith("/signin?next=%2Fresources%2FRES-0421");
    expect(fetchMock).toHaveBeenCalledTimes(1); // only the detail GET
  });
});

it("page helper shapes a cursor page", async () => {
  expect(await page([1], "c").json()).toEqual({ items: [1], next_cursor: "c" });
});
