# service/trending/logic.py

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.posts.posts import Post

TREND_WINDOW_DAYS = 30


def apply_trending_logic(
    *,
    base_query,
    db: Session,
    user_id: str,   # kept for tracking / future
    limit: int,
):
    trend_since = datetime.utcnow() - timedelta(days=TREND_WINDOW_DAYS)

    # 1️⃣ Rank sub_services by frequency
    stats = (
        db.query(
            Post.sub_service_id,
            func.count(Post.id)
        )
        .filter(
            Post.created_at >= trend_since,
            Post.sub_service_id.isnot(None),
        )
        .group_by(Post.sub_service_id)
        .order_by(func.count(Post.id).desc())
        .all()
    )

    if not stats:
        return base_query

    total = sum(count for _, count in stats)

    allocations = {}
    remaining = limit

    for sub_service_id, count in stats:
        quota = max(1, int((count / total) * limit))
        allocations[sub_service_id] = quota
        remaining -= quota
        if remaining <= 0:
            break

    # 2️⃣ Collect post IDs (NO DISTINCT — safe)
    selected_post_ids = []

    for sub_service_id, quota in allocations.items():
        rows = (
            db.query(Post.id)
            .filter(
                Post.sub_service_id == sub_service_id,
                Post.created_at >= trend_since,
            )
            .order_by(Post.created_at.desc())
            .limit(quota)
            .all()
        )
        selected_post_ids.extend(r[0] for r in rows)

    if not selected_post_ids:
        return base_query

    return base_query.filter(Post.id.in_(selected_post_ids))
