const scenarios = [
  {
    category: "Frontend · Network",
    title: "The blank dashboard",
    difficulty: "Warm-up",
    report: "My app worked yesterday. After deploying a new frontend, login succeeds, but the dashboard is completely blank for every user.",
    prompt: "Take the incident. What do you ask first, and how do you narrow it down without jumping to a fix?",
    evidence: [
      ["Browser console", "TypeError: Cannot read properties of undefined (reading 'map')\n    at Dashboard (Dashboard.8f12.js:1:1842)"],
      ["Network: GET /api/projects", "Status: 200 OK\nContent-Type: application/json\nBody: { \"data\": { \"projects\": null } }"],
      ["Deployment change", "Frontend changed from projects?.map(...) to projects.map(...).\nNo backend deployment occurred."],
    ],
    diagnosis: "A frontend null-handling regression crashes render when the API returns a valid nullable value.",
    approach: ["Confirm blast radius, browser/version, and last known good deployment.", "Separate rendering failure from API reachability using Console and Network.", "Reproduce with the returned payload and verify the failing line via source maps.", "Mitigate by rolling back or guarding the nullable field; then add an empty state and contract test."],
    update: "We found a display regression in the latest frontend—not a loss of customer data. We can restore the previous version while we add safe handling for empty project lists, then verify the dashboard with affected accounts.",
  },
  {
    category: "Backend · Authentication",
    title: "401 after a successful login",
    difficulty: "Core",
    report: "Users can sign in, but every API request immediately returns 401. It only happens in production; local development is fine.",
    prompt: "Walk me through the request path. Which evidence would you inspect, and in what order?",
    evidence: [
      ["Network request", "GET https://api.acme.app/v1/me → 401\nRequest headers: Authorization: Bearer eyJ...\nResponse: { \"error\": \"invalid token issuer\" }"],
      ["Decoded JWT claims", "iss: https://auth-staging.acme.app/\naud: acme-api\nexp: 1782099900"],
      ["Production environment", "AUTH_ISSUER=https://auth.acme.app/\nPUBLIC_AUTH_ISSUER=https://auth-staging.acme.app/"],
    ],
    diagnosis: "The production frontend requests tokens from staging while the API validates the production issuer.",
    approach: ["Establish whether 401 affects token issuance or token validation.", "Inspect the exact response, Authorization header, and safe decoded claims—never expose the token.", "Compare issuer, audience, expiry, clock, and API validator configuration.", "Correct the public build-time variable, rebuild, revoke inappropriate sessions, and test a fresh login."],
    update: "Authentication is available, but the production web app is issuing credentials from the wrong environment. We have isolated the configuration mismatch and will rebuild the frontend with the production identity provider, then validate new sessions end to end.",
  },
  {
    category: "Deployment · Containers",
    title: "Healthy build, crashing service",
    difficulty: "Core",
    report: "The deployment says the image built successfully, but the service never becomes healthy and keeps restarting.",
    prompt: "How do you distinguish an application crash from a platform or health-check problem?",
    evidence: [
      ["Container logs", "Server listening on http://127.0.0.1:3000\nReceived SIGTERM\nShutting down..."],
      ["Platform events", "Readiness probe failed: dial tcp 10.2.4.18:8080: connect: connection refused\nRestart count: 7"],
      ["Runtime configuration", "PORT=8080\nHealth check: GET :8080/health\nDocker CMD: npm start"],
    ],
    diagnosis: "The app ignores the platform PORT and binds localhost:3000, so the readiness probe cannot reach it.",
    approach: ["Check build success separately from process startup and readiness.", "Read application logs and platform events on the same timeline.", "Verify command, injected port, bind address, probe path, timeout, and resource limits.", "Bind to 0.0.0.0:$PORT, test the image under production env, deploy gradually, and watch restarts."],
    update: "The image is valid; the running process is listening on a private address and different port than the platform expects. We’ll correct the listener configuration and verify the health endpoint before replacing the current revision.",
  },
  {
    category: "Networking · CORS",
    title: "Works in curl, blocked in browser",
    difficulty: "Core",
    report: "The API works in Postman and curl, but the browser says it was blocked by CORS when uploading a file.",
    prompt: "Explain why those observations are consistent. What exact requests and headers do you inspect?",
    evidence: [
      ["Browser console", "Access to fetch at 'https://api.acme.app/upload' from origin 'https://app.acme.app' has been blocked by CORS policy."],
      ["Preflight request", "OPTIONS /upload → 204\nAccess-Control-Allow-Origin: *\nAccess-Control-Allow-Methods: GET, POST\nAccess-Control-Allow-Headers: Content-Type"],
      ["Frontend request", "POST /upload\nOrigin: https://app.acme.app\nAuthorization: Bearer ...\nContent-Type: multipart/form-data"],
    ],
    diagnosis: "The browser preflight asks to use Authorization, but that header is absent from Access-Control-Allow-Headers.",
    approach: ["Clarify the exact origin, method, custom headers, credentials mode, and affected route.", "Inspect the OPTIONS request—not only the POST—and compare requested vs allowed values.", "Explain that CORS is enforced by browsers, so curl success does not validate browser policy.", "Allow the precise trusted origin/header, preserve auth checks, verify preflight and actual response, and avoid wildcard credentials."],
    update: "The API itself is responding; the browser’s safety check is rejecting the upload because the authorization header is not in the route’s allowlist. We’ll make the narrow CORS policy change and retest from the production origin.",
  },
  {
    category: "Database · Reliability",
    title: "Intermittent checkout timeouts",
    difficulty: "Advanced",
    report: "Checkout becomes slow for a few minutes at a time. Retrying sometimes works. CPU looks normal, and no deployment happened today.",
    prompt: "This is ambiguous. Show me how you build and prioritize hypotheses before changing anything.",
    evidence: [
      ["API metrics", "POST /checkout p50: 210ms · p95: 12.4s · error rate: 8%\nOther endpoints p95: <400ms"],
      ["Application logs", "Prisma error P2024: Timed out fetching a new connection from the connection pool.\nPool limit: 10 · timeout: 10s"],
      ["Database activity", "9/10 connections: idle in transaction\nOldest transaction age: 14m 32s\nquery: SELECT ... FOR UPDATE"],
    ],
    diagnosis: "Leaked/long-lived checkout transactions exhaust the small connection pool and create intermittent queueing.",
    approach: ["Quantify impact and protect checkout: consider throttling, rollback, or traffic shaping.", "Correlate latency, errors, pool saturation, DB locks, and request traces by timestamp.", "Inspect transaction boundaries and the code path holding SELECT FOR UPDATE.", "Safely terminate confirmed stale sessions if needed, fix transaction cleanup, add timeouts, then monitor pool wait time."],
    update: "We’ve traced the slow checkouts to database connections being held open by a transaction path. We’re containing the queue now, then we’ll correct the transaction cleanup and monitor checkout latency and connection use after rollout.",
  },
  {
    category: "AI · Agent workflow",
    title: "The agent loops forever",
    difficulty: "Advanced",
    report: "Our research agent started calling the search tool repeatedly until requests time out. The same prompts worked last week.",
    prompt: "How would you debug a probabilistic workflow while controlling cost and customer impact?",
    evidence: [
      ["Trace excerpt", "step=7 tool=web_search args={query: 'Q2 revenue'}\nstep=8 tool=web_search args={query: 'Q2 revenue'}\nstep=9 tool=web_search args={query: 'Q2 revenue'}"],
      ["Recent change", "Prompt update removed: 'After receiving a search result, summarize it and do not repeat an identical tool call.'"],
      ["Orchestrator config", "max_steps: null\ntool_timeout_seconds: 30\nmodel: auto"],
    ],
    diagnosis: "A prompt regression exposed a missing orchestration guard: identical calls are allowed without a step/cost limit.",
    approach: ["Stop runaway executions and estimate affected runs, latency, and spend.", "Use traces to compare a failing run with a prior successful one, including prompt/model/tool outputs.", "Reproduce deterministically where possible and isolate prompt change from model/tool variability.", "Restore the instruction, but also add max steps, repeated-call detection, budgets, idempotency, and an actionable fallback."],
    update: "We’ve paused the looping workflow to prevent more delay and cost. A recent instruction change triggered repeated searches, and the workflow lacked a hard stop. We’ll restore the intended behavior and add execution limits so this failure mode cannot run indefinitely.",
  },
];

