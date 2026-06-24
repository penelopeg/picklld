import gradio as gr
from db import SORT_OPTIONS
from renderers import get_leaderboard_html, get_recent_html


def build_leaderboard_tab():
    with gr.Tab("Leaderboard"):
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

    return sort_dd, refresh_btn, leaderboard_out, recent_out
