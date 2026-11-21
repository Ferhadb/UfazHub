import createClient from "openapi-fetch";
import { authMiddleware } from "./client";
import { setAccessToken } from "@/lib/auth/token";
import type { paths } from "./schema";

function make() {
  const fetch = vi.fn(async () => Response.json({}));
  const client = createClient<paths>({ baseUrl: "http://localhost", fetch });
  client.use(authMiddleware);
  const sent = () => (fetch.mock.calls[0] as unknown as [Request])[0];
  return { client, sent };
}

describe("auth middleware", () => {
  afterEach(() => setAccessToken(null));

  it("injects the bearer token and the CSRF header on writes", async () => {
    setAccessToken("jwt-1");
    document.cookie = "csrf_token=c123; path=/";
    const { client, sent } = make();
    await client.POST("/api/auth/refresh");
    expect(sent().headers.get("Authorization")).toBe("Bearer jwt-1");
    expect(sent().headers.get("X-CSRF-Token")).toBe("c123");
  });

  it("sends no Authorization when signed out, and no CSRF header on GET", async () => {
    document.cookie = "csrf_token=c123; path=/";
    const { client, sent } = make();
    await client.GET("/api/health");
    expect(sent().headers.get("Authorization")).toBeNull();
    expect(sent().headers.get("X-CSRF-Token")).toBeNull();
  });
});
