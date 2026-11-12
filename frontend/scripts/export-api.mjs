import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
const local =
  process.platform === "win32"
    ? "../backend/.venv/Scripts/python.exe"
    : "../backend/.venv/bin/python";
const result = spawnSync(
  existsSync(local) ? local : "python",
  ["../backend/scripts/export_openapi.py"],
  { stdio: "inherit" },
);
if (result.error || result.status !== 0) process.exit(1);
