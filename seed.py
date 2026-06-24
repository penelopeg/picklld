from db import init_db, insert_review, DB_PATH
import sqlite3


_SAMPLE_REVIEWS = [
    ("Claussen Whole Dill",    "Claussen",  9, 10, 8, 7, 3, True,  "The gold standard. Snappy, garlicky, never mushy. Refrigerator section goat."),
    ("Claussen Whole Dill",    "Claussen",  8,  9, 7, 8, 2, True,  "Can't be beat fresh out of the jar. Perfect crunch every time."),
    ("Bread & Butter Chips",   "Vlasic",    6,  6, 4, 3, 1, False, "Sweet and mild — not my style, but my grandma loves them."),
    ("Bread & Butter Chips",   "Vlasic",    7,  7, 3, 2, 1, True,  "Great on burgers if you like sweet pickles."),
    ("Kosher Dill Spears",     "Bubbies",   10, 9, 10, 9, 4, True, "Fermented, funky, alive. These taste like actual pickles."),
    ("Kosher Dill Spears",     "Bubbies",   9,  8, 10, 8, 3, True, "The brine alone is worth it. Kimchi of the pickle world."),
    ("Italian Dill Spears",    "Grillo's",  9, 10, 7, 9, 2, True,  "Garlicky and fresh. The ziplock bag is weirdly charming."),
    ("Italian Dill Spears",    "Grillo's",  8,  9, 6, 9, 2, True,  "Light brine, heavy garlic — exactly what a deli pickle should be."),
    ("Spicy Dill Pickles",     "Wickles",   8,  8, 7, 5, 9, True,  "Real heat that builds. I put these on everything."),
    ("Spicy Dill Pickles",     "Wickles",   7,  7, 6, 4, 8, True,  "Good kick. Could use a touch more garlic."),
    ("Garlic Dill Pickles",    "Rick's",    8,  9, 8, 10, 3, True, "So much garlic. In the best possible way."),
    ("Cornichons",             "Maille",    7,  8, 9, 4, 2, True,  "Tiny and intensely sour. Perfect with a charcuterie board."),
    ("Polish Dill Spears",     "Claussen",  8,  9, 8, 6, 3, True,  "Slightly more sour than the standard dill. Love it."),
    ("Hamburger Dill Chips",   "Mt. Olive", 5,  6, 6, 4, 1, False, "Fine for a cookout, forgettable otherwise."),
]


def seed_db():
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    conn.close()
    if count > 0:
        return
    for args in _SAMPLE_REVIEWS:
        insert_review(*args)


if __name__ == "__main__":
    init_db()
    seed_db()
    print("Seeded sample pickle reviews.")
