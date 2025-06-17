from flask import Flask, render_template, request, jsonify, redirect, url_for,render_template_string
import json, os
from datetime import date, datetime, timedelta
import tkinter as tk
from tkinter import simpledialog

import webbrowser
import threading



def open_browser():
    os.startfile("http://127.0.0.1:5000/")

app = Flask(__name__)

# ───────────────────── Storage ─────────────────────
os.makedirs('data', exist_ok=True)
DB_FILE = 'data/habits.json'
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w') as fp:
        json.dump({}, fp, indent=2)

# ╭────────────── File helpers ──────────────╮
def load_db():
    try:
        with open(DB_FILE) as fp:
            return json.load(fp)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_db(db):
    with open(DB_FILE, 'w') as fp:
        json.dump(db, fp, indent=2)

# ╭────────────── ISO‑week helpers ──────────────╮
def monday_of(year: int, week: int) -> date:
    return date.fromisocalendar(year, week, 1)

def iso_year_week(d: date) -> tuple[int, int]:
    y, w, _ = d.isocalendar()
    return y, w

# ╭────────────────── Seeding logic ─────────────────╮
def seed_missing_weeks(db: dict) -> bool:
    """
    Ensure every ISO week up to the current one exists.
    For each missing week, copy the habit names from the latest stored week
    and set all values to zeros.

    Returns True if the DB was modified.
    """
    today_year, today_week = iso_year_week(date.today())
    today_monday = monday_of(today_year, today_week)

    # If DB empty, create current week and exit
    if not db:
        db[str(today_year)] = {str(today_week): {}}
        return True

    # Find the latest stored week by actual date
    latest_date = max(
        monday_of(int(y), int(w))
        for y, weeks in db.items()
        for w in weeks
    )
    if latest_date >= today_monday:
        return False  # nothing missing

    latest_year, latest_week = iso_year_week(latest_date)
    template_habits = db[str(latest_year)][str(latest_week)]

    # Add blank weeks up to (and including) current week
    modified = False
    next_date = latest_date + timedelta(weeks=1)
    while next_date <= today_monday:
        y, w = iso_year_week(next_date)
        db.setdefault(str(y), {})[str(w)] = {h: [0] * 7 for h in template_habits}
        modified = True
        next_date += timedelta(weeks=1)

    return modified

# ╭────────────────── Misc helpers ──────────────────╮
# Open the file in read mode
#with open("./data/name.txt", "r",encoding="utf-8") as file:
#    USERNAME  = file.read()  # Reads the entire file



# Ensure the data folder exists
os.makedirs("data", exist_ok=True)

NAME_FILE = "data/name.txt"

# Ask for name only if the file is missing or empty
if not os.path.exists(NAME_FILE) or not open(NAME_FILE, encoding="utf-8").read().strip():
    root = tk.Tk()
    root.withdraw()
    name = simpledialog.askstring("Welcome!", "What's your name?")
    with open(NAME_FILE, "w", encoding="utf-8") as f:
        f.write(name.strip() if name else "User")

with open(NAME_FILE, "r", encoding="utf-8") as file:
    USERNAME = file.read().strip()











def greeting() -> str:
    h = datetime.now().hour
    if 22 <= h or h < 4:
        msg = "haven't you slept yet?"
    elif h < 12:
        msg = "good morning!"
    elif h < 17:
        msg = "good afternoon!"
    else:
        msg = "good evening!"
    return f"Hi {USERNAME}, {msg}"

def year_week_from_offset(week_offset: int):
    target = date.today() + timedelta(weeks=week_offset)
    y, w, _ = target.isocalendar()
    return y, w, monday_of(y, w)

def ensure_week(db: dict, year: int, week: int):
    db.setdefault(str(year), {}).setdefault(str(week), {})
    return db

def get_week_habits(year: int, week: int):
    return load_db().get(str(year), {}).get(str(week), {})

def best_and_current_streak(db: dict, habit: str):
    if not db:
        return 0, 0
    first_seen = last_seen = None
    for y, weeks in db.items():
        for w, habits in weeks.items():
            if habit in habits:
                mon = monday_of(int(y), int(w))
                first_seen = mon if first_seen is None else min(first_seen, mon)
                last_seen = mon if last_seen is None else max(last_seen, mon)
    if first_seen is None:
        return 0, 0

    best = cur = run = 0
    today = date.today()
    d = first_seen
    while d <= last_seen + timedelta(days=6):
        y, w, dow = d.isocalendar()
        week_vals = db.get(str(y), {}).get(str(w), {}).get(habit, [0] * 7)
        run = run + 1 if week_vals[dow - 1] else 0
        best = max(best, run)
        if d == today:
            cur = run
        d += timedelta(days=1)
    return best, cur

