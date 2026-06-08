import gradio as gr
import sqlite3
import os
import shutil
import json
import re
from datetime import datetime
import pandas as pd

try:
    import google.generativeai as genai
    _GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    if _GEMINI_KEY:
        genai.configure(api_key=_GEMINI_KEY)
    _GEMINI_OK = bool(_GEMINI_KEY)
except ImportError:
    _GEMINI_OK = False

try:
    import PIL.Image as _PILImage
except ImportError:
    _PILImage = None

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


def _query_pickle_profiles(sort_by=None, name_filter="", brand_filter=""):
    """Aggregated profile per (pickle_name, brand) product, optionally filtered and sorted."""
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
        WHERE (:name  = '' OR LOWER(pickle_name)        LIKE '%' || LOWER(:name)  || '%')
          AND (:brand = '' OR LOWER(COALESCE(brand,'')) LIKE '%' || LOWER(:brand) || '%')
        GROUP BY LOWER(TRIM(pickle_name)), LOWER(TRIM(COALESCE(brand, '')))
        """,
        conn,
        params={"name": name_filter or "", "brand": brand_filter or ""},
    )
    conn.close()
    if df.empty:
        return df
    sort_col = _SORT_COLS.get(sort_by, "avg_overall")
    df = df.sort_values(sort_col, ascending=False).reset_index(drop=True)
    return df


def _query_leaderboard(sort_by="⭐ Overall"):
    df = _query_pickle_profiles(sort_by=sort_by)
    if df.empty:
        return df
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


def get_analytics():
    profiles = _query_pickle_profiles()

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT
            COUNT(*)                                  AS total_reviews,
            ROUND(AVG(CAST(crunchiness AS REAL)), 1)  AS avg_crunch,
            ROUND(AVG(CAST(sourness    AS REAL)), 1)  AS avg_sour,
            ROUND(AVG(CAST(garlic      AS REAL)), 1)  AS avg_garlic
        FROM reviews
    """).fetchone()
    conn.close()

    total      = int(row[0])   if row[0]       else 0
    avg_crunch = float(row[1]) if row[1] is not None else 0.0
    avg_sour   = float(row[2]) if row[2] is not None else 0.0
    avg_garlic = float(row[3]) if row[3] is not None else 0.0

    def _label(r):
        b = r["brand"]
        return f"{r['pickle_name']} ({b})" if b != "—" else r["pickle_name"]

    if profiles.empty:
        return total, "—", "—", avg_crunch, avg_sour, avg_garlic

    highest_rated  = _label(profiles.iloc[0])
    most_rev_label = _label(
        profiles.sort_values("review_count", ascending=False).iloc[0]
    )

    return total, highest_rated, most_rev_label, avg_crunch, avg_sour, avg_garlic


def search_pickles(name_query="", brand_query=""):
    name_q = (name_query or "").strip()
    brand_q = (brand_query or "").strip()

    if not name_q and not brand_q:
        return """
        <div class="lb-empty">
            <div style="font-size:3rem;margin-bottom:12px;">🔍</div>
            <p style="margin:0;color:#6b7280;font-size:0.95rem;">
                Type a pickle name or brand above to search.
            </p>
        </div>
        """

    df = _query_pickle_profiles(name_filter=name_q, brand_filter=brand_q)

    if df.empty:
        return """
        <div class="lb-empty">
            <div style="font-size:3rem;margin-bottom:12px;">🥒</div>
            <p style="margin:0;color:#6b7280;font-size:0.95rem;">
                No pickles matched your search. Try a different name or brand.
            </p>
        </div>
        """

    count = len(df)
    label = f'{count} result{"s" if count != 1 else ""}'

    rows_html = ""
    for _, row in df.iterrows():
        n = int(row["review_count"])
        review_label = f'{n} {"review" if n == 1 else "reviews"}'
        rows_html += f"""
        <tr class="lb-row">
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
    <p style="font-size:0.82rem;color:#6b7280;margin:0 0 10px;font-weight:600;
              text-transform:uppercase;letter-spacing:0.8px;">{label}</p>
    <div class="lb-wrapper">
        <table class="lb-table">
            <thead>
                <tr>
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


# ── Pickle Sommelier ─────────────────────────────────────────────────────────

_SOMMELIER_PROMPT = """\
You are the Pickle Sommelier — a refined expert in pickle culture, fermentation, and brine alchemy.

