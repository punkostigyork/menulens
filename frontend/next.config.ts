import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "standalone",
  experimental: { proxyClientMaxBodySize: Number(process.env.MAX_UPLOAD_BYTES || 10485760) + 1024 * 1024 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.BACKEND_URL || "http://backend:8000"}/api/:path*` }];
  },
};
export default nextConfig;
