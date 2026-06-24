import gradio as gr
from ai_features import scan_placeholder


def build_scan_tab():
    with gr.Tab("Scan"):
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

    return scan_image, scan_btn, scan_out
