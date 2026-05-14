"""add expired booking status

Revision ID: 20260514_0002
Revises: 20260512_0001
Create Date: 2026-05-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260514_0002"
down_revision: Union[str, None] = "20260512_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'EXPIRED'")


def downgrade() -> None:
    # PostgreSQL cannot remove an enum value directly. Keep downgrade safe by
    # refusing to leave rows with a status the previous enum cannot represent.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM bookings WHERE status = 'EXPIRED') THEN
                RAISE EXCEPTION 'Cannot downgrade while expired bookings exist';
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TYPE bookingstatus RENAME TO bookingstatus_old")
    op.execute(
        """
        CREATE TYPE bookingstatus AS ENUM (
            'PENDING',
            'CONFIRMED',
            'COMPLETED',
            'REJECTED',
            'CANCELLED',
            'NO_SHOW'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE bookings
        ALTER COLUMN status TYPE bookingstatus
        USING status::text::bookingstatus
        """
    )
    op.execute("DROP TYPE bookingstatus_old")