const scoreCategories = ["Problem framing", "Evidence & hypotheses", "Safe resolution", "Communication"];
const state = {
  current: 0,
  duration: 45 * 60,
  remaining: 45 * 60,
  running: false,
  timerId: null,
  notes: scenarios.map(() => ""),
  revealed: scenarios.map(() => []),
  scores: scenarios.map(() => [0, 0, 0, 0]),
  quick: false,
};

const $ = (id) => document.getElementById(id);
const welcome = $("welcome");
const interview = $("interview");
const results = $("results");
const workspace = document.querySelector(".workspace");

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem("incident-room-session"));
    if (saved?.notes?.length === scenarios.length) {
      state.notes = saved.notes;
      state.revealed = saved.revealed;
      state.scores = saved.scores;
    }
  } catch (_) { /* Ignore malformed local state. */ }
}

function persist() {
  localStorage.setItem("incident-room-session", JSON.stringify({
    notes: state.notes, revealed: state.revealed, scores: state.scores,
  }));
}

function startSession(quick = false) {
  state.quick = quick;
  state.duration = quick ? 8 * 60 : 45 * 60;
  state.remaining = state.duration;
  state.running = true;
  $("timerToggle").textContent = "Pause timer";
  welcome.classList.add("hidden");
  results.classList.add("hidden");
  interview.classList.remove("hidden");
  buildNav();
  renderScenario();
  startTimer();
}

