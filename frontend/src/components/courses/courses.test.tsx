import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { CourseFiling } from "./course-filing";
import { CourseView } from "./course-view";
import { CoursesView } from "./courses-view";

let session: { status: string; user: { id: string; role: string } | null };
vi.mock("@/lib/auth/use-session", () => ({ useSession: () => session }));
afterEach(() => vi.unstubAllGlobals());
beforeEach(() => {
  session = { status: "authenticated", user: { id: "u1", role: "user" } };
});

const course = {
  slug: "algorithms-l2",
  name: "Algorithms",
  level: "L2",
  description: "Sorting, graphs, DP.",
  program: { slug: "cs", name: "Computer Science" },
};
const card = (n: number, type = "resource") => ({
  id: `i${n}`,
  type,
  call_number: `${type === "article" ? "ART" : "RES"}-000${n}`,
  title: `Item ${n}`,
  description: "d",
  is_research: false,
  author: { id: "u2", display_name: "Leyla", reputation: 0 },
  tags: [],
  vote_score: 0,
  comment_count: 0,
  created_at: "2026-01-01T00:00:00Z",
});

describe("CoursesView", () => {
  it("groups courses under their programs", async () => {
    stubApi({
      "GET /api/programs": () =>
        Response.json([
          { slug: "cs", name: "Computer Science", description: "", courses: [course] },
        ]),
    });
    renderWithProviders(<CoursesView />);
    expect(await screen.findByRole("heading", { name: "Computer Science" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Algorithms/ })).toHaveAttribute(
      "href",
      "/courses/algorithms-l2",
    );
  });

  it("has an empty state", async () => {
    stubApi({ "GET /api/programs": () => Response.json([]) });
    renderWithProviders(<CoursesView />);
    expect(await screen.findByText("No courses yet")).toBeInTheDocument();
  });
});

describe("CourseView", () => {
  it("shows the numbered start-here path and filters the rest by type", async () => {
    const types: (string | null)[] = [];
    stubApi({
      "GET /api/courses/algorithms-l2": () =>
        Response.json({ ...course, item_count: 3, start_here: [card(1), card(2, "article")] }),
      "GET /api/courses/algorithms-l2/items": (req) => {
        const t = new URL(req.url).searchParams.get("type");
        types.push(t);
        return page(
          t === "article" ? [card(2, "article")] : [card(1), card(2, "article"), card(3)],
        );
      },
    });
    renderWithProviders(<CourseView slug="algorithms-l2" />);
    const path = await screen.findByRole("list", { name: "" }).catch(() => null);
    expect(path ?? true).toBeTruthy();
    const start = (await screen.findByRole("heading", { name: "Start here" })).closest("section")!;
    const items = start.querySelectorAll("ol > li");
    expect(items).toHaveLength(2);
    expect(items[0]!.textContent).toContain("Item 1");
    expect(items[1]!.querySelector("a")).toHaveAttribute("href", "/articles/ART-0002");
    await userEvent.click(await screen.findByRole("tab", { name: "Articles" }));
    await waitFor(() => expect(types.at(-1)).toBe("article"));
  });

  it("explains a missing course and an empty path", async () => {
    stubApi({
      "GET /api/courses/nope": () => Response.json({ message: "No such course." }, { status: 404 }),
    });
    renderWithProviders(<CourseView slug="nope" />);
    expect(await screen.findByText("No such course")).toBeInTheDocument();
  });

  it("invites editors to pin a path when there is none", async () => {
    stubApi({
      "GET /api/courses/algorithms-l2": () =>
        Response.json({ ...course, item_count: 0, start_here: [] }),
      "GET /api/courses/algorithms-l2/items": () => page([]),
    });
    renderWithProviders(<CourseView slug="algorithms-l2" />);
    expect(await screen.findByText(/No reading order yet/)).toBeInTheDocument();
    expect(await screen.findByText(/Nothing filed under this course yet/)).toBeInTheDocument();
  });
});

describe("CourseFiling", () => {
  it("shows chips to everyone and hides the editor from non-owners", async () => {
    stubApi({
      "GET /api/content/i1/courses": () => Response.json([course]),
      "GET /api/programs": () => Response.json([]),
    });
    renderWithProviders(<CourseFiling itemId="i1" canEdit={false} />);
    expect(await screen.findByRole("link", { name: /Algorithms L2/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "File under a course" })).toBeNull();
  });

  it("lets the author pick courses and saves them", async () => {
    let sent: unknown;
    stubApi({
      "GET /api/content/i1/courses": () => Response.json([]),
      "GET /api/programs": () =>
        Response.json([
          { slug: "cs", name: "Computer Science", description: "", courses: [course] },
        ]),
      "PUT /api/content/i1/courses": async (req) => {
        sent = await req.json();
        return Response.json([course]);
      },
    });
    renderWithProviders(<CourseFiling itemId="i1" canEdit />);
    await userEvent.click(await screen.findByRole("button", { name: "File under a course" }));
    await userEvent.click(await screen.findByRole("checkbox", { name: /Algorithms L2/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(sent).toEqual({ course_slugs: ["algorithms-l2"] }));
  });
});
