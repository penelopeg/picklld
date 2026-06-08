import os
import re
import json
import sqlite3
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

from db import DB_PATH, _query_pickle_profiles


_SOMMELIER_PROMPT = """\
You are the Pickle Sommelier — a refined expert in pickle culture, fermentation, and brine alchemy.

Analyze this pickle and craft a sommelier-style tasting profile from the community review data.

PICKLE: {pickle_name}
BRAND: {brand_display}
TOTAL REVIEWS: {review_count}
BUY AGAIN RATE: {buy_again_pct}%

AVERAGE SCORES (out of 10):
  Overall:     {avg_overall}
  Crunchiness: {avg_crunch}
  Sourness:    {avg_sour}
  Garlic:      {avg_garlic}
  Spiciness:   {avg_spicy}

COMMUNITY REVIEW NOTES:
{reviews_section}

Respond with exactly this JSON object:
{{
  "flavor_summary":    "2-3 sentences on the overall flavor character and brine profile",
  "crunch_description":"1-2 vivid sentences on texture, snap, and structural integrity",
  "best_uses":         ["use case 1", "use case 2", "use case 3", "use case 4"],
  "similar_styles":    ["similar pickle style 1", "similar pickle style 2", "similar pickle style 3"],
  "tasting_notes":     "2-3 playful sentences in wine-sommelier language applied absurdly to pickles",
  "verdict":           "One punchy sentence: should you buy this pickle again?"
}}

Return only the JSON — no markdown fences, no extra text.
"""

_VISION_PROMPT = """\
You are a pickle product expert examining a photo of a pickle jar.

Respond with ONLY a JSON object — no markdown, no extra text:
{
  "brand":         "Brand name from the label, or 'Not visible' if unreadable",
  "pickle_name":   "Full product name from the label (e.g. Kosher Dill Spears, Bread & Butter Chips)",
  "style":         "Pickle style (Kosher Dill, Bread & Butter, Spicy, Garlic Dill, Polish, Cornichon, etc.)",
  "description":   "1-2 sentences describing what you see",
  "flavor_profile":"Expected flavor based on style, color, brine, and visible spices"
}
"""


def _no_key_html():
    return (
        '<div class="som-error">⚠️ <strong>GEMINI_API_KEY</strong> is not set. '
        'Get a free key at <em>aistudio.google.com</em> and set it before restarting.</div>'
    )


def _parse_gemini_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$",          "", text)
    return json.loads(text)


def som_placeholder():
    return """
    <div class="lb-empty">
        <div style="font-size:3rem;margin-bottom:12px;">🍷</div>
        <p style="margin:0;color:#6b7280;font-size:0.95rem;">
            Select a pickle above and click <strong>Consult the Sommelier</strong>.
        </p>
    </div>
    """


def scan_placeholder():
    return """
    <div class="lb-empty">
        <div style="font-size:3rem;margin-bottom:12px;">📸</div>
        <p style="margin:0;color:#6b7280;font-size:0.95rem;">
            Upload a pickle jar photo and click <strong>Analyze Jar</strong>.
        </p>
    </div>
    """


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


def _render_sommelier_html(pickle_name, brand, review_count, data):
    brand_display = brand if brand != "—" else ""
    brand_span    = f'<span class="som-brand">{brand_display} &middot; </span>' if brand_display else ""
    rev_label     = f'{review_count} review{"s" if review_count != 1 else ""}'
    verdict       = data.get("verdict", "")
    verdict_html  = f'<div class="som-verdict">🏆 {verdict}</div>' if verdict else ""

    uses_html    = "".join(f'<span class="som-tag">{u}</span>'         for u in data.get("best_uses",     []))
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
        {verdict_html}
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
        return som_placeholder()
    if not _GEMINI_OK:
        return _no_key_html()

    parts       = pickle_choice.split("|||", 1)
    pickle_name = parts[0]
    brand_key   = parts[1] if len(parts) > 1 else "—"

    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query(
        """
        SELECT overall, crunchiness, sourness, garlic, spiciness, buy_again, review_text
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

    avg_overall   = round(float(df["overall"].mean()),     1)
    avg_crunch    = round(float(df["crunchiness"].mean()), 1)
    avg_sour      = round(float(df["sourness"].mean()),    1)
    avg_garlic    = round(float(df["garlic"].mean()),      1)
    avg_spicy     = round(float(df.get("spiciness", pd.Series([5])).mean()), 1)
    buy_again_pct = int(round(float(df["buy_again"].mean()) * 100, 0))

    texts           = [str(t).strip() for t in df["review_text"].tolist() if t and str(t).strip()]
    reviews_section = "\n".join(f'• "{t}"' for t in texts) if texts else "No written notes submitted."

    prompt = _SOMMELIER_PROMPT.format(
        pickle_name   = pickle_name,
        brand_display = brand_key if brand_key != "—" else "Unknown brand",
        review_count  = len(df),
        buy_again_pct = buy_again_pct,
        avg_overall   = avg_overall,
        avg_crunch    = avg_crunch,
        avg_sour      = avg_sour,
        avg_garlic    = avg_garlic,
        avg_spicy     = avg_spicy,
        reviews_section = reviews_section,
    )

    try:
        model    = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        data     = _parse_gemini_json(response.text)
    except Exception as exc:
        return f'<div class="som-error">⚠️ Sommelier is unavailable: {exc}</div>'

    return _render_sommelier_html(pickle_name, brand_key, len(df), data)


def _render_photo_analysis_html(data):
    brand          = data.get("brand",         "—")
    pickle_name    = data.get("pickle_name",   "—")
    style          = data.get("style",         "—")
    description    = data.get("description",   "")
    flavor_profile = data.get("flavor_profile","")

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
                <span class="scan-pill-label">🥒 Product</span>
                <span class="scan-pill-value">{pickle_name}</span>
            </div>
            <div class="scan-pill">
                <span class="scan-pill-label">🗂️ Style</span>
                <span class="scan-pill-value">{style}</span>
            </div>
        </div>
        <div class="scan-block">
            <div class="scan-block-label">👁️ What I See</div>
            <div class="scan-block-body">{description}</div>
        </div>
        <div class="scan-block">
            <div class="scan-block-label">🎭 Flavor Profile</div>
            <div class="scan-block-body">{flavor_profile}</div>
        </div>
        <p style="font-size:0.82rem;color:#6b7280;margin:14px 0 0;padding-top:12px;border-top:1px solid #e5e7eb;">
            💡 Fields pre-filled in <strong>Rate a Pickle</strong> — switch tabs to review it!
        </p>
    </div>
    """


def analyze_pickle_photo(image_path):
    """Returns (html, detected_name, detected_brand) for scan-to-rate pre-fill."""
    if image_path is None:
        return scan_placeholder(), "", ""
    if not _GEMINI_OK:
        return _no_key_html(), "", ""
    if _PILImage is None:
        return '<div class="som-error">⚠️ Pillow is required: <code>pip install Pillow</code></div>', "", ""

    try:
        img      = _PILImage.open(image_path)
        model    = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([_VISION_PROMPT, img])
        data     = _parse_gemini_json(response.text)
    except Exception as exc:
        return f'<div class="som-error">⚠️ Analysis failed: {exc}</div>', "", ""

    detected_brand = data.get("brand", "")
    if detected_brand in ("Not visible", "Unknown", "—"):
        detected_brand = ""
    detected_name = data.get("pickle_name", "") or data.get("style", "")

    return _render_photo_analysis_html(data), detected_name, detected_brand
