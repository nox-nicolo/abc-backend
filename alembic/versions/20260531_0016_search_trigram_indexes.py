"""add trigram indexes for search

Revision ID: 20260531_0016
Revises: 20260531_0015
Create Date: 2026-05-31
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260531_0016"
down_revision: Union[str, None] = "20260531_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRIGRAM_INDEXES = (
    ("ix_users_username_trgm", "users", "username"),
    ("ix_users_name_trgm", "users", "name"),
    ("ix_salons_title_trgm", "salons", "title"),
    ("ix_salons_slogan_trgm", "salons", "slogan"),
    ("ix_hashtags_name_trgm", "hashtags", "name"),
    ("ix_services_name_trgm", "services", "name"),
    ("ix_sub_services_name_trgm", "sub_services", "name"),
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for index_name, table_name, column_name in TRIGRAM_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {index_name} "
            f"ON {table_name} USING gin ({column_name} gin_trgm_ops)"
        )

    op.create_index(
        "ix_salon_service_prices_search_active",
        "salon_service_prices",
        ["status", "service_id", "sub_service_id"],
        unique=False,
    )
    op.create_index(
        "ix_salon_service_prices_search_price",
        "salon_service_prices",
        ["status", "price_min", "price_max"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index(
        "ix_salon_service_prices_search_price",
        table_name="salon_service_prices",
    )
    op.drop_index(
        "ix_salon_service_prices_search_active",
        table_name="salon_service_prices",
    )
    for index_name, _, _ in reversed(TRIGRAM_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
