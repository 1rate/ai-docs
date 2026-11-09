"""add_document_chunks

Revision ID: d842650a359b
Revises: 3aec8c687d2d
Create Date: 2026-11-06 17:49:25.399162

"""

from typing import Sequence, Union

from alembic import op

revision: str = "d842650a359b"
down_revision: Union[str, None] = "3aec8c687d2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE document_chunks (
            id UUID NOT NULL,
            document_id UUID NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_document_id")
    op.execute("DROP TABLE IF EXISTS document_chunks")
