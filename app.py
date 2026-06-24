import os
import gradio as gr

from db import init_db
from seed import seed_db
from ui.layout import build_demo
from ui.theme import PICKLE_THEME, CSS

init_db()
seed_db()
demo = build_demo()

try:
    from fastapi import FastAPI
    import uvicorn
    from tidewave.fastapi import Tidewave
    _fastapi_app = FastAPI()
    Tidewave().install(_fastapi_app)
    app = gr.mount_gradio_app(
        _fastapi_app,
        demo,
        path="/",
        theme=PICKLE_THEME,
        css=CSS,
        ssr_mode=False,
    )
except ImportError:
    app = None

if __name__ == "__main__":
    if app is not None and not os.environ.get("SPACE_ID"):
        uvicorn.run(app, host="0.0.0.0", port=7860)
    else:
        demo.launch(theme=PICKLE_THEME, css=CSS, ssr_mode=False)
