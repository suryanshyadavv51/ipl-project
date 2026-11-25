"""Statistics + the win-prediction model."""
import json
import math
from collections import defaultdict

import numpy as np
from sklearn.linear_model import LogisticRegression

FACTORS = ["Overall strength", "Recent form", "Head-to-head",
           "Venue record", "Toss won", "Toss decision"]


# ---------- prediction model ----------
class Tracker:
    """Keeps running records so every match is described using ONLY what was
    known before it was played (no peeking at the future)."""

    def __init__(self):
        self.w, self.p = defaultdict(int), defaultdict(int)
        self.form = defaultdict(list)
        self.h2h = defaultdict(int)          # (a, b) -> wins of a over b
        self.vw, self.vp = defaultdict(int), defaultdict(int)

    def _rate(self, t):
        return (self.w[t] + 5) / (self.p[t] + 10)

    def _form(self, t):
        f = self.form[t][-5:]
        return (sum(f) + 2.5) / (len(f) + 5)

    def _head(self, a, b):
        return (self.h2h[(a, b)] + 1) / (self.h2h[(a, b)] + self.h2h[(b, a)] + 2)

    def _venue(self, t, v):
        return (self.vw[(t, v)] + 1) / (self.vp[(t, v)] + 2)

    def features(self, a, b, venue, toss_winner, decision):
        """Team A minus team B. Swapping teams flips every sign, so the
        prediction is always fair to both sides."""
        toss = 1 if toss_winner == a else -1
        bat = 1 if str(decision).lower().startswith("bat") else -1
        return [self._rate(a) - self._rate(b),
                self._form(a) - self._form(b),
                self._head(a, b) - 0.5,
                self._venue(a, venue) - self._venue(b, venue),
                toss,
                toss * bat]

    def update(self, a, b, venue, winner):
        for t in (a, b):
            won = int(t == winner)
            self.p[t] += 1
            self.w[t] += won
            self.form[t].append(won)
            self.vp[(t, venue)] += 1
            self.vw[(t, venue)] += won
        loser = b if winner == a else a
        self.h2h[(winner, loser)] += 1


def _fit(X, y):
    m = LogisticRegression(fit_intercept=False, max_iter=1000)
    m.fit(np.vstack([X, -X]), np.concatenate([y, 1 - y]))  # mirror each match
    return m


def train(df):
    """Returns (model, tracker, test_accuracy, test_size)."""
    tr, X, y = Tracker(), [], []
    for r in df.itertuples():
        X.append(tr.features(r.team1, r.team2, r.venue, r.toss_winner, r.toss_decision))
        y.append(int(r.winner == r.team1))
        tr.update(r.team1, r.team2, r.venue, r.winner)
    X, y, seasons = np.array(X), np.array(y), df.season.to_numpy()

    acc, n = None, 0
    ss = sorted(set(seasons))
    if len(ss) >= 3:                      # test on the latest 2 seasons
        test = seasons >= ss[-2]
        n = int(test.sum())
        acc = float((_fit(X[~test], y[~test]).predict(X[test]) == y[test]).mean())
    return _fit(X, y), tr, acc, n


def predict(model, tr, a, b, venue, toss_winner, decision):
    x = np.array(tr.features(a, b, venue, toss_winner, decision))
    p = float(model.predict_proba([x])[0, 1])
    effect = model.coef_[0] * x
    return {"team1": a, "team2": b, "p1": round(p * 100, 1), "p2": round((1 - p) * 100, 1),
            "factors": [{"name": n, "effect": round(float(e), 3)} for n, e in zip(FACTORS, effect)]}


# ---------- statistics ----------
def _s(series):
    return {"labels": [str(i) for i in series.index], "values": [int(v) for v in series.values]}


def rows(m):
    out = m[["season", "date", "team1", "team2", "winner", "venue", "player_of_match"]].copy()
    out["date"] = out["date"].dt.strftime("%d %b %Y").fillna("")
    return json.loads(out.to_json(orient="records"))


def overview(df):
    toss_win = df.toss_winner == df.winner
    by_dec = toss_win.groupby(df.toss_decision).mean()
    players = df[df.player_of_match != ""].player_of_match.value_counts().head(8)
    return {
        "matches": len(df), "seasons": int(df.season.nunique()),
        "teams": len(set(df.team1) | set(df.team2)),
        "toss_win_pct": round(100 * float(toss_win.mean()), 1),
        "toss_by_decision": {k: round(100 * float(v), 1) for k, v in by_dec.items()},
        "per_season": _s(df.groupby("season").size()),
        "wins": _s(df.winner.value_counts()),
        "toss_decision": _s(df.toss_decision.value_counts()),
        "venues": _s(df.venue.value_counts().head(8)),
        "players": _s(players),
    }


def team(df, name):
    m = df[(df.team1 == name) | (df.team2 == name)]
    if m.empty:
        return None
    won = m.winner == name
    season = won.groupby(m.season).agg(["count", "sum"])
    opp_name = np.where(m.team1 == name, m.team2, m.team1)
    opp = won.groupby(opp_name).agg(["count", "sum"]).sort_values("count", ascending=False)
    return {
        "team": name, "played": len(m), "wins": int(won.sum()),
        "win_pct": round(100 * float(won.mean()), 1),
        "seasons": {"labels": [str(i) for i in season.index],
                    "played": [int(v) for v in season["count"]],
                    "won": [int(v) for v in season["sum"]]},
        "opponents": [{"opp": o, "played": int(r["count"]), "won": int(r["sum"])}
                      for o, r in opp.iterrows()],
        "venues": _s(m[won].venue.value_counts().head(5)),
    }


def head_to_head(df, a, b):
    m = df[((df.team1 == a) & (df.team2 == b)) | ((df.team1 == b) & (df.team2 == a))]
    return {"a": a, "b": b, "total": len(m),
            "wins_a": int((m.winner == a).sum()), "wins_b": int((m.winner == b).sum()),
            "recent": rows(m.tail(5).iloc[::-1])}


def matches(df, season="", team_name="", q="", page=1, per=15):
    m = df
    if season:
        m = m[m.season == int(season)]
    if team_name:
        m = m[(m.team1 == team_name) | (m.team2 == team_name)]
    if q:
        q = q.lower()
        hit = False
        for c in ["venue", "player_of_match", "winner", "team1", "team2"]:
            hit = hit | m[c].str.lower().str.contains(q, regex=False)
        m = m[hit]
    pages = max(1, math.ceil(len(m) / per))
    page = min(max(1, page), pages)
    part = m.iloc[::-1].iloc[(page - 1) * per: page * per]
    return {"total": len(m), "page": page, "pages": pages, "rows": rows(part)}
