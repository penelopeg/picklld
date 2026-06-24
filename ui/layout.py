import gradio as gr

from db import get_pickle_choices, get_top_pickles_df
from renderers import get_leaderboard_html, get_recent_html, get_analytics_html, search_pickles
from ai_features import generate_sommelier, analyze_pickle_photo
from handlers import submit_review
from ui.theme import TAB_ICON_JS
from ui.tabs.rate import build_rate_tab
from ui.tabs.scan import build_scan_tab
from ui.tabs.leaderboard import build_leaderboard_tab
from ui.tabs.sommelier import build_sommelier_tab
from ui.tabs.analytics import build_analytics_tab
from ui.tabs.search import build_search_tab


def build_demo():
    with gr.Blocks(title="Pickldd 🥒", js=TAB_ICON_JS) as demo:

        gr.HTML("""
        <div class="hero">
            <span class="hero-icon">🥒</span>
            <h1 class="hero-title">Pickl<span class="accent">dd</span></h1>
            <p class="hero-sub">The internet's most <em>serious</em> pickle review platform.</p>
        </div>
        """)

        with gr.Tabs():
            pickle_name, brand, overall, crunchiness, sourness, garlic, spiciness, buy_again, review_text, photo, submit_btn, status_msg = build_rate_tab()
            scan_image, scan_btn, scan_out = build_scan_tab()
            sort_dd, refresh_btn, leaderboard_out, recent_out = build_leaderboard_tab()
            som_dropdown, som_btn, som_out = build_sommelier_tab()
            analytics_refresh, analytics_out, top_chart = build_analytics_tab()
            search_name, search_brand, search_out = build_search_tab()

        # ── Event wiring ──────────────────────────────────────────────────────

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
            outputs=[scan_out, pickle_name, brand],
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

    return demo