def build_heatmap(days: int = 42, offset_days: int = 0):
    """
    Build a matrix dataset for the last `days` days (default 42 = 6 weeks).
    """
    db = load_db()
    today = date.today()
    end = today - timedelta(days=offset_days)
    start = end - timedelta(days=days - 1)
    daily = {start + timedelta(days=i): 0 for i in range(days)}
    for y, weeks in db.items():
        for w, habits in weeks.items():
            mon = monday_of(int(y), int(w))
            for i in range(7):
                d = mon + timedelta(days=i)
                if d in daily:
                    daily[d] += sum(h[i] for h in habits.values())
    first_mon = start - timedelta(days=start.weekday())
    return [
        {
            "x": (d - first_mon).days // 7,
            "y": d.weekday(),
            "v": v,
            "label": d.strftime("%d %b"),
        }
        for d, v in daily.items()
    ]

def weekly_completion_percent(habits: dict) -> int:
    total = sum(sum(v) for v in habits.values())
    possible = len(habits) * 7 if habits else 0
    return round(total / possible * 100) if possible else 0

def monthly_completion_percent(db: dict, year: int, month: int) -> int:
    total = possible = 0
    for w, habits in db.get(str(year), {}).items():
        mon = monday_of(year, int(w))
        for idx in range(7):
            d = mon + timedelta(days=idx)
            if d.month != month:
                continue
            for vals in habits.values():
                total += vals[idx]
                possible += 1
    return round(total / possible * 100) if possible else 0

def heatmap_month_label(offset_days: int = 0, span: int = 42) -> str:
    """
    Pretty label for the heat‑map date range.
    """
    today = date.today()
    end = today - timedelta(days=offset_days)
    start = end - timedelta(days=span - 1)
    if start.year == end.year:
        if start.month == end.month:
            return start.strftime("%B %Y")
        return f"{start.strftime('%b')}–{end.strftime('%b %Y')}"
    return f"{start.strftime('%b %Y')}–{end.strftime('%b %Y')}"

# ───────────────────────── Routes ─────────────────────────
@app.route("/")
def index():
    week_offset = int(request.args.get("week", 0))
    heat_offset = int(request.args.get("offset", 0))

    db = load_db()
    if seed_missing_weeks(db):
        save_db(db)

    year, week, mon_base = year_week_from_offset(week_offset)
    week_dates = [mon_base + timedelta(days=i) for i in range(7)]
    today = date.today()

    habits = db.get(str(year), {}).get(str(week), {})

    # Redirect to add page if current week has no habits
    if week_offset == 0 and not habits:
        return redirect(url_for("add_habit"))

    completion_rates = {h: round(sum(v) / 7 * 100) for h, v in habits.items()}

    best_streaks, current_streaks = {}, {}
    for h in habits:
        best, cur = best_and_current_streak(db, h)
        best_streaks[h] = best
        current_streaks[h] = cur

    week_percent = weekly_completion_percent(habits)
    month_percent = monthly_completion_percent(db, year, week_dates[0].month)
    heatmap_points = build_heatmap(offset_days=heat_offset)
    heatmap_label = heatmap_month_label(heat_offset)

    return render_template(
        "index.html",
        greet=greeting(),
        today_str=today.strftime("%A, %d %b %Y"),
        habits=habits,
        week_dates=week_dates,
        today=today,
        week_offset=week_offset,
        heat_offset=heat_offset,
        completion_rates=completion_rates,
        current_streaks=current_streaks,
        best_streaks=best_streaks,
        heatmap_points=heatmap_points,
        week_percent=week_percent,
        month_percent=month_percent,
        year_display=year,
        week_display=week,
        heatmap_label=heatmap_label,
    )

@app.route("/update_habit", methods=["POST"])
def update_habit():
    data = request.get_json(force=True)
    habit = data["habit"]
    day = int(data["day"])
    status = int(data["status"])
    year = int(data["year"])
    week = int(data["week"])

    db = load_db()
    ensure_week(db, year, week)
    db[str(year)][str(week)].setdefault(habit, [0] * 7)
    db[str(year)][str(week)][habit][day] = status
    save_db(db)
    return jsonify(success=True)

@app.route("/add", methods=["GET", "POST"])
def add_habit():
    if request.method == "POST":
        name = request.form["habit_name"].strip()
        if name:
            y, w, _ = year_week_from_offset(0)
            db = load_db()
            ensure_week(db, y, w)
            db[str(y)][str(w)].setdefault(name, [0] * 7)
            save_db(db)
        return redirect(url_for("index"))
    return render_template("add_habit.html")

@app.route("/delete", methods=["GET", "POST"])
def delete_habit():
    y, w, _ = year_week_from_offset(0)
    db = load_db()
    habits = db.get(str(y), {}).get(str(w), {})
    if request.method == "POST":
        name = request.form["habit_name"]
        habits.pop(name, None)
        save_db(db)
        return redirect(url_for("index"))
    return render_template("delete_habit.html", habits=habits)


if __name__ == "__main__":
    open_browser()
    app.run(debug=False, use_reloader=False)
