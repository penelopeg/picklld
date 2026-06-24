import gradio as gr

from db import save_photo, insert_review
from renderers import get_leaderboard_html, get_recent_html, get_analytics_html


def submit_review(pickle_name_v, brand_v, overall_v, crunchiness_v, sourness_v,
                  garlic_v, spiciness_v, buy_again_v, review_text_v, photo_v):
    _NO_CHANGE = (gr.update(),) * 9

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
        get_leaderboard_html(), get_recent_html(), get_analytics_html(),
    )
