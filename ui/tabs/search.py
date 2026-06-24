import gradio as gr
from renderers import search_pickles


def build_search_tab():
    with gr.Tab("Search"):
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

    return search_name, search_brand, search_out
