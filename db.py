import sqlite3
import os
import shutil
import pandas as pd
from datetime import datetime

DB_PATH    = os.environ.get("DB_PATH", "pickldd.db")
UPLOADS_DIR = "uploads"

SORT_OPTIONS = ["⭐ Overall", "🛒 Buy Again", "🔊 Crunchiness", "😬 Sourness", "🧄 Garlic", "🌶️ Spiciness", "📝 Reviews"]
_SORT_COLS   = {
    "⭐ Overall":      "avg_overall",
    "🛒 Buy Again":   "buy_again_pct",
    "🔊 Crunchiness": "avg_crunch",
    "😬 Sourness":    "avg_sour",
    "🧄 Garlic":      "avg_garlic",
    "🌶️ Spiciness":  "avg_spicy",
    "📝 Reviews":     "review_count",
}


def init_db():
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pickle_name TEXT    NOT NULL,
            brand       TEXT    DEFAULT '',
            overall     INTEGER NOT NULL CHECK(overall     BETWEEN 1 AND 10),
            crunchiness INTEGER NOT NULL CHECK(crunchiness BETWEEN 1 AND 10),
            sourness    INTEGER NOT NULL CHECK(sourness    BETWEEN 1 AND 10),
            garlic      INTEGER NOT NULL CHECK(garlic      BETWEEN 1 AND 10),
            spiciness   INTEGER NOT NULL DEFAULT 5,
            buy_again   INTEGER NOT NULL DEFAULT 1,
            review_text TEXT    DEFAULT '',
            photo_path  TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    # Non-destructive migrations for existing databases
    for col, defn in [
        ("spiciness", "INTEGER NOT NULL DEFAULT 5"),
        ("buy_again",  "INTEGER NOT NULL DEFAULT 1"),
    ]:
        try:
            conn.execute(f"ALTER TABLE reviews ADD COLUMN {col} {defn}")
        except sqlite3.OperationalError:
            pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_name  ON reviews(pickle_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_brand ON reviews(brand)")
    conn.commit()
    conn.close()


def save_photo(tmp_path, pickle_name):
    if not tmp_path:
        return None
    try:
        ext  = os.path.splitext(tmp_path)[1] or ".jpg"
        safe = "".join(c for c in pickle_name if c.isalnum() or c in "-_ ")[:30].strip()
        dest = os.path.join(UPLOADS_DIR, f"{datetime.now():%Y%m%d_%H%M%S}_{safe}{ext}")
        shutil.copy2(tmp_path, dest)
        return dest
    except Exception:
        return None


def insert_review(pickle_name, brand, overall, crunchiness, sourness, garlic,
                  spiciness, buy_again, review_text, photo_path):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """INSERT INTO reviews
               (pickle_name, brand, overall, crunchiness, sourness, garlic,
                spiciness, buy_again, review_text, photo_path)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                pickle_name.strip(),
                (brand or "").strip(),
                int(overall), int(crunchiness), int(sourness), int(garlic), int(spiciness),
                1 if buy_again else 0,
                (review_text or "").strip(),
                photo_path,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _query_pickle_profiles(sort_by=None, name_filter="", brand_filter=""):
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
            ROUND(AVG(CAST(spiciness   AS REAL)), 1) AS avg_spicy,
            ROUND(AVG(CAST(buy_again   AS REAL)) * 100, 0) AS buy_again_pct,
            COUNT(*) AS review_count
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
    return df.sort_values(sort_col, ascending=False).reset_index(drop=True)


def _query_leaderboard(sort_by="⭐ Overall"):
    df = _query_pickle_profiles(sort_by=sort_by)
    if df.empty:
        return df
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


def get_analytics():
    profiles = _query_pickle_profiles()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT
            COUNT(*)                                        AS total_reviews,
            COUNT(DISTINCT LOWER(TRIM(pickle_name)))        AS total_pickles,
            ROUND(AVG(CAST(crunchiness AS REAL)), 1)        AS avg_crunch,
            ROUND(AVG(CAST(sourness    AS REAL)), 1)        AS avg_sour,
            ROUND(AVG(CAST(garlic      AS REAL)), 1)        AS avg_garlic,
            ROUND(AVG(CAST(buy_again   AS REAL)) * 100, 0)  AS buy_again_pct
        FROM reviews
    """).fetchone()
    conn.close()

    total         = int(row[0])   if row[0]       else 0
    total_pickles = int(row[1])   if row[1]       else 0
    avg_crunch    = float(row[2]) if row[2] is not None else 0.0
    avg_sour      = float(row[3]) if row[3] is not None else 0.0
    avg_garlic    = float(row[4]) if row[4] is not None else 0.0
    buy_again_pct = float(row[5]) if row[5] is not None else 0.0

    def _label(r):
        return f"{r['pickle_name']} ({r['brand']})" if r["brand"] != "—" else r["pickle_name"]

    if profiles.empty:
        return total, total_pickles, "—", "—", avg_crunch, avg_sour, avg_garlic, buy_again_pct

    highest_rated = _label(profiles.iloc[0])
    most_reviewed = _label(profiles.sort_values("review_count", ascending=False).iloc[0])

    return total, total_pickles, highest_rated, most_reviewed, avg_crunch, avg_sour, avg_garlic, buy_again_pct


def get_pickle_choices():
    df = _query_pickle_profiles()
    if df.empty:
        return []
    choices = []
    for _, row in df.iterrows():
        b     = row["brand"]
        label = f"{row['pickle_name']} — {b}" if b != "—" else row["pickle_name"]
        choices.append((label, f"{row['pickle_name']}|||{b}"))
    return choices


def get_recent_reviews_df(limit=20):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT pickle_name, brand, overall, crunchiness, sourness, garlic, spiciness, buy_again,
               review_text, SUBSTR(created_at, 1, 10) AS date
        FROM reviews ORDER BY id DESC LIMIT :limit
        """,
        conn,
        params={"limit": limit},
    )
    conn.close()
    return df


def get_top_pickles_df(n=8):
    df = _query_pickle_profiles()
    if df.empty:
        return pd.DataFrame({"Pickle": [], "Avg Score": [], "Theme": []})
    top = df.head(n).copy()
    top["Pickle"] = top.apply(
        lambda r: r["pickle_name"] + (f" ({r['brand']})" if r["brand"] != "—" else ""), axis=1
    )
    top["Theme"] = "Pickle"
    return top[["Pickle", "avg_overall", "Theme"]].rename(columns={"avg_overall": "Avg Score"})
