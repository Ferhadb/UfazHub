import createClient from "openapi-fetch";
import type { paths } from "./schema";

describe("api client", () => {
  it("calls typed paths with the /api prefix", async () => {
    const fetch = vi.fn(async () => Response.json({ status: "ok" }));
    const client = createClient<paths>({ baseUrl: "http://localhost", fetch });
    const { data } = await client.GET("/api/health");
    expect(data).toEqual({ status: "ok" });
    const req = (fetch.mock.calls[0] as unknown as [Request])[0];
    expect(new URL(req.url).pathname).toBe("/api/health");
  });
});
