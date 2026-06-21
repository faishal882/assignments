import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const isWindows = process.platform === "win32";
const backendPython = path.join(root, "backend", ".venv", isWindows ? "Scripts/python.exe" : "bin/python");
const npm = isWindows ? "npm.cmd" : "npm";

if (!existsSync(backendPython)) {
  console.error("Backend virtual environment is missing. Run `npm ci` first.");
  process.exit(1);
}

const detached = !isWindows;
const processes = [
  spawn(backendPython, ["-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], {
    cwd: path.join(root, "backend"),
    detached,
    stdio: "inherit",
  }),
  spawn(npm, ["run", "dev", "--workspace", "frontend", "--", "--host", "127.0.0.1", "--port", "5173"], {
    cwd: root,
    detached,
    stdio: "inherit",
  }),
];

let stopping = false;

function stopProcess(child, signal = "SIGTERM") {
  if (!child.pid || child.killed) return;
  if (isWindows) child.kill(signal);
  else {
    try {
      process.kill(-child.pid, signal);
    } catch {
      // The process may have already exited.
    }
  }
}

function shutdown(signal, exitCode = 0) {
  if (stopping) return;
  stopping = true;
  processes.forEach((child) => stopProcess(child, signal));
  process.exitCode = exitCode;
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
processes.forEach((child) => {
  child.on("error", (error) => {
    console.error(error.message);
    shutdown("SIGTERM", 1);
  });
  child.on("exit", (code, signal) => {
    if (!stopping) {
      console.error(`Development process stopped unexpectedly (${signal ?? `exit ${code}`}).`);
      shutdown("SIGTERM", code ?? 1);
    }
  });
});

console.log("Backend: http://127.0.0.1:8000");
console.log("Frontend: http://127.0.0.1:5173");
