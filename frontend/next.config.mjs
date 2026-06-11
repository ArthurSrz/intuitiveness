import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Pin the workspace root to this dir — a stray package-lock.json in the
  // home directory otherwise confuses Next's root inference.
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
