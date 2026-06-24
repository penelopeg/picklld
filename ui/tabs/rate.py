import gradio as gr


def build_rate_tab():
    with gr.Tab("Rate"):
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
                sourness = gr.Slider(1, 10, value=7, step=1, label="😬 Sourness")
                garlic   = gr.Slider(1, 10, value=7, step=1, label="🧄 Garlic Level")
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

    return pickle_name, brand, overall, crunchiness, sourness, garlic, spiciness, buy_again, review_text, photo, submit_btn, status_msg
