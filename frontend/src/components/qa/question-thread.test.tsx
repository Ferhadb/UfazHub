import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { QuestionThread } from "./question-thread";

const replace = vi.fn();
let merged: string | null = null;
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace }),
  useSearchParams: () => ({ get: () => merged }),
  usePathname: () => "/questions/QST-0001",
}));
let session: { status: string; user: Record<string, unknown> | null };
vi.mock("@/lib/auth/use-session", () => ({ useSession: () => session }));

const asker = { id: "u1", display_name: "Aygün", reputation: 5 };
const other = { id: "u2", display_name: "Leyla", reputation: 40 };
const question = (over: Record<string, unknown> = {}) => ({
  id: "q1",
  type: "question",
  call_number: "QST-0001",
  title: "How do I prove Dijkstra correct?",
  body: "I lose the invariant proof.",
  topic: "Algorithms",
  status: "published",
  is_research: false,
  author: asker,
  tags: ["graphs"],
  vote_score: 2,
  bookmark_count: 0,
  comment_count: 0,
  answer_count: 2,
  has_accepted: true,
  linked_resource: { call_number: "RES-0421", title: "CLRS" },
  duplicate_of: null,
  created_at: "2026-01-01T00:00:00Z",
  my_vote: 0,
  bookmarked: false,
  ...over,
});
const answer = (over: Record<string, unknown> = {}) => ({
  id: "a1",
  type: "answer",
  call_number: "ANS-0001",
  question_id: "q1",
  body: "Use the loop invariant.",
  status: "published",
  author: other,
  vote_score: 12,
  comment_count: 0,
  accepted: false,
  pinned: false,
  created_at: "2026-01-02T00:00:00Z",
  my_vote: 0,
  bookmarked: false,
  ...over,
});

const routes = (
  q = question(),
  items = [
    answer({ accepted: true }),
    answer({ id: "a2", call_number: "ANS-0002", body: "Second", vote_score: 0 }),
  ],
) => ({
  "GET /api/questions/QST-0001": () => Response.json(q),
  "GET /api/questions/QST-0001/answers": () => page(items),
  "GET /api/content/q1/comments": () => page([]),
});

beforeEach(() => {
  merged = null;
  session = { status: "authenticated", user: { id: "u1", email_verified: true, role: "user" } };
});
afterEach(() => {
  vi.unstubAllGlobals();
  replace.mockReset();
});

describe("QuestionThread", () => {
  it("lays the thread out as an exam paper with a checked answer and the score in the margin", async () => {
    stubApi(routes());
    renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    expect(await screen.findByRole("heading", { name: question().title })).toBeInTheDocument();
    expect(await screen.findByText("Use the loop invariant.")).toBeInTheDocument();
    expect(screen.getAllByText("✓ checked")).toHaveLength(1);
    expect(screen.getByText("+12")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /RES-0421 CLRS/ })).toHaveAttribute(
      "href",
      "/resources/RES-0421",
    );
  });

  it("lets only the asker check an answer, and only an admin pin", async () => {
    stubApi(routes());
    const { unmount } = renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    expect(
      await screen.findAllByRole("button", { name: /Mark as checked|Remove the check/ }),
    ).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Pin" })).not.toBeInTheDocument();
    unmount();
    session = { status: "authenticated", user: { id: "u2", email_verified: true, role: "admin" } };
    renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    expect(await screen.findAllByRole("button", { name: "Pin" })).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /Mark as checked/ })).not.toBeInTheDocument();
  });

  it("accepts an answer through the API", async () => {
    let called = "";
    stubApi({
      ...routes(question({ has_accepted: false }), [
        answer({ id: "a2", call_number: "ANS-0002", body: "Second" }),
      ]),
      "PUT /api/answers/a2/accept": (req) => {
        called = req.method;
        return Response.json(answer({ id: "a2", accepted: true }));
      },
    });
    renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    await userEvent.click(await screen.findByRole("button", { name: "Mark as checked" }));
    await waitFor(() => expect(called).toBe("PUT"));
  });

  it("redirects a merged question to its original", async () => {
    stubApi(routes(question({ duplicate_of: { call_number: "QST-0007", title: "Original" } })));
    renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/questions/QST-0007?merged=QST-0001"),
    );
  });

  it("says where a merged question came from", async () => {
    merged = "QST-0004";
    stubApi(routes());
    renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    expect(await screen.findByText(/QST-0004 was a duplicate/)).toBeInTheDocument();
  });

  it("posts an answer, and gates guests and unverified users", async () => {
    let body: unknown;
    stubApi({
      ...routes(),
      "POST /api/questions/q1/answers": async (req) => {
        body = await req.json();
        return Response.json(answer({ id: "a9" }), { status: 201 });
      },
    });
    const { unmount } = renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    await userEvent.type(await screen.findByLabelText("Your answer"), "Because of the invariant.");
    await userEvent.click(screen.getByRole("button", { name: "Submit answer" }));
    await waitFor(() => expect(body).toEqual({ body: "Because of the invariant." }));
    unmount();
    session = { status: "anonymous", user: null };
    const again = renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    expect(await screen.findByText(/to write an answer/)).toBeInTheDocument();
    again.unmount();
    session = { status: "authenticated", user: { id: "u3", email_verified: false } };
    renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    expect(await screen.findByText("Verify your email to answer")).toBeInTheDocument();
  });

  it("shows a friendly page for an unknown question", async () => {
    stubApi({
      "GET /api/questions/QST-0001": () =>
        Response.json({ code: "not_found", message: "Not found." }, { status: 404 }),
      "GET /api/questions/QST-0001/answers": () => page([]),
    });
    renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    expect(await screen.findByText("No such question")).toBeInTheDocument();
  });

  it("renders answer text as text, never markup", async () => {
    stubApi(routes(question(), [answer({ body: "<img src=x onerror=alert(1)>" })]));
    const { container } = renderWithProviders(<QuestionThread callNumber="QST-0001" />);
    expect(await screen.findByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });
});
