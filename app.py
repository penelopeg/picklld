import gradio as gr
import sqlite3
import os
import shutil
from datetime import datetime
import pandas as pd

DB_PATH = "pickldd.db"
UPLOADS_DIR = "uploads"


def init_db():
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pickle_name TEXT    NOT NULL,
            brand       TEXT    DEFAULT '',
            overall     INTEGER NOT NULL,
            crunchiness INTEGER NOT NULL,
            sourness    INTEGER NOT NULL,
            garlic      INTEGER NOT NULL,
            review_text TEXT    DEFAULT '',
            photo_path  TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def save_photo(tmp_path, pickle_name):
    if not tmp_path:
        return None
    try:
        ext = os.path.splitext(tmp_path)[1] or ".jpg"
        safe = "".join(c for c in pickle_name if c.isalnum() or c in "-_ ")[:30].strip()
        dest = os.path.join(UPLOADS_DIR, f"{datetime.now():%Y%m%d_%H%M%S}_{safe}{ext}")
        shutil.copy2(tmp_path, dest)
        return dest
    except Exception:
        return None


def submit_review(pickle_name, brand, overall, crunchiness, sourness, garlic, review_text, photo):
    if not pickle_name or not pickle_name.strip():
        return "⚠️ Please enter a pickle name!", get_leaderboard_html()

    photo_path = save_photo(photo, pickle_name)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO reviews
           (pickle_name, brand, overall, crunchiness, sourness, garlic, review_text, photo_path)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            pickle_name.strip(),
            (brand or "").strip(),
            int(overall),
            int(crunchiness),
            int(sourness),
            int(garlic),
            (review_text or "").strip(),
            photo_path,
        ),
    )
    conn.commit()
    conn.close()
    return "✅ Pickled! Your review is brined and bottled. 🥒", get_leaderboard_html()


SORT_OPTIONS = ["⭐ Overall", "🔊 Crunchiness", "😬 Sourness", "🧄 Garlic", "📝 Reviews"]
_SORT_COLS = {
    "⭐ Overall":      "avg_overall",
    "🔊 Crunchiness": "avg_crunch",
    "😬 Sourness":    "avg_sour",
    "🧄 Garlic":      "avg_garlic",
    "📝 Reviews":     "review_count",
}


