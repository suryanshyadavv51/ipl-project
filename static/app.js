const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const GREEN = "#14452F", RED = "#C8202F", SAGE = "#8aa399";
const charts = {};
let META = {}, mPage = 1;

async function get(url, opts) {
  const r = await fetch(url, opts);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || "Something went wrong.");
  return j;
}
function draw(id, type, labels, datasets, options = {}) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($("#" + id), { type, data: { labels, datasets },
    options: { responsive: true, maintainAspectRatio: false, ...options } });
}
function fill(sel, items, blank) {
  $(sel).innerHTML = (blank ? `<option value="">${esc(blank)}</option>` : "") +
    items.map(i => `<option>${esc(i)}</option>`).join("");
}
const stat = (v, l) => `<div class="stat"><b>${esc(v)}</b><span>${esc(l)}</span></div>`;
function table(el, head, rows) {
  $(el).innerHTML = `<tr>${head.map(h => `<th>${esc(h)}</th>`).join("")}</tr>` +
    (rows.length ? rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")
                 : `<tr><td colspan="${head.length}">No matches found. Try different filters.</td></tr>`);
}
const matchRows = rows => rows.map(r => [r.season, r.date, `${r.team1} vs ${r.team2}`, r.winner, r.venue, r.player_of_match]);
const MATCH_HEAD = ["Season", "Date", "Match", "Winner", "Venue", "Player of the match"];

/* ---------- dashboard ---------- */
async function loadDash() {
  const o = await get("/api/overview");
  $("#dstats").innerHTML = stat(o.matches, "matches with a result") + stat(o.seasons, "seasons") +
    stat(o.teams, "teams") + stat(o.toss_win_pct + "%", "of toss winners won the match");
  const noLegend = { plugins: { legend: { display: false } } };
  draw("c_season", "line", o.per_season.labels, [{ data: o.per_season.values, borderColor: GREEN, backgroundColor: GREEN, tension: .25 }], noLegend);
  draw("c_wins", "bar", o.wins.labels, [{ data: o.wins.values, backgroundColor: GREEN }], { ...noLegend, indexAxis: "y" });
  draw("c_venue", "bar", o.venues.labels, [{ data: o.venues.values, backgroundColor: RED }], { ...noLegend, indexAxis: "y" });
  draw("c_toss", "doughnut", o.toss_decision.labels, [{ data: o.toss_decision.values, backgroundColor: [GREEN, RED, SAGE] }],
       { plugins: { legend: { position: "bottom" } } });
  $("#toss-note").textContent = "Toss winners won: " +
    Object.entries(o.toss_by_decision).map(([k, v]) => `${v}% when they chose to ${k}`).join(", ") + ".";
  table("#players", ["Player", "Awards"], o.players.labels.map((l, i) => [l, o.players.values[i]]));
}

/* ---------- team analysis ---------- */
async function loadTeam() {
  const d = await get("/api/team/" + encodeURIComponent($("#t_sel").value));
  $("#tstats").innerHTML = stat(d.played, "matches played") + stat(d.wins, "wins") + stat(d.win_pct + "%", "win rate") +
    stat(d.venues.labels[0] || "-", "venue with most wins");
  draw("c_team", "bar", d.seasons.labels, [
    { label: "Played", data: d.seasons.played, backgroundColor: SAGE },
    { label: "Won", data: d.seasons.won, backgroundColor: GREEN }], { plugins: { legend: { position: "bottom" } } });
  table("#opp", ["Opponent", "Played", "Won", "Win rate"],
    d.opponents.map(o => [o.opp, o.played, o.won, Math.round(100 * o.won / o.played) + "%"]));
}

/* ---------- head to head ---------- */
async function loadH2H() {
  $("#h_err").textContent = "";
  try {
    const d = await get(`/api/h2h?a=${encodeURIComponent($("#h_a").value)}&b=${encodeURIComponent($("#h_b").value)}`);
    const pa = d.total ? 100 * d.wins_a / d.total : 50;
    $("#h_out").innerHTML = `<div class="out"><p class="sub">${d.total} matches played</p>
      <div class="score"><span>${esc(d.a)}</span><span>${d.wins_a}</span><small>to</small><span>${d.wins_b}</span><span>${esc(d.b)}</span></div>
      <div class="versus"><i class="a" style="width:${pa}%"></i><i class="b" style="width:${100 - pa}%"></i></div></div>
      <h3 style="margin:20px 0 8px">Last 5 meetings</h3><div class="table-wrap"><table id="h_tab"></table></div>`;
    table("#h_tab", MATCH_HEAD, matchRows(d.recent));
  } catch (e) { $("#h_out").innerHTML = ""; $("#h_err").textContent = e.message; }
}

