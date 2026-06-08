import gradio as gr

pickles = []

def rate_pickle(name, rating, review):
    pickles.append(
        {
            "name": name,
            "rating": rating,
            "review": review
        }
    )

    leaderboard = sorted(
        pickles,
        key=lambda x: x["rating"],
        reverse=True
    )

    output = "\n".join(
        f"{p['name']} ⭐ {p['rating']}"
        for p in leaderboard
    )

    return output

with gr.Blocks() as demo:
    gr.Markdown("# 🥒 PickleRater")

    name = gr.Textbox(label="Pickle Brand")
    rating = gr.Slider(1, 10, value=5)
    review = gr.Textbox(label="Review")

    button = gr.Button("Submit")

    leaderboard = gr.Textbox(
        label="Top Pickles"
    )

    button.click(
        rate_pickle,
        [name, rating, review],
        leaderboard
    )

demo.launch()