def _query_leaderboard(sort_by="⭐ Overall"):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT
            pickle_name,
            COALESCE(NULLIF(TRIM(brand), ''), '—') AS brand,
            ROUND(AVG(CAST(overall     AS REAL)), 1) AS avg_overall,
            ROUND(AVG(CAST(crunchiness AS REAL)), 1) AS avg_crunch,
            ROUND(AVG(CAST(sourness    AS REAL)), 1) AS avg_sour,
            ROUND(AVG(CAST(garlic      AS REAL)), 1) AS avg_garlic,
            COUNT(*)                                  AS review_count
        FROM reviews
        GROUP BY pickle_name, brand
        """,
        conn,
    )
    conn.close()
    if df.empty:
        return df
    sort_col = _SORT_COLS.get(sort_by, "avg_overall")
    df = df.sort_values(sort_col, ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


def _score_bar(val):
    pct = int((float(val) / 10) * 100)
    color = "#52a81e" if float(val) >= 7 else "#f59e0b" if float(val) >= 4 else "#ef4444"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:8px;">'
        f'<span style="background:#e5e7eb;border-radius:4px;height:6px;width:56px;'
        f'display:inline-block;vertical-align:middle;">'
        f'<span style="background:{color};border-radius:4px;height:6px;width:{pct}%;'
        f'display:block;"></span></span>'
        f'<span style="font-weight:700;color:{color};min-width:18px;">{val}</span>'
        f'</span>'
    )


def get_leaderboard_html(sort_by="⭐ Overall"):
    df = _query_leaderboard(sort_by)

    if df.empty:
        return """
        <div class="lb-empty">
            <div style="font-size:4rem;margin-bottom:12px;">🥒</div>
            <h3 style="margin:0 0 8px;font-size:1.2rem;color:#1a2e0e;font-weight:700;">
                No pickles ranked yet!
            </h3>
            <p style="margin:0;color:#6b7280;font-size:0.95rem;">
                Be the first to rate a pickle and claim the top spot. 🏆
            </p>
        </div>
        """

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    row_classes = {1: "rank-gold", 2: "rank-silver", 3: "rank-bronze"}

    rows_html = ""
    for _, row in df.iterrows():
        rank = int(row["rank"])
        medal = medals.get(
            rank,
            f'<span style="color:#9ca3af;font-weight:700;font-size:0.85rem;">{rank}</span>',
        )
        row_cls = row_classes.get(rank, "")
        n = int(row["review_count"])
        review_label = f'{n} {"review" if n == 1 else "reviews"}'

        rows_html += f"""
        <tr class="lb-row {row_cls}">
            <td class="lb-rank">{medal}</td>
            <td class="lb-name"><span class="pickle-pill">{row['pickle_name']}</span></td>
            <td class="lb-brand">{row['brand']}</td>
            <td class="lb-score">{_score_bar(row['avg_overall'])}</td>
            <td class="lb-score">{_score_bar(row['avg_crunch'])}</td>
            <td class="lb-score">{_score_bar(row['avg_sour'])}</td>
            <td class="lb-score">{_score_bar(row['avg_garlic'])}</td>
            <td><span class="review-badge">{review_label}</span></td>
        </tr>
        """

    return f"""
    <div class="lb-wrapper">
        <table class="lb-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>🥒 Pickle</th>
                    <th>Brand</th>
                    <th>⭐ Overall</th>
                    <th>🔊 Crunch</th>
                    <th>😬 Sour</th>
                    <th>🧄 Garlic</th>
                    <th>Reviews</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """


def get_recent_html():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT pickle_name, brand, overall, crunchiness, sourness, garlic,
               review_text, SUBSTR(created_at, 1, 10) AS date
        FROM reviews ORDER BY id DESC LIMIT 20
        """,
        conn,
    )
    conn.close()

    if df.empty:
        return (
            '<p style="text-align:center;color:#9ca3af;padding:40px 32px;font-size:0.95rem;">'
            "No reviews yet — go rate some pickles! 🥒</p>"
        )

    cards = ""
    for _, r in df.iterrows():
        brand_clean = str(r["brand"]).strip()
        brand_html = (
            f'<span class="review-brand">· {brand_clean}</span>'
            if brand_clean and brand_clean != "—"
            else ""
        )
        body_html = (
            f'<p class="review-body">"{r["review_text"]}"</p>'
            if r["review_text"] and str(r["review_text"]).strip()
            else ""
        )
        cards += f"""
        <div class="review-card">
            <div class="review-card-header">
                <div>
                    <span class="review-pickle-name">{r['pickle_name']}</span>
                    {brand_html}
                </div>
                <span class="review-date">{r['date']}</span>
            </div>
            <div class="review-scores">
                <span class="score-chip">⭐ {r['overall']}</span>
                <span class="score-chip">🔊 {r['crunchiness']}</span>
                <span class="score-chip">😬 {r['sourness']}</span>
                <span class="score-chip">🧄 {r['garlic']}</span>
            </div>
            {body_html}
        </div>
        """

    return f'<div class="reviews-grid">{cards}</div>'


init_db()


