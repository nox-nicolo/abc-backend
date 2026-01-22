# service/search/scoring.py

from __future__ import annotations


def normalize_text(s: str | None) -> str:
    return (s or "").strip().lower()


def text_relevance(text: str | None, q: str) -> int:
    """
    Simple relevance:
    - startswith match > contains match > no match
    """
    text_n = normalize_text(text)
    q_n = normalize_text(q)

    if not text_n or not q_n:
        return 0

    if text_n == q_n:
        return 40
    if text_n.startswith(q_n):
        return 25
    if q_n in text_n:
        return 12
    return 0


def price_closeness_score(price_min: int | None, price_max: int | None, target: int | None) -> int:
    """
    Gives a small boost if the service price is close to the user's target price.
    """
    if target is None:
        return 0
    if price_min is None and price_max is None:
        return 0

    # Use a representative price
    if price_min is not None and price_max is not None:
        avg = (price_min + price_max) / 2
    else:
        avg = float(price_min or price_max or 0)

    diff = abs(avg - target)

    if diff == 0:
        return 18
    if diff <= target * 0.2:
        return 12
    if diff <= target * 0.5:
        return 6
    return 0


def entity_base(entity: str) -> int:
    """
    Base weights: adjust anytime to change global priority.
    """
    # higher = more priority in search
    return {
        "service_priced": 100,
        "service_fallback": 70,
        "salon": 60,
        "user": 50,
        "hashtag": 40,
    }.get(entity, 0)


def compute_user_score(username: str | None, full_name: str | None, q: str) -> float:
    score = entity_base("user")
    score += max(text_relevance(username, q), text_relevance(full_name, q))
    return float(score)


def compute_salon_score(title: str | None, slogan: str | None, q: str, is_verified: bool) -> float:
    score = entity_base("salon")
    score += max(text_relevance(title, q), text_relevance(slogan, q))
    if is_verified:
        score += 8
    return float(score)


def compute_hashtag_score(tag: str | None, q: str, post_count: int) -> float:
    score = entity_base("hashtag")
    score += text_relevance(tag, q)
    # popularity cap
    score += min(int(post_count), 20)
    return float(score)


def compute_service_score(
    *,
    name: str,
    q: str,
    category: str,  # "major" | "minor"
    is_priced: bool,
    target_price: int | None,
    price_min: int | None,
    price_max: int | None,
) -> float:
    score = entity_base("service_priced" if is_priced else "service_fallback")

    # Relevance
    score += text_relevance(name, q)

    # Minor services are usually more "actionable"
    if category == "minor":
        score += 10

    # Price intent boosts priced offerings
    if target_price is not None:
        if is_priced:
            score += 30
            score += price_closeness_score(price_min, price_max, target_price)
        else:
            # fallback results are less useful when user typed price
            score -= 25

    return float(score)
