import gradio as gr
from db import get_pickle_choices
from ai_features import som_placeholder


def build_sommelier_tab():
    with gr.Tab("Sommelier"):
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

    return som_dropdown, som_btn, som_out
