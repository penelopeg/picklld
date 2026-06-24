import gradio as gr
from db import get_top_pickles_df
from renderers import get_analytics_html


def build_analytics_tab():
    with gr.Tab("Analytics"):
        with gr.Row():
            analytics_refresh = gr.Button("🔄 Refresh", variant="secondary", scale=0)

        analytics_out = gr.HTML(value=get_analytics_html)

        top_chart = gr.BarPlot(
            value=get_top_pickles_df,
            x="Pickle",
            y="Avg Score",
            color="Theme",
            color_map={"Pickle": "#52a81e"},
            colors_in_legend=[],
            title="Top Pickles by Overall Rating",
            x_title="",
            y_title="Avg Score (out of 10)",
            height=350,
        )

    return analytics_refresh, analytics_out, top_chart
