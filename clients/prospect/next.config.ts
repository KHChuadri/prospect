import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits .next/standalone with a minimal server.js — the Docker image runs
  // that instead of `next start`, so it needs no node_modules.
  output: "standalone",
};

export default nextConfig;
