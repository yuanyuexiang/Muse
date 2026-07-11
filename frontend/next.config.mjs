/** @type {import('next').NextConfig} */
// 把 /api/* 反代到后端，前端同源调用，免 CORS。
const backend = process.env.BACKEND_ORIGIN || "http://localhost:18000";

const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
