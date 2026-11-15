import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
const local =
  ["../backend/.venv", "../backend/venv"]
    .map((environment) =>
      process.platform === "win32"
        ? `${environment}/Scripts/python.exe`
        : `${environment}/bin/python`,
    )
    .find(existsSync);
const result = spawnSync(
  local ?? "python",
  ["../backend/scripts/export_openapi.py"],
  { stdio: "inherit" },
);
if (result.error || result.status !== 0) process.exit(1);
