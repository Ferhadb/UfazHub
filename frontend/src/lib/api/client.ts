import createClient from "openapi-fetch";
import type { paths } from "./schema";

// Schema paths already carry the /api prefix, so the base is the site origin (same-origin by default).
export const api = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_ORIGIN ?? "",
  credentials: "include", // httpOnly refresh cookie
});
