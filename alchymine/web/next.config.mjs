/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    unoptimized: true,
  },
  env: {
    API_URL: process.env.API_URL || "http://localhost:8000",
    NEXT_PUBLIC_APP_VERSION: process.env.APP_VERSION || "dev",
  },
};

export default nextConfig;
