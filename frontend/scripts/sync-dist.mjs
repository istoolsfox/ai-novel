import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(here, "..");
const repoDir = resolve(frontendDir, "..");
const frontendDist = resolve(frontendDir, "dist");
const rootDist = resolve(repoDir, "dist");

if (!existsSync(frontendDist)) {
  throw new Error(`Frontend dist not found: ${frontendDist}`);
}

mkdirSync(repoDir, { recursive: true });
rmSync(rootDist, { recursive: true, force: true });
cpSync(frontendDist, rootDist, { recursive: true });
console.log(`Synced ${frontendDist} -> ${rootDist}`);
console.log("Cloudflare Pages root output is ready.");
