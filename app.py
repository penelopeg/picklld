import gradio as gr
import os

from db import init_db, save_photo, insert_review, get_pickle_choices, get_top_pickles_df, SORT_OPTIONS
from renderers import get_leaderboard_html, get_recent_html, search_pickles, get_analytics_html
from ai_features import generate_sommelier, analyze_pickle_photo, som_placeholder, scan_placeholder

init_db()


def submit_review(pickle_name_v, brand_v, overall_v, crunchiness_v, sourness_v,
                  garlic_v, spiciness_v, buy_again_v, review_text_v, photo_v):
    _NO_CHANGE = (gr.update(),) * 9  # form fields unchanged on validation error

    if not pickle_name_v or not pickle_name_v.strip():
        return ("⚠️ Please enter a pickle name!", *_NO_CHANGE,
                get_leaderboard_html(), get_recent_html(), get_analytics_html())

    photo_path = save_photo(photo_v, pickle_name_v.strip())
    try:
        insert_review(
            pickle_name_v, brand_v,
            int(overall_v), int(crunchiness_v), int(sourness_v),
            int(garlic_v), int(spiciness_v),
            buy_again_v == "Yes",
            review_text_v, photo_path,
        )
    except Exception as exc:
        return (f"⚠️ Failed to save: {exc}", *_NO_CHANGE,
                get_leaderboard_html(), get_recent_html(), get_analytics_html())

    return (
        "✅ Pickled! Your review is brined and bottled. 🥒",
        gr.update(value=""),     # pickle_name
        gr.update(value=""),     # brand
        gr.update(value=7),      # overall
        gr.update(value=7),      # crunchiness
        gr.update(value=7),      # sourness
        gr.update(value=7),      # garlic
        gr.update(value=5),      # spiciness
        gr.update(value="Yes"),  # buy_again
        gr.update(value=""),     # review_text
        # photo deliberately not cleared — user may want to view it
        get_leaderboard_html(), get_recent_html(), get_analytics_html(),
    )


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
.hero-tag:hover { background: rgba(255,255,255,0.17); }

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
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
    color: var(--muted) !important;
    border: none !important;
}
.tab-nav button.selected {
    background: linear-gradient(135deg, var(--pkl-mid) 0%, var(--pkl-bright) 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 2px 10px rgba(46,112,18,0.38) !important;
}

/* ── Cards ── */
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
.pkl-card.form:hover { box-shadow: var(--sh-md) !important; }
.pkl-card > .form {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
}

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

/* ── Section titles ── */
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
}
#submit-btn:hover {
    transform: translateY(-3px) scale(1.01) !important;
    box-shadow: 0 8px 28px rgba(46,112,18,0.52) !important;
}
#submit-btn:active { transform: translateY(0) scale(0.99) !important; }

/* ── Status box ── */
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

/* ── Leaderboard table ── */
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
.lb-rank     { font-size: 1.35rem; text-align: center; width: 52px; }
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
.lb-brand  { color: var(--muted); font-size: 0.84rem; }
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

/* ── Buy Again badges ── */
.buy-badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 100px;
    white-space: nowrap;
}
.buy-yes { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
.buy-no  { background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; }

/* ── Analytics stat cards ── */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
}
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    padding: 20px 16px;
    text-align: center;
    box-shadow: var(--sh-sm);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.stat-card:hover { box-shadow: var(--sh-md); transform: translateY(-2px); }
