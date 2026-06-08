from db import _query_leaderboard, _query_pickle_profiles, get_recent_reviews_df


def _score_bar(val):
    pct   = int((float(val) / 10) * 100)
    color = "#52a81e" if float(val) >= 7 else "#f59e0b" if float(val) >= 4 else "#ef4444"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;">'
        f'<span style="background:#e5e7eb;border-radius:4px;height:6px;width:50px;'
        f'display:inline-block;vertical-align:middle;">'
        f'<span style="background:{color};border-radius:4px;height:6px;width:{pct}%;display:block;"></span>'
        f'</span><span style="font-weight:700;color:{color};min-width:18px;font-size:0.85rem;">{val}</span>'
        f'</span>'
    )


def _buy_badge(pct):
    pct    = int(pct) if pct is not None else 0
    color  = "#15803d" if pct >= 70 else "#b45309" if pct >= 40 else "#dc2626"
    bg     = "#dcfce7" if pct >= 70 else "#fef3c7" if pct >= 40 else "#fee2e2"
    border = "#86efac" if pct >= 70 else "#fcd34d" if pct >= 40 else "#fca5a5"
    return (
        f'<span style="background:{bg};color:{color};border:1px solid {border};'
        f'font-size:0.78rem;font-weight:700;padding:3px 10px;border-radius:100px;white-space:nowrap;">'
        f'{pct}%</span>'
    )


_LB_EMPTY = """
<div class="lb-empty">
    <div style="font-size:4rem;margin-bottom:12px;">🥒</div>
    <h3 style="margin:0 0 8px;font-size:1.2rem;color:#1a2e0e;font-weight:700;">No pickles ranked yet!</h3>
    <p style="margin:0;color:#6b7280;font-size:0.95rem;">Be the first to rate a pickle and claim the top spot. 🏆</p>
</div>
"""


def get_leaderboard_html(sort_by="⭐ Overall"):
    df = _query_leaderboard(sort_by)
    if df.empty:
        return _LB_EMPTY

    medals     = {1: "🥇", 2: "🥈", 3: "🥉"}
    row_classes = {1: "rank-gold", 2: "rank-silver", 3: "rank-bronze"}

    rows_html = ""
    for _, row in df.iterrows():
        rank    = int(row["rank"])
        medal   = medals.get(rank, f'<span style="color:#9ca3af;font-weight:700;font-size:0.85rem;">{rank}</span>')
        row_cls = row_classes.get(rank, "")
        n       = int(row["review_count"])
        buy_pct = int(row.get("buy_again_pct", 0) or 0)

        rows_html += f"""
        <tr class="lb-row {row_cls}">
            <td class="lb-rank">{medal}</td>
            <td class="lb-name"><span class="pickle-pill">{row['pickle_name']}</span></td>
            <td class="lb-brand lb-col-md">{row['brand']}</td>
            <td class="lb-score">{_score_bar(row['avg_overall'])}</td>
            <td class="lb-score lb-col-lg">{_score_bar(row['avg_crunch'])}</td>
            <td class="lb-score lb-col-lg">{_score_bar(row['avg_sour'])}</td>
            <td class="lb-score lb-col-lg">{_score_bar(row['avg_garlic'])}</td>
            <td>{_buy_badge(buy_pct)}</td>
            <td class="lb-col-md"><span class="review-badge">{n} {"review" if n == 1 else "reviews"}</span></td>
        </tr>
        """

    return f"""
    <div class="lb-wrapper">
        <table class="lb-table">
            <thead>
                <tr>
                    <th>#</th><th>🥒 Pickle</th>
                    <th class="lb-col-md">Brand</th>
                    <th>⭐ Overall</th>
                    <th class="lb-col-lg">🔊 Crunch</th>
                    <th class="lb-col-lg">😬 Sour</th>
                    <th class="lb-col-lg">🧄 Garlic</th>
                    <th>🛒 Buy?</th>
                    <th class="lb-col-md">Reviews</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """


