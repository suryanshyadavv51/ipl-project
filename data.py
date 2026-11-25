"""Loads and cleans IPL match data.

If data/matches.csv exists (the Kaggle IPL file) it is used.
Otherwise a SAMPLE dataset is generated so the app still runs.
"""
import math
import os
import random
from datetime import datetime, timedelta

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
REAL = os.path.join(BASE, "data", "matches.csv")
SAMPLE = os.path.join(BASE, "data", "sample_matches.csv")

# Old franchise names -> current names, so one team is not split in two.
RENAME = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
}

HOME = {
    "Chennai Super Kings": ("Chennai", "MA Chidambaram Stadium"),
    "Mumbai Indians": ("Mumbai", "Wankhede Stadium"),
    "Kolkata Knight Riders": ("Kolkata", "Eden Gardens"),
    "Royal Challengers Bengaluru": ("Bengaluru", "M Chinnaswamy Stadium"),
    "Delhi Capitals": ("Delhi", "Arun Jaitley Stadium"),
    "Punjab Kings": ("Mohali", "PCA Stadium"),
    "Rajasthan Royals": ("Jaipur", "Sawai Mansingh Stadium"),
    "Sunrisers Hyderabad": ("Hyderabad", "Rajiv Gandhi Stadium"),
    "Gujarat Titans": ("Ahmedabad", "Narendra Modi Stadium"),
    "Lucknow Super Giants": ("Lucknow", "Ekana Stadium"),
}


def make_sample(path):
    """Fake-but-realistic matches (NOT real IPL results). Fixed seed."""
    rnd = random.Random(7)
    teams = list(HOME)
    strength = {t: rnd.gauss(0, 0.5) for t in teams}
    rows, mid = [], 1
    for season in range(2008, 2025):
        active = teams[:8] if season < 2022 else teams
        pairs = [(a, b) for a in active for b in active if a != b]
        rnd.shuffle(pairs)
        pairs = pairs[: 56 if season < 2022 else 74]
        start = datetime(season, 3, 26)
        for i, (a, b) in enumerate(pairs):
            city, venue = HOME[a]
            toss = rnd.choice([a, b])
            decision = "field" if rnd.random() < 0.65 else "bat"
            edge = strength[a] - strength[b] + 0.25 + (0.1 if toss == a else -0.1)
            win = a if rnd.random() < 1 / (1 + math.exp(-edge)) else b
            abbr = "".join(w[0] for w in win.split())
            rows.append(dict(
                id=mid, season=season, city=city,
                date=(start + timedelta(days=i)).strftime("%Y-%m-%d"),
                team1=a, team2=b, toss_winner=toss, toss_decision=decision,
                winner=win, venue=venue,
                player_of_match=f"{abbr} Player {rnd.randint(1, 11)}"))
            mid += 1
    pd.DataFrame(rows).to_csv(path, index=False)


def load_matches():
    """Returns (DataFrame, is_sample)."""
    is_sample = not os.path.exists(REAL)
    if is_sample and not os.path.exists(SAMPLE):
        make_sample(SAMPLE)
    df = pd.read_csv(SAMPLE if is_sample else REAL)
    df.columns = [c.strip().lower() for c in df.columns]

    need = ["team1", "team2", "toss_winner", "toss_decision", "winner", "venue"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"matches.csv is missing columns: {missing}")

    for c in ["team1", "team2", "toss_winner", "winner"]:
        df[c] = df[c].replace(RENAME)
    for c in ["city", "player_of_match"]:
        df[c] = df[c].fillna("") if c in df.columns else ""
    if "id" not in df.columns:
        df["id"] = range(len(df))

    df["date"] = pd.to_datetime(df["date"], errors="coerce") if "date" in df.columns else pd.NaT
    guess = pd.Series(float("nan"), index=df.index)
    if "season" in df.columns:  # handles "2007/08" style too
        s = df["season"].astype(str)
        guess = s.str.extract(r"(\d{4})")[0].astype(float) + s.str.contains("/").astype(int)
    df["season"] = df["date"].dt.year.fillna(guess)
    df = df.dropna(subset=["season"])
    df["season"] = df["season"].astype(int)

    # keep only matches that had a winner (drops no-result / abandoned)
    df = df[(df.winner == df.team1) | (df.winner == df.team2)]
    df["toss_decision"] = df["toss_decision"].astype(str).str.lower()
    df = df.sort_values(["season", "date", "id"]).reset_index(drop=True)
    return df, is_sample