CSS = """
/* ── Design tokens ── */
:root {
    --pkl-dark:   #1a3d0a;
    --pkl-mid:    #2e7012;
    --pkl-bright: #52a81e;
    --pkl-light:  #a8e063;
    --pkl-pale:   #edf7e2;
    --pkl-brine:  #f4fbed;
    --gold:       #f59e0b;
    --silver:     #94a3b8;
    --bronze:     #b45309;
    --surface:    #f5faf0;
    --card-bg:    #ffffff;
    --border:     rgba(82,168,30,0.18);
    --text:       #1a2e0e;
    --muted:      #6b7280;
    --r-sm:       10px;
    --r-md:       16px;
    --r-lg:       24px;
    --sh-sm:      0 1px 3px rgba(0,0,0,0.07), 0 2px 8px rgba(0,0,0,0.04);
    --sh-md:      0 4px 12px rgba(0,0,0,0.09), 0 8px 24px rgba(0,0,0,0.05);
    --sh-lg:      0 8px 32px rgba(0,0,0,0.11), 0 16px 48px rgba(0,0,0,0.06);
}

/* ── Global ── */
body, .main, .gradio-container {
    background: var(--surface) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.gradio-container {
    max-width: 960px !important;
    margin: 0 auto !important;
    padding: 0 16px 40px !important;
}

/* ── Hero ── */
.hero {
    position: relative;
    background: linear-gradient(140deg, #0c1f05 0%, #1a3d0a 35%, #2e7012 70%, #3d8b1a 100%);
    border-radius: var(--r-lg);
    padding: 56px 32px 48px;
    margin: 24px 0 20px;
    text-align: center;
    overflow: hidden;
    box-shadow: var(--sh-lg);
}

.hero::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(168,224,99,0.13) 0%, transparent 70%);
    pointer-events: none;
}

.hero::after {
    content: '';
    position: absolute;
    bottom: -60px; left: -60px;
    width: 240px; height: 240px;
    background: radial-gradient(circle, rgba(82,168,30,0.10) 0%, transparent 70%);
    pointer-events: none;
}

.hero-icon {
    display: block;
    font-size: 5rem;
    line-height: 1;
    margin-bottom: 16px;
    filter: drop-shadow(0 4px 16px rgba(0,0,0,0.35));
    animation: bob 3.5s ease-in-out infinite;
}

@keyframes bob {
    0%, 100% { transform: translateY(0px) rotate(-2deg); }
    50%       { transform: translateY(-10px) rotate(2deg); }
}

.hero-title {
    font-size: 3.8rem;
    font-weight: 900;
    letter-spacing: -2.5px;
    color: #ffffff;
    margin: 0 0 10px;
    line-height: 1;
    text-shadow: 0 2px 20px rgba(0,0,0,0.4);
}

.hero-title .accent {
    background: linear-gradient(135deg, #d4f582 0%, #a8e063 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-sub {
    color: rgba(255,255,255,0.75);
    font-size: 1.05rem;
    margin: 0 0 28px;
    font-weight: 400;
    letter-spacing: 0.2px;
}

.hero-tags {
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 10px;
}

.hero-tag {
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.18);
    color: rgba(255,255,255,0.88);
    padding: 6px 16px;
    border-radius: 100px;
    font-size: 0.83rem;
    font-weight: 500;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.18s;
}

.hero-tag:hover {
    background: rgba(255,255,255,0.17);
}

/* ── Tabs ── */
.tabs { margin-top: 0 !important; }

.tab-nav {
    background: var(--card-bg) !important;
    border-radius: var(--r-md) !important;
    padding: 6px !important;
    border: 1px solid var(--border) !important;
    gap: 6px !important;
    box-shadow: var(--sh-sm) !important;
    margin-bottom: 20px !important;
}

.tab-nav button {
    font-weight: 600 !important;
    font-size: 0.93rem !important;
    border-radius: var(--r-sm) !important;
    padding: 10px 28px !important;
    transition: all 0.2s ease !important;
    color: var(--muted) !important;
    border: none !important;
}

.tab-nav button.selected {
    background: linear-gradient(135deg, var(--pkl-mid) 0%, var(--pkl-bright) 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 2px 10px rgba(46,112,18,0.38) !important;
}

/* ── Form cards (gr.Group with elem_classes="pkl-card") ── */
.pkl-card,
.pkl-card.form,
.pkl-card > .form {
    background: var(--card-bg) !important;
    border-radius: var(--r-md) !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--sh-sm) !important;
    padding: 22px 24px !important;
    margin-bottom: 14px !important;
    transition: box-shadow 0.2s ease !important;
}

.pkl-card:hover,
.pkl-card.form:hover {
    box-shadow: var(--sh-md) !important;
}

/* Prevent double-border from nested Gradio wrappers */
.pkl-card > .form {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* ── Section titles (inside cards) ── */
.card-section-title {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: var(--pkl-mid);
    margin: 0 0 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.card-section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right, rgba(82,168,30,0.25), transparent);
    margin-left: 4px;
}

/* ── Rating hint ── */
.rating-hint p, .rating-hint {
    color: var(--muted) !important;
    font-size: 0.85rem !important;
    margin: 0 0 12px !important;
}

/* ── Sliders ── */
input[type="range"] {
    accent-color: var(--pkl-bright) !important;
    height: 6px !important;
}

/* ── Submit button ── */
#submit-btn {
    background: linear-gradient(135deg, var(--pkl-mid) 0%, var(--pkl-bright) 100%) !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    font-size: 1.08rem !important;
    border-radius: var(--r-md) !important;
    border: none !important;
    padding: 16px 40px !important;
    width: 100% !important;
    margin-top: 10px !important;
    box-shadow: 0 4px 18px rgba(46,112,18,0.42) !important;
    transition: all 0.22s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    letter-spacing: 0.3px !important;
}

#submit-btn:hover {
    transform: translateY(-3px) scale(1.01) !important;
    box-shadow: 0 8px 28px rgba(46,112,18,0.52) !important;
}

#submit-btn:active {
    transform: translateY(0) scale(0.99) !important;
}

/* ── Status message ── */
#status-box {
    border-radius: var(--r-sm) !important;
    border: 1px solid var(--border) !important;
    background: var(--pkl-pale) !important;
    margin-top: 10px !important;
    overflow: hidden !important;
}

#status-box textarea {
    text-align: center !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    color: var(--pkl-dark) !important;
    resize: none !important;
    background: transparent !important;
    border: none !important;
    min-height: 0 !important;
    padding: 12px !important;
}

/* ── Leaderboard HTML table ── */
.lb-wrapper {
    overflow-x: auto;
    border-radius: var(--r-md);
    box-shadow: var(--sh-md);
    border: 1px solid var(--border);
    background: var(--card-bg);
}

.lb-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
    color: var(--text);
}

.lb-table thead tr {
    background: linear-gradient(135deg, #0f2405 0%, var(--pkl-dark) 50%, var(--pkl-mid) 100%);
}

.lb-table thead th {
    color: rgba(255,255,255,0.88);
    font-weight: 700;
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    padding: 14px 16px;
    text-align: left;
    white-space: nowrap;
}

.lb-table tbody tr {
    border-bottom: 1px solid #f0f4ec;
    transition: background 0.15s ease;
}

.lb-table tbody tr:last-child { border-bottom: none; }
.lb-table tbody tr:hover      { background: var(--pkl-brine) !important; }

.lb-table tbody tr.rank-gold   { background: #fffdf0; }
.lb-table tbody tr.rank-silver { background: #f9fafb; }
.lb-table tbody tr.rank-bronze { background: #fff8f0; }

.lb-table td { padding: 13px 16px; vertical-align: middle; }

.lb-rank {
    font-size: 1.35rem;
    text-align: center;
    width: 52px;
}

.pickle-pill {
    display: inline-block;
    background: var(--pkl-pale);
    color: var(--pkl-dark);
    font-weight: 600;
    font-size: 0.88rem;
    padding: 4px 13px;
    border-radius: 100px;
    border: 1px solid rgba(82,168,30,0.22);
    white-space: nowrap;
}

.lb-brand { color: var(--muted); font-size: 0.84rem; }

.review-badge {
    display: inline-block;
    background: var(--pkl-pale);
    color: var(--pkl-mid);
    font-weight: 700;
    font-size: 0.8rem;
    padding: 4px 12px;
    border-radius: 100px;
    border: 1px solid var(--border);
    white-space: nowrap;
}

.lb-empty {
    text-align: center;
    padding: 64px 32px;
    color: var(--muted);
    background: var(--card-bg);
    border-radius: var(--r-md);
    border: 2px dashed rgba(82,168,30,0.25);
}

/* ── Leaderboard section heading ── */
.lb-section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text);
    margin: 28px 0 14px;
}

.lb-section-title::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 1em;
    background: linear-gradient(180deg, var(--pkl-bright), var(--pkl-mid));
    border-radius: 2px;
    flex-shrink: 0;
}

/* ── Recent reviews grid ── */
.reviews-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
    gap: 14px;
}

.review-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    padding: 16px 18px;
    box-shadow: var(--sh-sm);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.review-card:hover {
    box-shadow: var(--sh-md);
    transform: translateY(-2px);
}

.review-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 10px;
}

.review-pickle-name {
    font-weight: 700;
    font-size: 0.93rem;
    color: var(--pkl-dark);
}

.review-brand {
    font-size: 0.78rem;
    color: var(--muted);
    margin-left: 4px;
}

.review-date {
    font-size: 0.74rem;
    color: var(--muted);
    white-space: nowrap;
    margin-top: 2px;
}

.review-scores {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
}

.score-chip {
    background: var(--pkl-pale);
    color: var(--pkl-dark);
    border: 1px solid rgba(82,168,30,0.2);
    border-radius: 100px;
    font-size: 0.77rem;
    font-weight: 600;
    padding: 3px 10px;
}

.review-body {
    font-size: 0.84rem;
    color: var(--muted);
    font-style: italic;
    margin: 8px 0 0;
    line-height: 1.55;
    border-left: 3px solid var(--border);
    padding-left: 10px;
}

/* ── Sort controls card ── */
.sort-card,
.sort-card.form,
.sort-card > .form {
    background: var(--card-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    box-shadow: var(--sh-sm) !important;
    padding: 14px 20px !important;
    margin-bottom: 16px !important;
}

.sort-card > .form {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* ── Mobile ── */
@media (max-width: 640px) {
    .hero {
        padding: 40px 20px 36px;
        border-radius: var(--r-md);
        margin: 12px 0 16px;
    }
    .hero-title  { font-size: 2.7rem; letter-spacing: -1.5px; }
    .hero-icon   { font-size: 3.8rem; }
    .hero-sub    { font-size: 0.92rem; }
    .hero-tag    { font-size: 0.78rem; padding: 5px 12px; }

    .gradio-container { padding: 0 8px 32px !important; }

    .pkl-card, .pkl-card.form { padding: 16px !important; }

    .lb-table          { font-size: 0.8rem; }
    .lb-table thead th,
    .lb-table td       { padding: 10px 10px; }

    .reviews-grid { grid-template-columns: 1fr; }

    #submit-btn { font-size: 1rem !important; }

    .tab-nav button { padding: 9px 16px !important; font-size: 0.87rem !important; }
}
"""