def search_pickles(name_query="", brand_query=""):
    name_q  = (name_query  or "").strip()
    brand_q = (brand_query or "").strip()

    if not name_q and not brand_q:
        return """
        <div class="lb-empty">
            <div style="font-size:3rem;margin-bottom:12px;">🔍</div>
            <p style="margin:0;color:#6b7280;font-size:0.95rem;">Type a pickle name or brand above to search.</p>
        </div>
        """

    df = _query_pickle_profiles(name_filter=name_q, brand_filter=brand_q)

    if df.empty:
        return """
        <div class="lb-empty">
            <div style="font-size:3rem;margin-bottom:12px;">🤷</div>
            <p style="margin:0;color:#6b7280;font-size:0.95rem;">No pickles matched. Try a different name or brand.</p>
        </div>
        """

    count     = len(df)
    rows_html = ""
    for _, row in df.iterrows():
        n       = int(row["review_count"])
        buy_pct = int(row.get("buy_again_pct", 0) or 0)
        rows_html += f"""
        <tr class="lb-row">
            <td class="lb-name"><span class="pickle-pill">{row['pickle_name']}</span></td>
            <td class="lb-brand lb-col-md">{row['brand']}</td>
            <td class="lb-score">{_score_bar(row['avg_overall'])}</td>
            <td class="lb-score lb-col-lg">{_score_bar(row['avg_crunch'])}</td>
            <td class="lb-score lb-col-lg">{_score_bar(row['avg_sour'])}</td>
            <td class="lb-score lb-col-lg">{_score_bar(row['avg_garlic'])}</td>
            <td>{_buy_badge(buy_pct)}</td>
            <td class="lb-col-md"><span class="review-badge">{n} {"review" if n == 1 else "reviews"}</span></td>
        </tr>
        """

    return f"""
    <p style="font-size:0.82rem;color:#6b7280;margin:0 0 10px;font-weight:600;
              text-transform:uppercase;letter-spacing:0.8px;">{count} result{"s" if count != 1 else ""}</p>
    <div class="lb-wrapper">
        <table class="lb-table">
            <thead>
                <tr>
                    <th>🥒 Pickle</th>
                    <th class="lb-col-md">Brand</th>
                    <th>⭐ Overall</th>
                    <th class="lb-col-lg">🔊 Crunch</th>
                    <th class="lb-col-lg">😬 Sour</th>
                    <th class="lb-col-lg">🧄 Garlic</th>
                    <th>🛒 Buy?</th>
                    <th class="lb-col-md">Reviews</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """


def get_recent_html():
    df = get_recent_reviews_df()
    if df.empty:
        return """
        <div class="lb-empty" style="border-style:dashed;">
            <div style="font-size:3rem;margin-bottom:12px;">🥒</div>
            <p style="margin:0;color:#6b7280;font-size:0.95rem;">No reviews yet — go rate some pickles!</p>
        </div>
        """

    cards = ""
    for _, r in df.iterrows():
        brand_clean = str(r["brand"]).strip()
        brand_html  = (
            f'<span class="review-brand">· {brand_clean}</span>'
            if brand_clean and brand_clean not in ("", "—") else ""
        )
        body_html = (
            f'<p class="review-body">"{r["review_text"]}"</p>'
            if str(r.get("review_text", "")).strip() else ""
        )
        spicy     = int(r.get("spiciness", 5) or 5)
        buy_val   = int(r.get("buy_again", 1) or 1)
        buy_badge = (
            '<span class="buy-badge buy-yes">🛒 Buy Again</span>'
            if buy_val else
            '<span class="buy-badge buy-no">👎 Pass</span>'
        )

        cards += f"""
        <div class="review-card">
            <div class="review-card-header">
                <div>
                    <span class="review-pickle-name">{r['pickle_name']}</span>
                    {brand_html}
                </div>
                <span class="review-date">{r['date']}</span>
            </div>
            <div class="review-scores">
                <span class="score-chip">⭐ {r['overall']}</span>
                <span class="score-chip">🔊 {r['crunchiness']}</span>
                <span class="score-chip">😬 {r['sourness']}</span>
                <span class="score-chip">🧄 {r['garlic']}</span>
                <span class="score-chip">🌶️ {spicy}</span>
                {buy_badge}
            </div>
            {body_html}
        </div>
        """

    return f'<div class="reviews-grid">{cards}</div>'


def get_analytics_html():
    total, total_pickles, highest, most_rev, avg_crunch, avg_sour, avg_garlic, buy_pct = (
        __import__("db").get_analytics()
    )

    if total == 0:
        return """
        <div class="lb-empty">
            <div style="font-size:4rem;margin-bottom:12px;">📊</div>
            <h3 style="margin:0 0 8px;font-size:1.2rem;color:#1a2e0e;font-weight:700;">No data yet!</h3>
            <p style="margin:0;color:#6b7280;font-size:0.95rem;">Submit some pickle reviews to see analytics here.</p>
        </div>
        """

    buy_color  = "#15803d" if buy_pct >= 70 else "#b45309" if buy_pct >= 40 else "#dc2626"

    def _card(icon, value, label, color="#1a2e0e"):
        return (
            f'<div class="stat-card">'
            f'<div class="stat-icon">{icon}</div>'
            f'<div class="stat-value" style="color:{color};">{value}</div>'
            f'<div class="stat-label">{label}</div>'
            f'</div>'
        )

    cards = (
        _card("📝", total,            "Total Reviews")
        + _card("🥒", total_pickles,  "Unique Pickles")
        + _card("🏆", highest,        "Highest Rated")
        + _card("🌟", most_rev,       "Most Reviewed")
        + _card("🔊", f"{avg_crunch}/10", "Avg Crunchiness")
        + _card("😬", f"{avg_sour}/10",   "Avg Sourness")
        + _card("🧄", f"{avg_garlic}/10", "Avg Garlic")
        + _card("🛒", f"{int(buy_pct)}%", "Buy Again", buy_color)
    )

    return f'<div class="stat-grid">{cards}</div>'
