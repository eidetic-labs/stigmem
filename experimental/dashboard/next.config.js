/** @type {import('next').NextConfig} */
const nextConfig = {
  // expose stigmem API URL to server components without the NEXT_PUBLIC_ prefix
  // NEXT_PUBLIC_STIGMEM_API_URL is also set for client-side use (React Query hooks)
  output: "standalone",
};

module.exports = nextConfig;
