import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    return [{ source: "/api/backend/:path*", destination: `${api}/:path*` }];
  },
};

export default nextConfig;