Analyze the following pickle product and craft a sommelier-style tasting profile drawing from the \
community review data provided.

PICKLE: {pickle_name}
BRAND: {brand_display}
TOTAL REVIEWS: {review_count}

AVERAGE SCORES (out of 10):
  Overall:     {avg_overall}
  Crunchiness: {avg_crunch}
  Sourness:    {avg_sour}
  Garlic:      {avg_garlic}

COMMUNITY REVIEW NOTES:
{reviews_section}

Respond with a JSON object containing exactly these keys:
{{
  "flavor_summary":    "2-3 sentences on the overall flavor character and brine profile",
  "crunch_description":"1-2 vivid sentences on texture, snap, and structural integrity",
  "best_uses":         ["use case 1", "use case 2", "use case 3", "use case 4"],
  "similar_styles":    ["similar pickle style 1", "similar pickle style 2", "similar pickle style 3"],
  "tasting_notes":     "2-3 playful sentences written in wine-sommelier language applied absurdly to pickles"
}}

Return only the JSON object — no markdown fences, no extra text.
"""


def get_pickle_choices():
    df = _query_pickle_profiles()
    if df.empty:
        return []
    choices = []
    for _, row in df.iterrows():
        b = row["brand"]
        label = f"{row['pickle_name']} — {b}" if b != "—" else row["pickle_name"]
        value = f"{row['pickle_name']}|||{b}"
        choices.append((label, value))
    return choices


def _som_placeholder():
    return """
    <div class="lb-empty">
        <div style="font-size:3rem;margin-bottom:12px;">🍷</div>
        <p style="margin:0;color:#6b7280;font-size:0.95rem;">
            Select a pickle above and consult the Sommelier for an AI-powered tasting profile.
        </p>
    </div>
    """


def _render_sommelier_html(pickle_name, brand, review_count, data):
    brand_display = brand if brand != "—" else ""
    brand_span = f'<span class="som-brand">{brand_display} &middot; </span>' if brand_display else ""
    n = review_count
    rev_label = f'{n} review{"s" if n != 1 else ""}'

    uses_html    = "".join(f'<span class="som-tag">{u}</span>' for u in data.get("best_uses", []))
    similar_html = "".join(f'<span class="som-tag som-tag-alt">{s}</span>' for s in data.get("similar_styles", []))

    return f"""
    <div class="sommelier-profile">
        <div class="som-header">
            <span class="som-icon">🍷</span>
            <div>
                <div class="som-name">{pickle_name}</div>
                <div class="som-meta">{brand_span}<span>Based on {rev_label}</span></div>
            </div>
        </div>
        <div class="som-grid">
            <div class="som-card">
                <div class="som-card-title">🎭 Flavor Profile</div>
                <p>{data.get("flavor_summary", "")}</p>
            </div>
            <div class="som-card">
                <div class="som-card-title">🔊 Crunch Report</div>
                <p>{data.get("crunch_description", "")}</p>
            </div>
            <div class="som-card som-full">
                <div class="som-card-title">🥂 Tasting Notes</div>
                <p class="som-notes">{data.get("tasting_notes", "")}</p>
            </div>
            <div class="som-card">
                <div class="som-card-title">🥪 Best Uses</div>
                <div class="som-tags">{uses_html}</div>
            </div>
            <div class="som-card">
                <div class="som-card-title">🥒 Similar Styles</div>
                <div class="som-tags">{similar_html}</div>
            </div>
        </div>
    </div>
    """


def generate_sommelier(pickle_choice):
    if not pickle_choice:
        return _som_placeholder()

    if not _GEMINI_OK:
        return (
            '<div class="som-error">⚠️ <strong>GEMINI_API_KEY</strong> environment variable is not set. '
            'Get a free key at <em>aistudio.google.com</em> and restart the app.</div>'
        )

    parts = pickle_choice.split("|||", 1)
    pickle_name = parts[0]
    brand_key   = parts[1] if len(parts) > 1 else "—"

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT overall, crunchiness, sourness, garlic, review_text
        FROM reviews
        WHERE LOWER(TRIM(pickle_name))        = LOWER(TRIM(:name))
          AND LOWER(TRIM(COALESCE(brand,''))) = LOWER(TRIM(:brand))
        """,
        conn,
        params={"name": pickle_name, "brand": "" if brand_key == "—" else brand_key},
    )
    conn.close()

    if df.empty:
        return '<div class="som-error">No reviews found for this pickle.</div>'

    avg_overall = round(float(df["overall"].mean()), 1)
    avg_crunch  = round(float(df["crunchiness"].mean()), 1)
    avg_sour    = round(float(df["sourness"].mean()), 1)
    avg_garlic  = round(float(df["garlic"].mean()), 1)

    texts = [str(t).strip() for t in df["review_text"].tolist() if t and str(t).strip()]
    reviews_section = "\n".join(f'• "{t}"' for t in texts) if texts else "No written notes submitted."

    prompt = _SOMMELIER_PROMPT.format(
        pickle_name=pickle_name,
        brand_display=brand_key if brand_key != "—" else "Unknown brand",
        review_count=len(df),
        avg_overall=avg_overall,
        avg_crunch=avg_crunch,
        avg_sour=avg_sour,
        avg_garlic=avg_garlic,
        reviews_section=reviews_section,
    )

    try:
        model    = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text     = response.text.strip()
        text     = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text     = re.sub(r"\n?```\s*$", "", text)
        data     = json.loads(text)
    except Exception as exc:
        return f'<div class="som-error">⚠️ Sommelier is unavailable right now: {exc}</div>'

    return _render_sommelier_html(pickle_name, brand_key, len(df), data)