function startTimer() {
  clearInterval(state.timerId);
  renderTimer();
  state.timerId = setInterval(() => {
    if (!state.running) return;
    state.remaining -= 1;
    renderTimer();
    if (state.remaining <= 0) finishSession();
  }, 1000);
}

function renderTimer() {
  const minutes = Math.floor(Math.max(0, state.remaining) / 60);
  const seconds = Math.max(0, state.remaining) % 60;
  $("timer").textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function buildNav() {
  $("scenarioNav").innerHTML = scenarios.map((scenario, index) => `
    <button class="nav-item ${index === state.current ? "active" : ""}" data-index="${index}">
      <span class="nav-number">${String(index + 1).padStart(2, "0")}</span>
      <span><strong>${scenario.title}</strong><small>${scenario.category.split(" · ")[0]}</small></span>
    </button>`).join("");
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => switchScenario(Number(button.dataset.index)));
  });
}

function switchScenario(index) {
  saveNotes();
  state.current = index;
  closeCoach();
  buildNav();
  renderScenario();
}

function renderScenario() {
  const scenario = scenarios[state.current];
  $("scenarioKicker").textContent = `Scenario ${state.current + 1} / ${scenarios.length} · ${scenario.category}`;
  $("scenarioTitle").textContent = scenario.title;
  $("difficulty").textContent = scenario.difficulty;
  $("customerReport").textContent = scenario.report;
  $("interviewerPrompt").textContent = scenario.prompt;
  $("notes").value = state.notes[state.current];
  $("previousButton").disabled = state.current === 0;
  $("nextButton").textContent = state.quick || state.current === scenarios.length - 1 ? "Finish session" : "Save & next";
  renderEvidence();
}

function renderEvidence() {
  const scenario = scenarios[state.current];
  const revealed = state.revealed[state.current];
  $("evidenceList").innerHTML = scenario.evidence.map(([label, value], index) => `
    <div>
      <button class="evidence-button" data-evidence="${index}">
        <span>${revealed.includes(index) ? "Evidence reviewed" : "Request"}: ${label}</span>
        <span>${revealed.includes(index) ? "−" : "+"}</span>
      </button>
      ${revealed.includes(index) ? `<pre class="evidence-value">${escapeHtml(value)}</pre>` : ""}
    </div>`).join("");
  document.querySelectorAll(".evidence-button").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.evidence);
      const list = state.revealed[state.current];
      state.revealed[state.current] = list.includes(index) ? list.filter((item) => item !== index) : [...list, index];
      persist();
      renderEvidence();
    });
  });
}

