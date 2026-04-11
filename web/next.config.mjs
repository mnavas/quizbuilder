/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    // Proxy all /api/v1/* requests to the API container on the internal Docker network.
    // This means the browser always calls the same origin (port 3000) and never needs
    // direct access to port 8000 — eliminating all CORS and firewall issues.
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://api:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
