import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // typedRoutes intentionally off: we build a couple of href strings dynamically
  // (e.g. "/analyze?name=...&smiles=...") for the "re-analyze" flow, which the
  // typedRoutes RouteImpl<string> would otherwise reject at build time.
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    return [{ source: "/api/backend/:path*", destination: `${api}/:path*` }];
  },
};

export default nextConfig;
