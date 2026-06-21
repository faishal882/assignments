import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const backend = path.join(root, "backend");
const isWindows = process.platform === "win32";
const venvPython = path.join(backend, ".venv", isWindows ? "Scripts/python.exe" : "bin/python");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: "inherit", ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function findPython() {
  const candidates = process.env.PYTHON ? [process.env.PYTHON] : isWindows ? ["py", "python"] : ["python3", "python"];
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["--version"], { stdio: "ignore" });
    if (!result.error && result.status === 0) return candidate;
  }
  console.error("Python 3.11+ was not found. Install Python or set the PYTHON environment variable.");
  process.exit(1);
}

if (!existsSync(venvPython)) {
  const python = findPython();
  console.log("Creating backend virtual environment...");
  run(python, ["-m", "venv", path.join(backend, ".venv")]);
}

console.log("Installing backend Python packages...");
run(venvPython, ["-m", "pip", "install", "--disable-pip-version-check", "-r", path.join(backend, "requirements.txt")]);