.stat-icon  { font-size: 2rem; margin-bottom: 8px; }
.stat-value {
    font-size: 1.55rem;
    font-weight: 900;
    color: var(--pkl-dark);
    letter-spacing: -0.8px;
    line-height: 1.1;
    word-break: break-word;
}
.stat-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-top: 6px;
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
.review-card:hover { box-shadow: var(--sh-md); transform: translateY(-2px); }
.review-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 10px;
}
.review-pickle-name { font-weight: 700; font-size: 0.93rem; color: var(--pkl-dark); }
.review-brand       { font-size: 0.78rem; color: var(--muted); margin-left: 4px; }
.review-date        { font-size: 0.74rem; color: var(--muted); white-space: nowrap; margin-top: 2px; }
.review-scores      { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
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
.scan-header   { margin-bottom: 16px; }
.scan-title    {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: var(--pkl-mid);
}
.scan-pills    { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.scan-pill {
    flex: 1;
    min-width: 110px;
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
.scan-pill-value { display: block; font-size: 0.92rem; font-weight: 700; color: var(--pkl-dark); }
.scan-block          { margin-bottom: 14px; }
.scan-block:last-child { margin-bottom: 0; }
.scan-block-label {
    font-size: 0.67rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--muted);
    margin-bottom: 5px;
}
.scan-block-body { font-size: 0.87rem; color: var(--text); line-height: 1.6; }

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
    margin-bottom: 16px;
    padding-bottom: 18px;
    border-bottom: 1px solid rgba(255,255,255,0.11);
}
.som-icon  { font-size: 2.4rem; line-height: 1; }
.som-name  { font-size: 1.35rem; font-weight: 800; color: #d4f582; letter-spacing: -0.4px; line-height: 1.2; }
.som-meta  { font-size: 0.8rem; color: rgba(255,255,255,0.55); margin-top: 4px; }
.som-brand { color: rgba(255,255,255,0.7); }
.som-verdict {
    background: rgba(212,245,130,0.12);
    border: 1px solid rgba(212,245,130,0.28);
    border-radius: var(--r-sm);
    padding: 12px 16px;
    margin-bottom: 16px;
    font-size: 0.9rem;
    font-weight: 600;
    color: #d4f582;
    font-style: italic;
}
.som-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
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
.som-card p  { font-size: 0.87rem; color: rgba(255,255,255,0.82); line-height: 1.65; margin: 0; }
.som-notes   { font-style: italic !important; color: rgba(255,255,255,0.9) !important; }
.som-tags    { display: flex; flex-wrap: wrap; gap: 7px; }
.som-tag {
    background: rgba(168,224,99,0.14);
    border: 1px solid rgba(168,224,99,0.28);
    color: #d4f582;
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 0.77rem;
    font-weight: 600;
}
.som-tag-alt { background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.25); color: #fcd34d; }
.som-error {
    padding: 18px 20px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: var(--r-md);
    color: #dc2626;
    font-size: 0.88rem;
    line-height: 1.5;
}

/* ── Responsive — hide table columns on small screens ── */
@media (max-width: 760px) {
    .lb-col-lg { display: none !important; }
}
@media (max-width: 500px) {
    .lb-col-md { display: none !important; }
}

/* ── Mobile ── */
@media (max-width: 640px) {
    .hero             { padding: 40px 20px 36px; border-radius: var(--r-md); margin: 12px 0 16px; }
    .hero-title       { font-size: 2.7rem; letter-spacing: -1.5px; }
    .hero-icon        { font-size: 3.8rem; }
    .hero-sub         { font-size: 0.92rem; }
    .hero-tag         { font-size: 0.78rem; padding: 5px 12px; }
    .gradio-container { padding: 0 8px 32px !important; }
    .pkl-card,
    .pkl-card.form    { padding: 16px !important; }
    .lb-table         { font-size: 0.8rem; }
    .lb-table thead th,
    .lb-table td      { padding: 10px 10px; }
    .reviews-grid     { grid-template-columns: 1fr; }
    .stat-grid        { grid-template-columns: repeat(2, 1fr); }
    .stat-value       { font-size: 1.25rem; }
    #submit-btn       { font-size: 1rem !important; }
    .tab-nav button   { padding: 9px 12px !important; font-size: 0.82rem !important; }
    .som-grid         { grid-template-columns: 1fr; }
    .scan-pills       { flex-direction: column; }
}
"""


with gr.Blocks(title="Pickldd 🥒") as demo:

    gr.HTML("""
    <div class="hero">
        <span class="hero-icon">🥒</span>
        <h1 class="hero-title">Pickl<span class="accent">dd</span></h1>
        <p class="hero-sub">The internet's most <em>serious</em> pickle review platform.</p>
        <div class="hero-tags">
            <span class="hero-tag">🧄 Garlic Lovers</span>
            <span class="hero-tag">🔊 Crunch Seekers</span>
            <span class="hero-tag">😬 Sour Heads</span>
            <span class="hero-tag">🛒 Buy Again?</span>
            <span class="hero-tag">🌶️ Heat Hunters</span>
        </div>
    </div>
    """)

    with gr.Tabs():

        # ── Tab 1: Rate a Pickle ─────────────────────────────────────────────
        with gr.Tab("🥒 Rate"):

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
                    sourness  = gr.Slider(1, 10, value=7, step=1, label="😬 Sourness")
                    garlic    = gr.Slider(1, 10, value=7, step=1, label="🧄 Garlic Level")
                with gr.Row():
                    spiciness = gr.Slider(1, 10, value=5, step=1, label="🌶️ Spiciness")
                    buy_again = gr.Radio(
                        choices=["Yes", "No"],
                        value="Yes",
                        label="🛒 Would you buy this pickle again?",
                        scale=1,
                    )

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

        # ── Tab 2: Scan a Jar ────────────────────────────────────────────────
        with gr.Tab("📸 Scan"):

            with gr.Row(equal_height=True):
                with gr.Column(scale=1):
                    scan_image = gr.Image(
                        label="Pickle Jar Photo",
                        type="filepath",
                        sources=["upload", "webcam"],
                    )
                    scan_btn = gr.Button("🔍 Analyze Jar", variant="primary")
                with gr.Column(scale=1):
                    scan_out = gr.HTML(value=scan_placeholder)

        # ── Tab 3: Leaderboard ───────────────────────────────────────────────
        with gr.Tab("🏆 Leaderboard"):

            with gr.Group(elem_classes="sort-card"):
                with gr.Row(equal_height=True):
                    sort_dd     = gr.Dropdown(
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

        # ── Tab 4: Sommelier ─────────────────────────────────────────────────
        with gr.Tab("🍷 Sommelier"):

            with gr.Group(elem_classes="sort-card"):
                with gr.Row(equal_height=True):
                    som_dropdown = gr.Dropdown(
                        choices=get_pickle_choices(),
                        label="Select a Pickle",
                        scale=3,
                        container=False,
                    )
                    som_btn = gr.Button("✨ Consult the Sommelier", variant="primary", scale=1)

            som_out = gr.HTML(value=som_placeholder)

        # ── Tab 5: Analytics ─────────────────────────────────────────────────
        with gr.Tab("📊 Analytics"):

            with gr.Row():
                analytics_refresh = gr.Button("🔄 Refresh", variant="secondary", scale=0)

            analytics_out = gr.HTML(value=get_analytics_html)

            top_chart = gr.BarPlot(
                value=get_top_pickles_df,
                x="Pickle",
                y="Avg Score",
                title="Top Pickles by Overall Rating",
                x_title="",
                y_title="Avg Score (out of 10)",
                height=350,
            )

        # ── Tab 6: Search ────────────────────────────────────────────────────
        with gr.Tab("🔍 Search"):

            with gr.Group(elem_classes="sort-card"):
                with gr.Row(equal_height=True):
                    search_name  = gr.Textbox(
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

    # ── Event wiring ─────────────────────────────────────────────────────────

    _submit_outputs = [
        status_msg,
        pickle_name, brand,
        overall, crunchiness, sourness, garlic, spiciness, buy_again,
        review_text,
        leaderboard_out, recent_out, analytics_out,
    ]

    submit_btn.click(
        fn=submit_review,
        inputs=[pickle_name, brand, overall, crunchiness, sourness, garlic,
                spiciness, buy_again, review_text, photo],
        outputs=_submit_outputs,
    ).then(fn=get_pickle_choices, outputs=[som_dropdown])

    scan_btn.click(
        fn=analyze_pickle_photo,
        inputs=[scan_image],
        outputs=[scan_out, pickle_name, brand],  # pre-fills the Rate form
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

    analytics_refresh.click(
        fn=lambda: (get_analytics_html(), get_top_pickles_df()),
        outputs=[analytics_out, top_chart],
    )

    som_btn.click(fn=generate_sommelier, inputs=[som_dropdown], outputs=[som_out])

    demo.load(fn=get_analytics_html, outputs=[analytics_out])
    demo.load(fn=get_pickle_choices, outputs=[som_dropdown])


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
        demo.launch(theme=gr.themes.Soft(), css=CSS, ssr_mode=False)
