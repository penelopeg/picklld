---
title: Pickldd
emoji: 🥒
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: "6.17.3"
app_file: app.py
pinned: false
tags:
  - build-small-hackathon
  - track:thousand-token-wood
  - achievement:offbrand
  - achievement:tinytitan
  - gradio
  - pickle
  - huggingface
  - vision
---

# Pickldd 🥒 — Pickle Rater

The internet's most *serious* pickle review platform. Rate pickles by crunchiness, sourness, garlic level, and spice. The AI Pickle Sommelier writes tasting notes. Scan a jar photo to auto-detect brand and style.

**🔗 Links**
- 🚀 [Live Space](https://huggingface.co/spaces/build-small-hackathon/picklld)
- 💻 [GitHub](https://github.com/penelopeg/picklld)
- 📣 [Social post](https://x.com/penelope_tg/status/2066646172379369775)

## Demo

<video src="https://github.com/penelopeg/picklld/raw/main/demo.webm" controls width="100%"></video>

## AI features (Tiny Titan — all models ≤4B)

| Feature | Model | Params |
|---|---|---|
| 🍷 Pickle Sommelier | `Qwen/Qwen2.5-3B-Instruct` | 3B |
| 📸 Jar photo scan | `google/gemma-3-4b-it` | 4B |

Both served via [HF Inference Providers](https://huggingface.co/docs/inference-providers) (featherless-ai). Requires `HF_TOKEN` set as a Space secret.

## Setup

**Requirements:** Python 3.9 or later.

```bash
git clone https://github.com/penelopeg/picklld
cd picklld
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app runs at `http://localhost:7860`. Set `HF_TOKEN` in your environment to enable AI features.