with gr.Blocks(theme=gr.themes.Soft(), css=CSS, title="Pickldd 🥒") as demo:

    gr.HTML("""
    <div class="hero">
        <span class="hero-icon">🥒</span>
        <h1 class="hero-title">Pickl<span class="accent">dd</span></h1>
        <p class="hero-sub">The internet's most <em>serious</em> pickle review platform.</p>
        <div class="hero-tags">
            <span class="hero-tag">🧄 Garlic Lovers</span>
            <span class="hero-tag">🔊 Crunch Seekers</span>
            <span class="hero-tag">😬 Sour Heads</span>
            <span class="hero-tag">🥒 Brine Connoisseurs</span>
        </div>
    </div>
    """)

    with gr.Tabs():

        # ── Tab 1: Rate a Pickle ─────────────────────────────────────────
        with gr.Tab("🥒 Rate a Pickle"):

            with gr.Group(elem_classes="pkl-card"):
                gr.HTML('<div class="card-section-title">🥒 The Pickle</div>')
                with gr.Row():
                    pickle_name = gr.Textbox(
                        label="Pickle Name *",
                        placeholder="e.g. Claussen Whole Dill, Grillo's Italian Spears…",
                        scale=2,
                    )
                    brand = gr.Textbox(
                        label="Brand",
                        placeholder="e.g. Vlasic, Bubbies, Grillo's…",
                        scale=1,
                    )

            with gr.Group(elem_classes="pkl-card"):
                gr.HTML('<div class="card-section-title">⭐ Rate It</div>')
                gr.Markdown(
                    "Rate each quality &nbsp;*(1 = 😐 bland &nbsp;·&nbsp; 10 = 🤩 perfection)*",
                    elem_classes="rating-hint",
                )
                with gr.Row():
                    overall     = gr.Slider(1, 10, value=7, step=1, label="⭐ Overall Rating")
                    crunchiness = gr.Slider(1, 10, value=7, step=1, label="🔊 Crunchiness")
                with gr.Row():
                    sourness = gr.Slider(1, 10, value=7, step=1, label="😬 Sourness")
                    garlic   = gr.Slider(1, 10, value=7, step=1, label="🧄 Garlic Level")

            with gr.Group(elem_classes="pkl-card"):
                gr.HTML('<div class="card-section-title">📝 Your Take</div>')
                review_text = gr.Textbox(
                    label="Review",
                    placeholder="Tell the world what makes this pickle special (or not)…",
                    lines=3,
                    show_label=False,
                )
                photo = gr.Image(
                    label="📸 Pickle Photo (optional)",
                    type="filepath",
                    sources=["upload", "webcam"],
                )

            submit_btn = gr.Button(
                "🥒 Pickle It!",
                variant="primary",
                elem_id="submit-btn",
                size="lg",
            )

            status_msg = gr.Textbox(
                value="",
                show_label=False,
                interactive=False,
                elem_id="status-box",
                container=False,
                lines=1,
            )

        # ── Tab 2: Leaderboard ───────────────────────────────────────────
        with gr.Tab("🏆 Leaderboard"):

            with gr.Group(elem_classes="sort-card"):
                with gr.Row(equal_height=True):
                    sort_dd = gr.Dropdown(
                        choices=SORT_OPTIONS,
                        value="⭐ Overall",
                        label="Sort by",
                        scale=3,
                        container=False,
                    )
                    refresh_btn = gr.Button("🔄 Refresh", scale=1, variant="secondary")

            leaderboard_out = gr.HTML(value=get_leaderboard_html)

            gr.HTML('<div class="lb-section-title">📋 Recent Reviews</div>')
            recent_out = gr.HTML(value=get_recent_html)

    # ── Event wiring ─────────────────────────────────────────────────────

    submit_btn.click(
        fn=submit_review,
        inputs=[pickle_name, brand, overall, crunchiness, sourness, garlic, review_text, photo],
        outputs=[status_msg, leaderboard_out],
    )

    sort_dd.change(
        fn=get_leaderboard_html,
        inputs=[sort_dd],
        outputs=[leaderboard_out],
    )

    refresh_btn.click(
        fn=lambda s: (get_leaderboard_html(s), get_recent_html()),
        inputs=[sort_dd],
        outputs=[leaderboard_out, recent_out],
    )


from fastapi import FastAPI
import uvicorn
from tidewave.fastapi import Tidewave

fastapi_app = FastAPI()
Tidewave().install(fastapi_app)
fastapi_app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="0.0.0.0", port=7860)
