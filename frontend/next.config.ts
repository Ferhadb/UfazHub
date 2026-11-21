import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const config: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  // In Docker nginx routes /api to the backend; locally `next dev` proxies it.
  async rewrites() {
    if (process.env.NODE_ENV === "production") return [];
    const target = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${target}/api/:path*` }];
  },
};

export default createNextIntlPlugin()(config);