function escapeHtml(value) {
  return value.replace(/[&<>"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]);
}

function openCoach() {
  saveNotes();
  const scenario = scenarios[state.current];
  $("coachContent").innerHTML = `
    <div class="coach-section"><h4>Likely root cause</h4><ul><li>${scenario.diagnosis}</li></ul></div>
    <div class="coach-section"><h4>Strong investigation path</h4><ol>${scenario.approach.map((step) => `<li>${step}</li>`).join("")}</ol></div>
    <div class="coach-section"><h4>Customer-safe update</h4><div class="sample-update">“${scenario.update}”</div></div>`;
  renderScores();
  $("coach").classList.remove("hidden");
  workspace.classList.add("coach-open");
}

function closeCoach() {
  $("coach").classList.add("hidden");
  workspace.classList.remove("coach-open");
}

function renderScores() {
  $("scoreInputs").innerHTML = scoreCategories.map((category, index) => `
    <label class="score-row"><span>${category}</span><select data-score="${index}">
      ${[0,1,2,3,4,5].map((value) => `<option value="${value}" ${state.scores[state.current][index] === value ? "selected" : ""}>${value} / 5</option>`).join("")}
    </select></label>`).join("");
  document.querySelectorAll("[data-score]").forEach((select) => {
    select.addEventListener("change", () => {
      state.scores[state.current][Number(select.dataset.score)] = Number(select.value);
      persist();
      updateScoreTotal();
    });
  });
  updateScoreTotal();
}

function updateScoreTotal() {
  const total = state.scores[state.current].reduce((sum, score) => sum + score, 0);
  $("scoreTotal").textContent = `${total} / 20`;
}

function saveNotes() {
  state.notes[state.current] = $("notes").value;
  persist();
}

function finishSession() {
  saveNotes();
  state.running = false;
  clearInterval(state.timerId);
  interview.classList.add("hidden");
  results.classList.remove("hidden");
  const selected = state.quick ? [state.current] : scenarios.map((_, index) => index);
  const total = selected.reduce((sum, index) => sum + state.scores[index].reduce((a, b) => a + b, 0), 0);
  const possible = selected.length * 20;
  const percent = possible ? Math.round((total / possible) * 100) : 0;
  $("resultSummary").textContent = percent >= 75
    ? `You scored ${total}/${possible}. Your structure is interview-ready; focus next on making every diagnostic step falsifiable.`
    : `You scored ${total}/${possible}. Repeat the weaker scenarios and make your evidence requests, decision points, and customer updates more explicit.`;
  $("resultGrid").innerHTML = selected.map((index) => {
    const score = state.scores[index].reduce((a, b) => a + b, 0);
    return `<div class="result-card"><span>${scenarios[index].title}</span><strong>${score} / 20</strong></div>`;
  }).join("");
}

$("startButton").addEventListener("click", () => startSession(false));
$("quickButton").addEventListener("click", () => startSession(true));
$("timerToggle").addEventListener("click", () => {
  state.running = !state.running;
  $("timerToggle").textContent = state.running ? "Pause timer" : "Resume timer";
});
$("previousButton").addEventListener("click", () => switchScenario(Math.max(0, state.current - 1)));
$("nextButton").addEventListener("click", () => {
  if (state.quick || state.current === scenarios.length - 1) finishSession();
  else switchScenario(state.current + 1);
});
$("coachButton").addEventListener("click", openCoach);
$("closeCoach").addEventListener("click", closeCoach);
$("notes").addEventListener("input", saveNotes);
$("restartButton").addEventListener("click", () => {
  state.current = 0;
  startSession(false);
});

loadState();