# ── Photo Analysis ────────────────────────────────────────────────────────────

_VISION_PROMPT = """\
You are a pickle product expert examining a photo of a pickle jar or pickle product.

Study the image carefully and respond with ONLY a JSON object — no markdown, no extra text:
{
  "brand":         "Brand name read from the label, or 'Not visible' if unreadable",
  "style":         "Pickle style (e.g. Kosher Dill, Bread & Butter, Spicy, Garlic Dill, Polish, Cornichon, etc.)",
  "description":   "1-2 sentences describing what you see in the image",
  "flavor_profile":"Expected flavor characteristics based on the visible style, color, brine, and any spices"
}
"""


def _scan_placeholder():
    return """
    <div class="lb-empty">
        <div style="font-size:3rem;margin-bottom:12px;">📸</div>
        <p style="margin:0;color:#6b7280;font-size:0.95rem;">
            Upload a pickle jar photo and click <strong>Analyze Jar</strong>.
        </p>
    </div>
    """


def _render_photo_analysis_html(data):
    brand         = data.get("brand", "—")
    style         = data.get("style", "—")
    description   = data.get("description", "")
    flavor_profile = data.get("flavor_profile", "")

    return f"""
    <div class="scan-result">
        <div class="scan-header">
            <span class="scan-title">🔍 Jar Analysis</span>
        </div>
        <div class="scan-pills">
            <div class="scan-pill">
                <span class="scan-pill-label">🏷️ Brand</span>
                <span class="scan-pill-value">{brand}</span>
            </div>
            <div class="scan-pill">
                <span class="scan-pill-label">🥒 Style</span>
                <span class="scan-pill-value">{style}</span>
            </div>
        </div>
        <div class="scan-block">
            <div class="scan-block-label">👁️ What I See</div>
            <div class="scan-block-body">{description}</div>
        </div>
        <div class="scan-block">
            <div class="scan-block-label">🎭 Likely Flavor Profile</div>
            <div class="scan-block-body">{flavor_profile}</div>
        </div>
    </div>
    """


