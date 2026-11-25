"""add is_admin to users

Revision ID: b5de423bba96
Revises: c202d82fcc90

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5de423bba96'
down_revision: Union[str, Sequence[str], None] = 'c202d82fcc90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the wrongly-typed String column left by c202d82fcc90
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_admin")
    # Re-add it as a real boolean
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")