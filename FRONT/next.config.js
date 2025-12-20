/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Next.js automatically loads .env.local, .env, etc.
  // We don't need to manually pass them through env: {}
  // The NEXT_PUBLIC_ prefix makes them available in the browser
}

module.exports = nextConfig