def analyze_pickle_photo(image_path):
    if image_path is None:
        return _scan_placeholder()

    if not _GEMINI_OK:
        return (
            '<div class="som-error">⚠️ <strong>GEMINI_API_KEY</strong> is not set. '
            'Get a free key at <em>aistudio.google.com</em> and restart the app.</div>'
        )

    if _PILImage is None:
        return '<div class="som-error">⚠️ Pillow is required: <code>pip install Pillow</code></div>'

    try:
        img      = _PILImage.open(image_path)
        model    = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([_VISION_PROMPT, img])
        text     = response.text.strip()
        text     = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text     = re.sub(r"\n?```\s*$", "", text)
        data     = json.loads(text)
    except Exception as exc:
        return f'<div class="som-error">⚠️ Analysis failed: {exc}</div>'

    return _render_photo_analysis_html(data)


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
    .som-grid { grid-template-columns: 1fr; }
    .scan-pills { flex-direction: column; }
}

/* ── Photo scan result ── */
.scan-result {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    padding: 20px 22px;
    box-shadow: var(--sh-sm);
    height: 100%;
    box-sizing: border-box;
}

.scan-header { margin-bottom: 16px; }

.scan-title {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: var(--pkl-mid);
}

.scan-pills {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}

.scan-pill {
    flex: 1;
    min-width: 120px;
    background: var(--pkl-pale);
    border: 1px solid var(--border);
    border-radius: var(--r-sm);
    padding: 10px 14px;
}

.scan-pill-label {
    display: block;
    font-size: 0.67rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--muted);
    margin-bottom: 4px;
}

.scan-pill-value {
    display: block;
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--pkl-dark);
}

.scan-block { margin-bottom: 14px; }
.scan-block:last-child { margin-bottom: 0; }

.scan-block-label {
    font-size: 0.67rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--muted);
    margin-bottom: 5px;
}

.scan-block-body {
    font-size: 0.87rem;
    color: var(--text);
    line-height: 1.6;
}

/* ── Pickle Sommelier ── */
.sommelier-profile {
    background: linear-gradient(160deg, #0c1f05 0%, #1a3d0a 60%, #2e7012 100%);
    border-radius: var(--r-lg);
    padding: 28px;
    box-shadow: var(--sh-lg);
}

.som-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 22px;
    padding-bottom: 18px;
    border-bottom: 1px solid rgba(255,255,255,0.11);
}

.som-icon { font-size: 2.4rem; line-height: 1; }

.som-name {
    font-size: 1.35rem;
    font-weight: 800;
    color: #d4f582;
    letter-spacing: -0.4px;
    line-height: 1.2;
}

.som-meta { font-size: 0.8rem; color: rgba(255,255,255,0.55); margin-top: 4px; }
.som-brand { color: rgba(255,255,255,0.7); }

.som-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.som-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--r-md);
    padding: 16px 18px;
}

.som-full { grid-column: 1 / -1; }

.som-card-title {
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1.1px;
    color: #a8e063;
    margin-bottom: 10px;
}

.som-card p {
    font-size: 0.87rem;
    color: rgba(255,255,255,0.82);
    line-height: 1.65;
    margin: 0;
}

.som-notes { font-style: italic !important; color: rgba(255,255,255,0.9) !important; }

.som-tags { display: flex; flex-wrap: wrap; gap: 7px; }

.som-tag {
    background: rgba(168,224,99,0.14);
    border: 1px solid rgba(168,224,99,0.28);
    color: #d4f582;
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 0.77rem;
    font-weight: 600;
}

.som-tag-alt {
    background: rgba(245,158,11,0.12);
    border-color: rgba(245,158,11,0.25);
    color: #fcd34d;
}

