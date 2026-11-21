import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { Heatmap, level } from "./heatmap";
import { PeopleView } from "./people-view";
import { ProfileForm } from "./profile-form";
import { ProfileView } from "./profile-view";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth/use-session", () => ({
  useSession: () => ({ status: "authenticated", user: { id: "u1", role: "user" } }),
}));
afterEach(() => vi.unstubAllGlobals());

const person = (over: Record<string, unknown> = {}) => ({
  id: "u1",
  display_name: "Aygün Məmmədova",
  avatar_url: null,
  reputation: 120,
  role: "verified_ufazian",
  faculty: "Computer Science",
  graduation_year: 2026,
  job_title: "Teaching assistant",
  ...over,
});
const profile = (over: Record<string, unknown> = {}) => ({
  ...person(),
  bio: "Writes things down.",
  socials: { github: "https://github.com/aygun" },
  cosmetics: { banner: "banner-c-red", frame: "frame-ring" },
  supporter_tier: 0,
  gpa_url: "https://ufazgpa.xyz/u/22423010",
  joined_at: "2025-09-01T00:00:00Z",
  counts: { resource: 2, article: 1, collection: 0, question: 0, answer: 0, research: 0 },
  badges: [{ slug: "verified", name: "Verified Ufazian", description: "Confirmed as a student." }],
  activity: [{ day: "2026-11-20", count: 3 }],
  ...over,
});
const card = (over: Record<string, unknown> = {}) => ({
  id: "i1",
  type: "article",
  call_number: "ART-0001",
  title: "Surviving the algorithms exam",
  description: "Solve one problem a day.",
  is_research: false,
  author: { id: "u1", display_name: "Aygün", reputation: 1 },
  tags: ["algorithms"],
  vote_score: 4,
  comment_count: 0,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
});

describe("Heatmap", () => {
  it("levels counts and summarises the year for screen readers", () => {
    expect([0, 1, 2, 3, 4, 5, 40].map(level)).toEqual([0, 1, 2, 3, 3, 4, 4]);
    const { container } = renderWithProviders(
      <Heatmap
        today={new Date("2026-11-21T10:00:00Z")}
        activity={[
          { day: "2026-11-20", count: 3 },
          { day: "2026-11-01", count: 1 },
        ]}
      />,
    );
    expect(
      screen.getByRole("img", { name: "4 contributions in the last year" }),
    ).toBeInTheDocument();
    expect(container.querySelectorAll("path")).toHaveLength(2); // one stitch per active day
    expect(container.textContent).toContain("3 on 2026-11-20");
  });
});

