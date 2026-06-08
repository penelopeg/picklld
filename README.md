# Pickldd - Pickle Rater

Rate and review pickle products. Track crunchiness, sourness, garlic level, and overall quality. View a live leaderboard sorted by average rating.

## Setup

**Requirements:** Python 3.9 or later.

1. Clone the repository and enter the project directory:

```bash
git clone <repo-url>
cd pickldd
```

2. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the app

```bash
python app.py
```

The app will be available at `http://localhost:7860` by default. The SQLite database (`pickldd.db`) and the `uploads/` folder for photos are created automatically on first run.
