"""hot path indexes

Revision ID: 20260508_0002
Revises: 20260508_0001
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260508_0002"
down_revision: Union[str, None] = "20260508_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEXES = [
    ("ix_posts_status_created", "posts", "status, created_at"),
    ("ix_posts_user_created", "posts", "user_id, created_at"),
    ("ix_posts_sub_service_created", "posts", "sub_service_id, created_at"),
    ("ix_media_data_post_created", "media_data", "post_id, created_at"),
    ("ix_post_bookmarks_user_created", "post_bookmarks", "user_id, created_at"),
    ("ix_post_bookmarks_user_post", "post_bookmarks", "user_id, post_id"),
    ("ix_post_mentions_mentioned_created", "post_mentions", "mentioned_user_id, created_at"),
    ("ix_post_mentions_post_mentioned", "post_mentions", "post_id, mentioned_user_id"),
    ("ix_post_hashtags_hashtag_created", "post_hashtags", "hashtag_id, created_at"),
    ("ix_post_hashtags_post_hashtag", "post_hashtags", "post_id, hashtag_id"),
    ("ix_post_shares_post_created_user", "post_shares", "post_id, share_user_id"),
    ("ix_post_shares_share_user", "post_shares", "share_user_id"),
    ("ix_post_shares_received_user", "post_shares", "user_id"),
    ("ix_post_views_post_viewed", "post_views", "post_id, viewed_at"),
    ("ix_post_views_user_viewed", "post_views", "user_id, viewed_at"),
    ("ix_post_likes_post_liked", "post_likes", "post_id, liked"),
    ("ix_post_likes_user_created", "post_likes", "user_id, created_at"),
    ("ix_post_likes_post_user", "post_likes", "post_id, user_id"),
    ("ix_post_comments_post_parent_created", "post_comments", "post_id, comment_id, created_at"),
    ("ix_post_comments_user_created", "post_comments", "user_com, created_at"),
    ("ix_post_reports_post_status", "post_reports", "post_id, status"),
    ("ix_post_reports_user_created", "post_reports", "user_id, created_at"),
    ("ix_bookings_customer_status_start", "bookings", "customer_id, status, start_at"),
    ("ix_bookings_salon_status_start", "bookings", "salon_id, status, start_at"),
    ("ix_bookings_service_status_start", "bookings", "salon_service_price_id, status, start_at"),
    ("ix_bookings_customer_start", "bookings", "customer_id, start_at"),
    ("ix_bookings_salon_start", "bookings", "salon_id, start_at"),
    ("ix_bookings_created", "bookings", "created_at"),
    ("ix_notifications_recipient_read_created", "notifications", "recipient_id, is_read, created_at"),
    ("ix_notifications_actor_created", "notifications", "actor_id, created_at"),
    ("ix_search_histories_user_created", "search_histories", "user_id, created_at"),
    ("ix_search_histories_user_query", "search_histories", "user_id, query"),
    ("ix_search_histories_entity_entity_id", "search_histories", "entity, entity_id"),
    ("ix_users_role_access_created", "users", "role, account_access, created_at"),
    ("ix_users_name", "users", "name"),
    ("ix_salon_followers_user_created", "salon_followers", "user_id, created_at"),
    ("ix_salon_followers_salon_created", "salon_followers", "salon_id, created_at"),
    ("ix_salon_followers_notifications", "salon_followers", "salon_id, notifications_enabled"),
    ("ix_salon_blocks_user_created", "salon_blocks", "user_id, created_at"),
    ("ix_salon_blocks_salon_created", "salon_blocks", "salon_id, created_at"),
    ("ix_salon_reports_user_created", "salon_reports", "user_id, created_at"),
    ("ix_salon_reports_salon_created", "salon_reports", "salon_id, created_at"),
]

EXPRESSION_INDEXES = [
    ("ix_users_username_lower", "users", "lower(username)"),
    ("ix_users_name_lower", "users", "lower(name)"),
    ("ix_hashtags_name_lower", "hashtags", "lower(name)"),
    ("ix_services_name_lower", "services", "lower(name)"),
    ("ix_sub_services_name_lower", "sub_services", "lower(name)"),
]


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})")

    for name, table, expression in EXPRESSION_INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({expression})")


def downgrade() -> None:
    for name, _, _ in reversed(EXPRESSION_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")

    for name, _, _ in reversed(INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")
