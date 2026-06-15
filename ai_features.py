import os
import re
import json
import base64
import io
import sqlite3
import pandas as pd

try:
    from huggingface_hub import InferenceClient as _InferenceClient
    _HF_TOKEN      = os.environ.get("HF_TOKEN", "")
    _client_text   = _InferenceClient(provider="featherless-ai", api_key=_HF_TOKEN or None)
    _client_vision = _InferenceClient(provider="featherless-ai", api_key=_HF_TOKEN or None)
    _HF_OK         = True
except ImportError:
    _HF_OK         = False
    _client_text   = None
    _client_vision = None

try:
    import PIL.Image as _PILImage
except ImportError:
    _PILImage = None

from db import DB_PATH, _query_pickle_profiles

_TEXT_MODEL   = "Qwen/Qwen2.5-3B-Instruct"  # 3 B — featherless-ai
_TEXT_FALLBACKS = [
    "google/gemma-3-4b-it",
    "meta-llama/Llama-3.2-3B-Instruct",
]
_VISION_MODEL = "google/gemma-3-4b-it"       # 4 B vision — featherless-ai

_SOMMELIER_SYSTEM = (
    "You are the Pickle Sommelier — an expert in pickle culture and brine alchemy. "
    "Reply ONLY with a valid JSON object, no markdown fences, no extra text."
)

_SOMMELIER_USER = """\
Analyze this pickle and craft a sommelier-style tasting profile from the review data.

PICKLE: {pickle_name}
BRAND: {brand_display}
REVIEWS: {review_count}  |  Buy-again rate: {buy_again_pct}%
SCORES /10 — Overall: {avg_overall} | Crunch: {avg_crunch} | Sour: {avg_sour} | Garlic: {avg_garlic} | Spice: {avg_spicy}

COMMUNITY NOTES:
{reviews_section}

Return exactly this JSON structure:
{{"flavor_summary":"2-3 sentences on flavor and brine","crunch_description":"1-2 sentences on texture and snap","best_uses":["use1","use2","use3","use4"],"similar_styles":["style1","style2","style3"],"tasting_notes":"2-3 playful wine-sommelier sentences applied absurdly to pickles","verdict":"One punchy buy-it-or-skip-it sentence"}}"""

_VISION_SYSTEM = (
    "You are a pickle product expert. "
    "Reply ONLY with a valid JSON object, no markdown fences, no extra text."
)

_VISION_USER = """\
Examine this pickle jar photo carefully.

Return exactly this JSON structure:
{{"brand":"brand name from the label or Not visible","pickle_name":"full product name from the label","style":"pickle style e.g. Kosher Dill / Bread & Butter / Spicy / Garlic Dill / Polish / Cornichon","description":"1-2 sentences on what you see","flavor_profile":"expected flavor based on the visible style, color, brine, and spices"}}"""


def _parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _no_token_html():
    return (
        '<div class="som-error">⚠️ <strong>HF_TOKEN</strong> is not set. '
        'Add a free Hugging Face token as a Space secret to enable AI features.</div>'
    )


# ── Shared placeholder HTML ───────────────────────────────────────────────────

def som_placeholder():
    return """
    <div class="lb-empty">
        <div style="font-size:3rem;margin-bottom:12px;">🍷</div>
        <p style="margin:0;color:var(--muted);font-size:0.95rem;">
            Select a pickle above and click <strong>Consult the Sommelier</strong>.
        </p>
    </div>
    """


def scan_placeholder():
    return """
    <div class="lb-empty">
        <div style="font-size:3rem;margin-bottom:12px;">📸</div>
        <p style="margin:0;color:var(--muted);font-size:0.95rem;">
            Upload a pickle jar photo and click <strong>Analyze Jar</strong>.
        </p>
    </div>
    """


# ── Sommelier ─────────────────────────────────────────────────────────────────

def _render_sommelier_html(pickle_name, brand, review_count, data):
    brand_display = brand if brand != "—" else ""
    brand_span    = f'<span class="som-brand">{brand_display} &middot; </span>' if brand_display else ""
    rev_label     = f'{review_count} review{"s" if review_count != 1 else ""}'
    verdict       = data.get("verdict", "")
    verdict_html  = f'<div class="som-verdict">🏆 {verdict}</div>' if verdict else ""

    uses_html    = "".join(f'<span class="som-tag">{u}</span>'             for u in data.get("best_uses",     []))
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
    if not _HF_OK:
        return _no_token_html()

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
    buy_again_pct = int(round(float(df["buy_again"].mean()) * 100))

    texts           = [str(t).strip() for t in df["review_text"].tolist() if t and str(t).strip()]
    reviews_section = "\n".join(f'• "{t}"' for t in texts) if texts else "No written notes submitted."

    user_msg = _SOMMELIER_USER.format(
        pickle_name     = pickle_name,
        brand_display   = brand_key if brand_key != "—" else "Unknown brand",
        review_count    = len(df),
        buy_again_pct   = buy_again_pct,
        avg_overall     = avg_overall,
        avg_crunch      = avg_crunch,
        avg_sour        = avg_sour,
        avg_garlic      = avg_garlic,
        avg_spicy       = avg_spicy,
        reviews_section = reviews_section,
    )

    messages = [
        {"role": "system", "content": _SOMMELIER_SYSTEM},
        {"role": "user",   "content": user_msg},
    ]
    last_exc = None
    data = None
    for model in [_TEXT_MODEL] + _TEXT_FALLBACKS:
        try:
            response = _client_text.chat.completions.create(
                model       = model,
                messages    = messages,
                max_tokens  = 600,
                temperature = 0.7,
            )
            data = _parse_json(response.choices[0].message.content)
            break
        except Exception as exc:
            last_exc = exc
    if data is None:
        return f'<div class="som-error">⚠️ Sommelier is unavailable: {last_exc}</div>'

    return _render_sommelier_html(pickle_name, brand_key, len(df), data)


# ── Photo analysis ────────────────────────────────────────────────────────────

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
        <p style="font-size:0.82rem;color:var(--muted);margin:14px 0 0;padding-top:12px;border-top:1px solid var(--row-border);">
            💡 Fields pre-filled in <strong>Rate a Pickle</strong> — switch tabs to review it!
        </p>
    </div>
    """


def analyze_pickle_photo(image_path):
    """Returns (html, detected_name, detected_brand) for scan-to-rate pre-fill."""
    if image_path is None:
        return scan_placeholder(), "", ""
    if not _HF_OK:
        return _no_token_html(), "", ""
    if _PILImage is None:
        return '<div class="som-error">⚠️ Pillow is required: <code>pip install Pillow</code></div>', "", ""

    try:
        img = _PILImage.open(image_path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64      = base64.b64encode(buf.getvalue()).decode()
        data_url = f"data:image/jpeg;base64,{b64}"

        response = _client_vision.chat.completions.create(
            model    = _VISION_MODEL,
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text",      "text": f"{_VISION_SYSTEM}\n\n{_VISION_USER}"},
                ],
            }],
            max_tokens = 400,
        )
        data = _parse_json(response.choices[0].message.content)
    except Exception as exc:
        return f'<div class="som-error">⚠️ Analysis failed: {exc}</div>', "", ""

    detected_brand = data.get("brand", "")
    if detected_brand in ("Not visible", "Unknown", "—"):
        detected_brand = ""
    detected_name = data.get("pickle_name", "") or data.get("style", "")

    return _render_photo_analysis_html(data), detected_name, detected_brand