/* ---------- predictor ---------- */
function syncToss() {
  const a = $("#p_a").value, b = $("#p_b").value;
  fill("#p_t", [a, b]);
}
async function runPredict() {
  $("#p_err").textContent = "";
  const body = { team1: $("#p_a").value, team2: $("#p_b").value, venue: $("#p_v").value,
                 toss_winner: $("#p_t").value, toss_decision: $("#p_d").value };
  try {
    const d = await get("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const max = Math.max(0.05, ...d.factors.map(f => Math.abs(f.effect)));
    $("#p_out").innerHTML = `<div class="out">
      <div class="pct"><span>${d.p1}%<small>${esc(d.team1)}</small></span><span>${d.p2}%<small>${esc(d.team2)}</small></span></div>
      <div class="versus"><i class="a" style="width:0" data-w="${d.p1}"></i><i class="b" style="width:0" data-w="${d.p2}"></i></div>
      <h3 style="margin:22px 0 4px">What drove this prediction</h3>
      ${d.factors.map(f => `<div class="factor"><span>${esc(f.name)}</span>
        <div class="${f.effect >= 0 ? "a" : "b"}" style="width:${Math.max(3, 100 * Math.abs(f.effect) / max)}%"></div>
        <span>${Math.abs(f.effect) < 0.005 ? "No effect" : "Favours " + esc(f.effect >= 0 ? d.team1 : d.team2)}</span></div>`).join("")}
      <p class="sub">${META.accuracy === null ? "" : `On the latest two seasons this model picked the winner ${META.accuracy}% of the time (${META.test_matches} matches). Cricket is hard to predict, so treat this as an estimate.`}</p></div>`;
    requestAnimationFrame(() => document.querySelectorAll("#p_out .versus i").forEach(i => i.style.width = i.dataset.w + "%"));
  } catch (e) { $("#p_out").innerHTML = ""; $("#p_err").textContent = e.message; }
}

/* ---------- match list ---------- */
async function loadMatches(page = 1) {
  const q = new URLSearchParams({ season: $("#m_s").value, team: $("#m_t").value, q: $("#m_q").value, page });
  const d = await get("/api/matches?" + q);
  mPage = d.page;
  table("#m_tab", MATCH_HEAD, matchRows(d.rows));
  $("#m_pg").textContent = `Page ${d.page} of ${d.pages} (${d.total} matches)`;
  $("#m_prev").disabled = d.page <= 1; $("#m_next").disabled = d.page >= d.pages;
}

/* ---------- start-up ---------- */
const loaded = {};
const loaders = { dash: loadDash, teams: loadTeam, h2h: loadH2H, matches: () => loadMatches(1) };
function show(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("on", v.id === view));
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("on", b.dataset.view === view));
  if (loaders[view] && !loaded[view]) { loaded[view] = true; loaders[view]().catch(e => alert(e.message)); }
}

(async function init() {
  META = await get("/api/meta");
  if (META.sample) {
    $("#banner").hidden = false;
    $("#banner").textContent = "You are looking at generated sample data, not real IPL results. Put the Kaggle file matches.csv in the data folder and restart the app to use real data.";
  }
  $("#model-note").textContent = `${META.total} matches loaded` + (META.sample ? " (sample data)" : "");
  fill("#t_sel", META.teams);
  fill("#h_a", META.teams); fill("#h_b", META.teams); $("#h_b").selectedIndex = Math.min(1, META.teams.length - 1);
  fill("#p_a", META.active); fill("#p_b", META.active); $("#p_b").selectedIndex = Math.min(1, META.active.length - 1);
  fill("#p_v", META.venues, "Neutral or unknown venue"); syncToss();
  fill("#m_s", [...META.seasons].reverse(), "All seasons"); fill("#m_t", META.teams, "All teams");

  document.querySelectorAll("#nav button").forEach(b => b.onclick = () => show(b.dataset.view));
  $("#t_sel").onchange = loadTeam;
  $("#h_go").onclick = loadH2H;
  $("#p_a").onchange = $("#p_b").onchange = syncToss;
  $("#p_go").onclick = runPredict;
  $("#m_go").onclick = () => loadMatches(1);
  $("#m_q").onkeydown = e => { if (e.key === "Enter") loadMatches(1); };
  $("#m_prev").onclick = () => loadMatches(mPage - 1);
  $("#m_next").onclick = () => loadMatches(mPage + 1);
  show("dash");
})().catch(e => { $("#banner").hidden = false; $("#banner").textContent = "Could not load data: " + e.message; });
