import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { comment, page, renderWithProviders, stubApi } from "@/test/utils";
import { Comments } from "./comments";

let session: { status: string; user: Record<string, unknown> | null } = {
  status: "authenticated",
  user: { id: "u1", email_verified: true, role: "student" },
};
vi.mock("@/lib/auth/use-session", () => ({ useSession: () => session }));

const ID = "11111111-1111-1111-1111-111111111111";
afterEach(() => {
  vi.unstubAllGlobals();
  session = { status: "authenticated", user: { id: "u1", email_verified: true, role: "student" } };
});

describe("Comments", () => {
  it("shows the empty state", async () => {
    stubApi({ [`GET /api/content/${ID}/comments`]: () => page([]) });
    renderWithProviders(<Comments itemId={ID} count={0} />);
    expect(await screen.findByText(/No notes yet/)).toBeInTheDocument();
  });

  it("renders comment text as text, never as markup", async () => {
    stubApi({
      [`GET /api/content/${ID}/comments`]: () =>
        page([comment({ body: "<img src=x onerror=alert(1)>" })]),
    });
    const { container } = renderWithProviders(<Comments itemId={ID} count={1} />);
    expect(await screen.findByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });

  it("posts a note", async () => {
    let body: unknown;
    stubApi({
      [`GET /api/content/${ID}/comments`]: () => page([]),
      [`POST /api/content/${ID}/comments`]: async (req) => {
        body = await req.json();
        return Response.json(comment(), { status: 201 });
      },
    });
    renderWithProviders(<Comments itemId={ID} count={0} />);
    await userEvent.type(await screen.findByLabelText("Add a note"), "Thanks!");
    await userEvent.click(screen.getByRole("button", { name: "Post note" }));
    await waitFor(() => expect(body).toEqual({ body: "Thanks!" }));
  });

  it("asks guests to sign in and unverified users to verify", async () => {
    stubApi({ [`GET /api/content/${ID}/comments`]: () => page([]) });
    session = { status: "anonymous", user: null };
    const { unmount } = renderWithProviders(<Comments itemId={ID} count={0} />);
    expect(await screen.findByRole("link", { name: "Sign in" })).toBeInTheDocument();
    unmount();
    session = { status: "authenticated", user: { id: "u1", email_verified: false } };
    renderWithProviders(<Comments itemId={ID} count={0} />);
    expect(await screen.findByText("Verify your email to comment")).toBeInTheDocument();
    expect(screen.queryByLabelText("Add a note")).not.toBeInTheDocument();
  });

  it("lets only replies to top-level notes, and the owner delete", async () => {
    let deleted = false;
    stubApi({
      [`GET /api/content/${ID}/comments`]: () =>
        page([
          comment({
            id: "c1",
            author: { id: "u1", display_name: "Me" },
            replies: [comment({ id: "c2", parent_id: "c1", body: "reply" })],
          }),
        ]),
      "DELETE /api/comments/c1": () => {
        deleted = true;
        return new Response(null, { status: 204 });
      },
    });
    renderWithProviders(<Comments itemId={ID} count={2} />);
    await screen.findByText("reply");
    expect(screen.getAllByRole("button", { name: "Reply" })).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: /Delete/ }));
    await waitFor(() => expect(deleted).toBe(true));
  });
});
