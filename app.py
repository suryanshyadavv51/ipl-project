"""Flask backend: serves the website and the JSON API."""
import os

from flask import Flask, jsonify, render_template, request

import analysis as an
from data import load_matches

app = Flask(__name__)

DF, IS_SAMPLE = load_matches()
MODEL, TRACKER, ACCURACY, TEST_N = an.train(DF)

LAST = int(DF.season.max())
TEAMS = sorted(set(DF.team1) | set(DF.team2))
RECENT = DF[DF.season == LAST]
ACTIVE = sorted(set(RECENT.team1) | set(RECENT.team2))   # teams still playing
VENUES = sorted(DF.venue.unique())


def bad(msg, code=400):
    return jsonify(error=msg), code


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/meta")
def meta():
    return jsonify(sample=IS_SAMPLE, teams=TEAMS, active=ACTIVE, venues=VENUES,
                   seasons=sorted(int(s) for s in DF.season.unique()),
                   accuracy=None if ACCURACY is None else round(100 * ACCURACY, 1),
                   test_matches=TEST_N, total=len(DF))


@app.route("/api/overview")
def overview():
    return jsonify(an.overview(DF))


@app.route("/api/team/<name>")
def team(name):
    data = an.team(DF, name)
    return jsonify(data) if data else bad("Unknown team", 404)


@app.route("/api/h2h")
def h2h():
    a, b = request.args.get("a", ""), request.args.get("b", "")
    if a not in TEAMS or b not in TEAMS:
        return bad("Pick two teams.")
    if a == b:
        return bad("Pick two different teams.")
    return jsonify(an.head_to_head(DF, a, b))


@app.route("/api/matches")
def matches():
    try:
        page = int(request.args.get("page", 1))
        return jsonify(an.matches(DF, request.args.get("season", ""),
                                  request.args.get("team", ""),
                                  request.args.get("q", "").strip(), page))
    except ValueError:
        return bad("Invalid filter.")


@app.route("/api/predict", methods=["POST"])
def predict():
    d = request.get_json(silent=True) or {}
    t1, t2 = d.get("team1"), d.get("team2")
    toss, dec = d.get("toss_winner"), str(d.get("toss_decision", "")).lower()
    if t1 not in TEAMS or t2 not in TEAMS:
        return bad("Pick both teams.")
    if t1 == t2:
        return bad("Pick two different teams.")
    if toss not in (t1, t2):
        return bad("The toss winner must be one of the two teams.")
    if dec not in ("bat", "field"):
        return bad("Toss decision must be bat or field.")
    return jsonify(an.predict(MODEL, TRACKER, t1, t2, d.get("venue") or "", toss, dec))


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