.som-error {
    padding: 18px 20px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: var(--r-md);
    color: #dc2626;
    font-size: 0.88rem;
    line-height: 1.5;
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

        # ── Tab 2: Scan a Jar ────────────────────────────────────────────
        with gr.Tab("📸 Scan a Jar"):

            with gr.Row(equal_height=True):
                with gr.Column(scale=1):
                    scan_image = gr.Image(
                        label="Pickle Jar Photo",
                        type="filepath",
                        sources=["upload", "webcam"],
                    )
                    scan_btn = gr.Button(
                        "🔍 Analyze Jar",
                        variant="primary",
                    )
                with gr.Column(scale=1):
                    scan_out = gr.HTML(value=_scan_placeholder)

        # ── Tab 3: Leaderboard ──────────────────────────────────────────
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

        # ── Tab 3: Sommelier ─────────────────────────────────────────────
        with gr.Tab("🍷 Sommelier"):

            with gr.Group(elem_classes="sort-card"):
                with gr.Row(equal_height=True):
                    som_dropdown = gr.Dropdown(
                        choices=get_pickle_choices(),
                        label="Select a Pickle",
                        scale=3,
                        container=False,
                    )
                    som_btn = gr.Button(
                        "✨ Consult the Sommelier",
                        variant="primary",
                        scale=1,
                    )

            som_out = gr.HTML(value=_som_placeholder)

        # ── Tab 4: Analytics ─────────────────────────────────────────────
        with gr.Tab("📊 Analytics"):

            with gr.Row():
                analytics_refresh = gr.Button("🔄 Refresh", variant="secondary", scale=0)

            with gr.Row():
                stat_total = gr.Number(
                    label="Total Reviews",
                    interactive=False,
                    precision=0,
                )
                stat_highest = gr.Textbox(
                    label="Highest Rated Pickle",
                    interactive=False,
                )
                stat_most_rev = gr.Textbox(
                    label="Most Reviewed Pickle",
                    interactive=False,
                )

            with gr.Row():
                stat_crunch = gr.Number(
                    label="Avg Crunchiness",
                    interactive=False,
                    precision=1,
                )
                stat_sour = gr.Number(
                    label="Avg Sourness",
                    interactive=False,
                    precision=1,
                )
                stat_garlic = gr.Number(
                    label="Avg Garlic Level",
                    interactive=False,
                    precision=1,
                )

        # ── Tab 4: Search ────────────────────────────────────────────────

        with gr.Tab("🔍 Search"):

            with gr.Group(elem_classes="sort-card"):
                with gr.Row(equal_height=True):
                    search_name = gr.Textbox(
                        label="Pickle Name",
                        placeholder="e.g. Claussen, Spear, Dill…",
                        scale=2,
                    )
                    search_brand = gr.Textbox(
                        label="Brand",
                        placeholder="e.g. Vlasic, Bubbies…",
                        scale=1,
                    )

            search_out = gr.HTML(value=search_pickles)

    # ── Event wiring ─────────────────────────────────────────────────────

    _analytics_outputs = [stat_total, stat_highest, stat_most_rev, stat_crunch, stat_sour, stat_garlic]

    submit_btn.click(
        fn=submit_review,
        inputs=[pickle_name, brand, overall, crunchiness, sourness, garlic, review_text, photo],
        outputs=[status_msg, leaderboard_out],
    ).then(fn=get_analytics, outputs=_analytics_outputs
    ).then(fn=get_pickle_choices, outputs=[som_dropdown])

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

    search_name.input(
        fn=search_pickles,
        inputs=[search_name, search_brand],
        outputs=[search_out],
    )

    search_brand.input(
        fn=search_pickles,
        inputs=[search_name, search_brand],
        outputs=[search_out],
    )

    analytics_refresh.click(fn=get_analytics, outputs=_analytics_outputs)

    som_btn.click(fn=generate_sommelier, inputs=[som_dropdown], outputs=[som_out])

    scan_btn.click(fn=analyze_pickle_photo, inputs=[scan_image], outputs=[scan_out])

    demo.load(fn=get_analytics, outputs=_analytics_outputs)


try:
    from fastapi import FastAPI
    import uvicorn
    from tidewave.fastapi import Tidewave
    _fastapi_app = FastAPI()
    Tidewave().install(_fastapi_app)
    app = gr.mount_gradio_app(_fastapi_app, demo, path="/")
except ImportError:
    app = None

if __name__ == "__main__":
    if app is not None and not os.environ.get("SPACE_ID"):
        uvicorn.run(app, host="0.0.0.0", port=7860)
    else:
        demo.launch()
