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
        return "⚠️ Please enter a pickle name!", get_leaderboard("⭐ Overall")

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
    return "✅ Pickled! Your review is brined and bottled. 🥒", get_leaderboard("⭐ Overall")


SORT_OPTIONS = ["⭐ Overall", "🔊 Crunchiness", "😬 Sourness", "🧄 Garlic", "📝 Reviews"]
_SORT_COLS = {
    "⭐ Overall":      "avg_overall",
    "🔊 Crunchiness": "avg_crunch",
    "😬 Sourness":    "avg_sour",
    "🧄 Garlic":      "avg_garlic",
    "📝 Reviews":     "review_count",
}

_EMPTY_LB = pd.DataFrame(
    columns=["#", "🥒 Pickle", "Brand", "⭐ Overall", "🔊 Crunch", "😬 Sour", "🧄 Garlic", "📝 Reviews"]
)


def get_leaderboard(sort_by="⭐ Overall"):
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
        return _EMPTY_LB.copy()

    sort_col = _SORT_COLS.get(sort_by, "avg_overall")
    df = df.sort_values(sort_col, ascending=False).reset_index(drop=True)
    df.insert(0, "#", range(1, len(df) + 1))
    df.columns = ["#", "🥒 Pickle", "Brand", "⭐ Overall", "🔊 Crunch", "😬 Sour", "🧄 Garlic", "📝 Reviews"]
    return df


def get_recent_reviews():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT
            pickle_name                             AS "🥒 Pickle",
            COALESCE(NULLIF(TRIM(brand), ''), '—') AS "Brand",
            overall                                 AS "⭐",
            crunchiness                             AS "🔊",
            sourness                                AS "😬",
            garlic                                  AS "🧄",
            COALESCE(NULLIF(TRIM(review_text), ''), '—') AS "Review",
            SUBSTR(created_at, 1, 10)               AS "Date"
        FROM reviews
        ORDER BY id DESC
        LIMIT 50
        """,
        conn,
    )
    conn.close()
    return df


init_db()


CSS = """
/* ── Layout ── */
.gradio-container { max-width: 880px !important; margin: 0 auto !important; }

/* ── Header ── */
.pkl-header { text-align:center; padding:28px 0 12px 0; }
.pkl-title  {
    font-size: 2.8rem;
    font-weight: 900;
    background: linear-gradient(135deg, #2d5a0e 0%, #5a9e1e 55%, #90c520 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -1.5px;
    margin: 0;
    line-height: 1.1;
}
.pkl-sub { color: #6b7280; font-size: 1rem; margin: 6px 0 0 0; }

/* ── Tabs ── */
.tab-nav button { font-weight: 700 !important; font-size: 0.95rem !important; }

/* ── Submit button ── */
#submit-btn {
    background: linear-gradient(135deg, #3a6b1a, #79be14) !important;
    color: white !important;
    font-weight: 800 !important;
    font-size: 1.05rem !important;
    border-radius: 10px !important;
    border: none !important;
    transition: opacity 0.18s ease !important;
}
#submit-btn:hover { opacity: 0.82 !important; }

/* ── Status message ── */
#status-box textarea {
    text-align: center !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    border: none !important;
    background: transparent !important;
    color: #374151 !important;
    resize: none !important;
}

/* ── Rating section label ── */
.rating-hint { color: #6b7280; font-size: 0.85rem; }
"""

with gr.Blocks(theme=gr.themes.Soft(), css=CSS, title="Pickldd 🥒") as demo:

    gr.HTML("""
    <div class="pkl-header">
      <div style="font-size:3.8rem;line-height:1.15;">🥒</div>
      <h1 class="pkl-title">Pickldd</h1>
      <p class="pkl-sub">Rate your pickles. Find your perfect brine. 🧄</p>
    </div>
    """)

    with gr.Tabs():

        # ── Tab 1: Rate a Pickle ─────────────────────────────────────────
        with gr.Tab("🥒 Rate a Pickle"):

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

            gr.Markdown(
                "**Rate each quality** &nbsp;*(1 = 😐 bland · 10 = 🤩 perfection)*",
                elem_classes="rating-hint",
            )

            with gr.Row():
                overall     = gr.Slider(1, 10, value=7, step=1, label="⭐ Overall Rating")
                crunchiness = gr.Slider(1, 10, value=7, step=1, label="🔊 Crunchiness")

            with gr.Row():
                sourness = gr.Slider(1, 10, value=7, step=1, label="😬 Sourness")
                garlic   = gr.Slider(1, 10, value=7, step=1, label="🧄 Garlic Level")

            review_text = gr.Textbox(
                label="Your Review",
                placeholder="Tell the world what makes this pickle special (or not)…",
                lines=3,
            )

            photo = gr.Image(
                label="📸 Pickle Photo (optional)",
                type="filepath",
                sources=["upload", "webcam"],
            )

            submit_btn = gr.Button(
                "Pickle It! 🥒",
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

            with gr.Row(equal_height=True):
                sort_dd = gr.Dropdown(
                    choices=SORT_OPTIONS,
                    value="⭐ Overall",
                    label="Sort by",
                    scale=2,
                )
                refresh_btn = gr.Button("🔄 Refresh", scale=1, variant="secondary")

            leaderboard_df = gr.DataFrame(
                value=get_leaderboard,
                label="🏆 Pickle Rankings",
                interactive=False,
                wrap=True,
            )

            gr.Markdown("---")
            gr.Markdown("#### 📋 Recent Reviews")

            recent_df = gr.DataFrame(
                value=get_recent_reviews,
                label="Recent Reviews",
                interactive=False,
                wrap=True,
            )

    # ── Event wiring ─────────────────────────────────────────────────────

    submit_btn.click(
        fn=submit_review,
        inputs=[pickle_name, brand, overall, crunchiness, sourness, garlic, review_text, photo],
        outputs=[status_msg, leaderboard_df],
    )

    sort_dd.change(
        fn=get_leaderboard,
        inputs=[sort_dd],
        outputs=[leaderboard_df],
    )

    refresh_btn.click(
        fn=lambda s: (get_leaderboard(s), get_recent_reviews()),
        inputs=[sort_dd],
        outputs=[leaderboard_df, recent_df],
    )


if __name__ == "__main__":
    demo.launch()