describe("PeopleView", () => {
  it("lists people and sends the filters", async () => {
    const seen: string[] = [];
    stubApi({
      "GET /api/people": (req) => {
        seen.push(new URL(req.url).search);
        return page([person()]);
      },
      "GET /api/leaderboard": () =>
        Response.json([{ rank: 1, points: 40, person: person({ display_name: "Top Dog" }) }]),
      "GET /api/leaderboard/contributor-of-the-month": () =>
        Response.json({ rank: 1, points: 40, person: person({ display_name: "Top Dog" }) }),
    });
    renderWithProviders(<PeopleView />);
    expect(await screen.findByRole("link", { name: "Aygün Məmmədova" })).toHaveAttribute(
      "href",
      "/people/u1",
    );
    expect(screen.getByText(/Computer Science · class of 2026/)).toBeInTheDocument();
    expect(await screen.findByText("Contributor of the month")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Faculty"), "Geology");
    await userEvent.type(screen.getByLabelText("Class of"), "2027");
    await waitFor(() => expect(seen.at(-1)).toContain("graduation_year=2027"));
    expect(seen.at(-1)).toContain("faculty=Geology");
  });

  it("shows an empty state and an error with retry", async () => {
    stubApi({
      "GET /api/people": () => page([]),
      "GET /api/leaderboard": () => Response.json([]),
      "GET /api/leaderboard/contributor-of-the-month": () => Response.json(null),
    });
    renderWithProviders(<PeopleView />);
    expect(await screen.findByText("Nobody by that name")).toBeInTheDocument();
    expect(await screen.findByText("Nobody yet. The month is young.")).toBeInTheDocument();
    expect(screen.getByText("No points on the board yet.")).toBeInTheDocument();
  });

  it("offers a retry when the directory fails", async () => {
    let fail = true;
    stubApi({
      "GET /api/people": () =>
        fail
          ? ((fail = false), Response.json({ message: "Boom" }, { status: 500 }))
          : page([person()]),
      "GET /api/leaderboard": () => Response.json([]),
      "GET /api/leaderboard/contributor-of-the-month": () => Response.json(null),
    });
    renderWithProviders(<PeopleView />);
    await userEvent.click(await screen.findByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("link", { name: "Aygün Məmmədova" })).toBeInTheDocument();
  });
});

describe("ProfileView", () => {
  it("renders the library card, stamps, safe links and contributions", async () => {
    stubApi({
      "GET /api/people/u1": () => Response.json(profile()),
      "GET /api/people/u1/contributions": () => page([card()]),
    });
    renderWithProviders(<ProfileView id="u1" />);
    expect(await screen.findByRole("heading", { name: "Aygün Məmmədova" })).toBeInTheDocument();
    expect(screen.getByText("UFAZ Hub library card · UFZ-U1")).toBeInTheDocument();
    expect(screen.getByText("Teaching assistant")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View on/ })).toHaveAttribute(
      "href",
      "https://ufazgpa.xyz/u/22423010",
    );
    const stamps = screen.getByRole("heading", { name: "Stamps" }).closest("section")!;
    expect(within(stamps).getByText("Verified Ufazian")).toBeInTheDocument();
    const gh = screen.getByRole("link", { name: /GitHub/ });
    expect(gh).toHaveAttribute("rel", "noopener nofollow ugc");
    expect(screen.getByRole("link", { name: "Edit profile" })).toHaveAttribute("href", "/settings");
    expect(
      await screen.findByRole("link", { name: "Surviving the algorithms exam" }),
    ).toHaveAttribute("href", "/articles/ART-0001");
    expect(
      screen.getByRole("img", { name: "3 contributions in the last year" }),
    ).toBeInTheDocument();
  });

  it("says so when the person does not exist", async () => {
    stubApi({
      "GET /api/people/u1": () => Response.json({ message: "No" }, { status: 404 }),
      "GET /api/people/u1/contributions": () => page([]),
    });
    renderWithProviders(<ProfileView id="u1" />);
    expect(await screen.findByText("No such card-holder")).toBeInTheDocument();
  });
});

describe("ProfileForm", () => {
  it("blocks bad links, then saves only what the API accepts", async () => {
    let body: Record<string, unknown> | undefined;
    stubApi({
      "GET /api/people/u1": () => Response.json(profile()),
      "PATCH /api/me/profile": async (req) => {
        body = await req.json();
        return Response.json(profile({ bio: "New bio" }));
      },
    });
    renderWithProviders(<ProfileForm userId="u1" />);
    const bio = await screen.findByLabelText("Bio");
    await userEvent.clear(bio);
    await userEvent.type(bio, "New bio");
    await userEvent.clear(screen.getByLabelText("Website"));
    await userEvent.type(screen.getByLabelText("Website"), "javascript:alert(1)");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText("A full link starting with https://")).toBeInTheDocument();
    expect(body).toBeUndefined();
    await userEvent.clear(screen.getByLabelText("Website"));
    await userEvent.type(screen.getByLabelText("Website"), "https://aygun.example.org");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() => expect(body).toBeDefined());
    expect(body).toMatchObject({
      bio: "New bio",
      graduation_year: 2026,
      socials: { website: "https://aygun.example.org", github: "https://github.com/aygun" },
    });
    expect(await screen.findByText("Profile saved")).toBeInTheDocument();
  });

  it("shows the server's field error", async () => {
    stubApi({
      "GET /api/people/u1": () => Response.json(profile()),
      "PATCH /api/me/profile": () =>
        Response.json(
          { code: "validation_error", message: "Invalid", fields: { faculty: "Not a faculty" } },
          { status: 422 },
        ),
    });
    renderWithProviders(<ProfileForm userId="u1" />);
    const faculty = await screen.findByLabelText("Faculty");
    await userEvent.type(faculty, "x");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText("Not a faculty")).toBeInTheDocument();
  });
});
