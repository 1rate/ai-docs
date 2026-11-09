"""add_user_names

Revision ID: 3aec8c687d2d
Revises: fbf42a08c4c6
Create Date: 2026-11-06 17:36:37.243013

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "3aec8c687d2d"
down_revision: Union[str, None] = "fbf42a08c4c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.execute("UPDATE users SET first_name = 'User' WHERE first_name IS NULL")
    op.alter_column("users", "first_name", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
