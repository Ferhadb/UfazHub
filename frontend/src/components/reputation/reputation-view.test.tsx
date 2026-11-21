import { screen } from "@testing-library/react";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { ReputationView } from "./reputation-view";

let status = "authenticated";
vi.mock("@/lib/auth/use-session", () => ({
  useSession: () => ({ status, user: status === "authenticated" ? { reputation: 17 } : null }),
}));
afterEach(() => {
  vi.unstubAllGlobals();
  status = "authenticated";
});

const rules = {
  points: [
    { reason: "upvote_answer", label: "Your answer is upvoted", points: 10 },
    { reason: "downvote", label: "Your post is downvoted", points: -2 },
  ],
  privileges: [{ key: "downvote_answers", label: "Downvote answers", threshold: 15 }],
  daily_vote_cap: 200,
};

describe("ReputationView", () => {
  it("renders the points table and privileges from the API, plus your own history", async () => {
    stubApi({
      "GET /api/reputation/rules": () => Response.json(rules),
      "GET /api/me/reputation": () =>
        page([
          {
            reason: "vote_up",
            points: 10,
            call_number: "ANS-0001",
            title: "x",
            created_at: "2026-01-01T00:00:00Z",
          },
        ]),
    });
    renderWithProviders(<ReputationView />);
    expect(await screen.findByText("Your answer is upvoted")).toBeInTheDocument();
    expect(screen.getByText("+10", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByText("-2")).toBeInTheDocument();
    expect(screen.getByText("Downvote answers")).toBeInTheDocument();
    expect(screen.getByText(/at most 200 reputation per day/)).toBeInTheDocument();
    expect(await screen.findByText("ANS-0001")).toBeInTheDocument();
  });

  it("is public: guests get the rules and a sign-in hint", async () => {
    status = "anonymous";
    stubApi({ "GET /api/reputation/rules": () => Response.json(rules) });
    renderWithProviders(<ReputationView />);
    expect(await screen.findByText("Downvote answers")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("offers a retry when the rules fail to load", async () => {
    status = "anonymous";
    stubApi({
      "GET /api/reputation/rules": () =>
        Response.json({ code: "boom", message: "Nope" }, { status: 500 }),
    });
    renderWithProviders(<ReputationView />);
    expect(await screen.findByText("Nope")).toBeInTheDocument();
  });
});
