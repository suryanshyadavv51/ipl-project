# IPL Cricket Data Analysis and Prediction

A full-stack mini project: Python backend (Flask + pandas + scikit-learn) and a browser frontend (HTML, CSS, JavaScript, Chart.js).

## What it does
- **Dashboard**: matches per season, wins by team, busiest venues, toss statistics, top player-of-the-match winners
- **Team analysis**: any team's record by season and against every opponent
- **Head to head**: wins for each side and the last 5 meetings
- **Match predictor**: pick two teams, venue, toss winner and decision, then get each team's win probability and see which factors drove it
- **All matches**: filter by season/team and search by venue or player

## Run it (VS Code, step by step)
1. Install Python 3.10 or newer from python.org. On Windows, tick **Add Python to PATH** in the installer.
2. In VS Code choose **File > Open Folder** and open the `ipl-project` folder.
3. Open a terminal with **Terminal > New Terminal** and run these one at a time:
   ```
   python -m venv venv
   venv\Scripts\activate          (Windows)
   source venv/bin/activate       (Mac or Linux)
   pip install -r requirements.txt
   python app.py
   ```
4. Open **http://127.0.0.1:5000** in your browser. Stop the server with `Ctrl + C`.

You need internet the first time you open the page, because the chart library and fonts load from a CDN.

## Use real IPL data
The project starts with a **generated sample dataset**, and the page shows a yellow banner saying so. The sample results are not real. To use real data:
1. Download `matches.csv` from the Kaggle "IPL Complete Dataset" (search Kaggle for "IPL matches deliveries").
2. Put it in the `data` folder, named exactly `matches.csv`.
3. Restart `python app.py`. The banner disappears.

The loader needs these columns: `team1, team2, toss_winner, toss_decision, winner, venue` (plus `date` or `season`). `player_of_match` and `city` are optional. Old team names (Delhi Daredevils, Kings XI Punjab, Royal Challengers Bangalore) are renamed to their current names, and matches with no result are skipped.

## Files
| File | Job |
|---|---|
| `app.py` | Flask server: the web page and the `/api/...` endpoints |
| `data.py` | Loads and cleans the CSV, creates the sample data |
| `analysis.py` | Statistics functions and the prediction model |
| `templates/index.html` | The page layout |
| `static/style.css` | Styling |
| `static/app.js` | Calls the API and draws charts and tables |

## API
| Endpoint | Returns |
|---|---|
| `GET /api/meta` | Teams, venues, seasons, model accuracy, sample-data flag |
| `GET /api/overview` | Dashboard numbers |
| `GET /api/team/<name>` | One team's record |
| `GET /api/h2h?a=...&b=...` | Head-to-head result |
| `GET /api/matches?season=&team=&q=&page=` | Filtered match list |
| `POST /api/predict` | Body: `team1, team2, venue, toss_winner, toss_decision` (`bat` or `field`) |

If your group builds its own backend, the frontend only needs these endpoints to return the same JSON shape.

## How the prediction works (for your viva)
1. Matches are processed in date order. Before each match, the code records what was known *at that time*: each team's overall win rate, last-5-match form, head-to-head record, and record at that venue (all lightly smoothed so tiny samples do not swing wildly).
2. For each match it computes "Team 1 minus Team 2" for those four numbers, plus whether Team 1 won the toss and whether the toss winner chose to bat.
3. A **logistic regression** learns how much each factor matters. Every match is also added with the teams swapped, so the model is fair to both sides.
4. Accuracy is measured honestly: the model is trained on older seasons and tested on the **latest two seasons** it has not seen. Real IPL results are close to a coin flip, so expect roughly 55 to 60 percent on real data, not 90.

Ideas to extend it: add `deliveries.csv` for batsman and bowler stats, a Random Forest to compare against logistic regression, a "live" predictor for upcoming fixtures.
