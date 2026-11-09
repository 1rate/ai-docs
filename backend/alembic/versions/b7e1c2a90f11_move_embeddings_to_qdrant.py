"""move_embeddings_to_qdrant

Revision ID: b7e1c2a90f11
Revises: 04aac2d1eda6
Create Date: 2026-11-09 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b7e1c2a90f11"
down_revision: Union[str, None] = "04aac2d1eda6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("document_chunks", "embedding")


def downgrade() -> None:
    raise NotImplementedError("Embeddings are stored in Qdrant; restore DB from backup if needed")
