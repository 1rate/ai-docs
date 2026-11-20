"""align models with architecture

Revision ID: c1a2b3d4e5f6
Revises: b7e1c2a90f11
Create Date: 2026-11-20 18:50:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "b7e1c2a90f11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # --- users ---
    op.execute("UPDATE users SET last_name = '' WHERE last_name IS NULL")
    op.alter_column("users", "last_name", existing_type=sa.String(length=100), nullable=False)
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN email TYPE CITEXT
        USING email::citext
        """
    )
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- documents ---
    op.add_column("documents", sa.Column("file_hash", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.execute(
        """
        UPDATE documents
        SET
            file_hash = encode(sha256(convert_to(id::text || storage_key, 'UTF8')), 'hex'),
            size_bytes = 0
        WHERE file_hash IS NULL
        """
    )
    op.alter_column("documents", "file_hash", nullable=False)
    op.alter_column("documents", "size_bytes", nullable=False)
    op.create_unique_constraint("uq_documents_file_hash", "documents", ["file_hash"])

    op.alter_column(
        "documents",
        "filename",
        existing_type=sa.String(length=512),
        type_=sa.String(length=500),
        existing_nullable=False,
    )
    op.execute("ALTER TABLE documents RENAME COLUMN content_type TO mime_type")
    op.execute("UPDATE documents SET mime_type = 'application/octet-stream' WHERE mime_type IS NULL")
    op.alter_column(
        "documents",
        "mime_type",
        existing_type=sa.String(length=255),
        type_=sa.String(length=100),
        nullable=False,
    )
    op.alter_column(
        "documents",
        "storage_key",
        existing_type=sa.String(length=1024),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.drop_constraint("documents_storage_key_key", "documents", type_="unique")

    op.add_column("documents", sa.Column("doc_type", sa.String(length=50), nullable=True))
    op.add_column("documents", sa.Column("doc_number", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("doc_date", sa.Date(), nullable=True))
    op.add_column("documents", sa.Column("jurisdiction", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("official_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("language", sa.String(length=10), server_default="ru", nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index("idx_documents_doc_date", "documents", ["doc_date"])
    op.create_index(
        "idx_documents_metadata",
        "documents",
        ["metadata"],
        postgresql_using="gin",
    )
    op.drop_index("ix_documents_uploaded_by", table_name="documents")

    # --- document_chunks ---
    op.add_column("document_chunks", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("document_chunks", sa.Column("token_count", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("section_title", sa.String(length=500), nullable=True))
    op.add_column("document_chunks", sa.Column("section_number", sa.String(length=50), nullable=True))
    op.add_column("document_chunks", sa.Column("char_start", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("char_end", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("qdrant_point_id", sa.UUID(), nullable=True))
    op.add_column(
        "document_chunks",
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE document_chunks
        SET
            content_hash = encode(sha256(convert_to(content, 'UTF8')), 'hex'),
            qdrant_point_id = id,
            embedding_model = 'legacy',
            token_count = cardinality(string_to_array(btrim(content), ' '))
        WHERE content_hash IS NULL
        """
    )
    op.alter_column("document_chunks", "content_hash", nullable=False)
    op.alter_column("document_chunks", "qdrant_point_id", nullable=False)
    op.alter_column("document_chunks", "embedding_model", nullable=False)
    op.create_unique_constraint(
        "uq_document_chunks_qdrant_point_id",
        "document_chunks",
        ["qdrant_point_id"],
    )
    op.create_unique_constraint(
        "uq_chunks_document_index",
        "document_chunks",
        ["document_id", "chunk_index"],
    )
    op.create_index("idx_chunks_content_hash", "document_chunks", ["content_hash"])
    op.execute(
        """
        UPDATE documents d
        SET chunk_count = COALESCE(c.cnt, 0)
        FROM (
            SELECT document_id, COUNT(*) AS cnt
            FROM document_chunks
            GROUP BY document_id
        ) c
        WHERE d.id = c.document_id
        """
    )

    # --- document_index_status ---
    op.create_table(
        "document_index_status",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("qdrant_collection", sa.String(length=100), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "indexed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "qdrant_collection", name="uq_doc_index_collection"),
    )
    op.create_index(
        "uq_doc_index_current",
        "document_index_status",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.create_index("idx_doc_index_model", "document_index_status", ["embedding_model"])
    op.execute(
        """
        INSERT INTO document_index_status (
            id, document_id, embedding_model, qdrant_collection, chunk_count, is_current
        )
        SELECT
            gen_random_uuid(),
            d.id,
            COALESCE(
                (SELECT embedding_model FROM document_chunks WHERE document_id = d.id LIMIT 1),
                'legacy'
            ),
            'document_chunks',
            d.chunk_count,
            true
        FROM documents d
        WHERE d.status = 'ready' AND d.chunk_count > 0
        """
    )

    # --- chats ---
    op.alter_column(
        "chats",
        "title",
        existing_type=sa.String(length=255),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
    op.add_column(
        "chats",
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("chats", sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "chats",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.drop_index("ix_chats_user_id", table_name="chats")
    op.create_index("idx_chats_user", "chats", ["user_id", "last_message_at"])

    # --- messages ---
    op.add_column("messages", sa.Column("parent_message_id", sa.UUID(), nullable=True))
    op.add_column(
        "messages",
        sa.Column("variant_index", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("messages", sa.Column("model_name", sa.String(length=100), nullable=True))
    op.add_column("messages", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("completion_tokens", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("cost", sa.Numeric(12, 6), nullable=True))
    op.add_column(
        "messages",
        sa.Column("cost_currency", sa.String(length=10), server_default="USD", nullable=True),
    )
    op.add_column("messages", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("langfuse_trace_id", sa.String(length=100), nullable=True))
    op.add_column(
        "messages",
        sa.Column("raw_request", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_parent_message_id",
        "messages",
        "messages",
        ["parent_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_index("ix_messages_chat_id", table_name="messages")
    op.create_index("idx_messages_chat", "messages", ["chat_id", "created_at"])
    op.create_index("idx_messages_parent", "messages", ["parent_message_id", "variant_index"])

    # Existing assistant messages need a parent before the CHECK can be applied.
    op.execute(
        """
        DO $$
        DECLARE
            r RECORD;
            parent_id UUID;
        BEGIN
            FOR r IN
                SELECT id, chat_id
                FROM messages
                WHERE role = 'assistant' AND parent_message_id IS NULL
            LOOP
                parent_id := gen_random_uuid();
                INSERT INTO messages (id, chat_id, role, content, variant_index)
                VALUES (parent_id, r.chat_id, 'user', '[legacy placeholder]', 0);
                UPDATE messages SET parent_message_id = parent_id WHERE id = r.id;
            END LOOP;
        END $$;
        """
    )
    op.create_check_constraint(
        "ck_messages_assistant_parent",
        "messages",
        "role <> 'assistant' OR parent_message_id IS NOT NULL",
    )

    # --- citations ---
    op.create_table(
        "citations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.REAL(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_citations_message", "citations", ["message_id"])
    op.create_index("idx_citations_chunk", "citations", ["chunk_id"])
    op.create_index("idx_citations_document", "citations", ["document_id"])


def downgrade() -> None:
    op.drop_index("idx_citations_document", table_name="citations")
    op.drop_index("idx_citations_chunk", table_name="citations")
    op.drop_index("idx_citations_message", table_name="citations")
    op.drop_table("citations")

    op.drop_index("idx_messages_parent", table_name="messages")
    op.drop_index("idx_messages_chat", table_name="messages")
    op.create_index("ix_messages_chat_id", "messages", ["chat_id"])
    op.drop_constraint("ck_messages_assistant_parent", "messages", type_="check")
    op.drop_constraint("fk_messages_parent_message_id", "messages", type_="foreignkey")
    op.drop_column("messages", "raw_response")
    op.drop_column("messages", "raw_request")
    op.drop_column("messages", "langfuse_trace_id")
    op.drop_column("messages", "latency_ms")
    op.drop_column("messages", "cost_currency")
    op.drop_column("messages", "cost")
    op.drop_column("messages", "completion_tokens")
    op.drop_column("messages", "prompt_tokens")
    op.drop_column("messages", "model_name")
    op.drop_column("messages", "variant_index")
    op.drop_column("messages", "parent_message_id")

    op.drop_index("idx_chats_user", table_name="chats")
    op.create_index("ix_chats_user_id", "chats", ["user_id"])
    op.drop_column("chats", "updated_at")
    op.drop_column("chats", "last_message_at")
    op.drop_column("chats", "is_archived")
    op.alter_column(
        "chats",
        "title",
        existing_type=sa.String(length=500),
        type_=sa.String(length=255),
        existing_nullable=True,
    )

    op.drop_index("idx_doc_index_model", table_name="document_index_status")
    op.drop_index("uq_doc_index_current", table_name="document_index_status")
    op.drop_table("document_index_status")

    op.drop_index("idx_chunks_content_hash", table_name="document_chunks")
    op.drop_constraint("uq_chunks_document_index", "document_chunks", type_="unique")
    op.drop_constraint("uq_document_chunks_qdrant_point_id", "document_chunks", type_="unique")
    op.drop_column("document_chunks", "metadata")
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "qdrant_point_id")
    op.drop_column("document_chunks", "char_end")
    op.drop_column("document_chunks", "char_start")
    op.drop_column("document_chunks", "section_number")
    op.drop_column("document_chunks", "section_title")
    op.drop_column("document_chunks", "page_number")
    op.drop_column("document_chunks", "token_count")
    op.drop_column("document_chunks", "content_hash")

    op.drop_index("idx_documents_metadata", table_name="documents")
    op.drop_index("idx_documents_doc_date", table_name="documents")
    op.drop_column("documents", "metadata")
    op.drop_column("documents", "language")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "page_count")
    op.drop_column("documents", "description")
    op.drop_column("documents", "official_url")
    op.drop_column("documents", "jurisdiction")
    op.drop_column("documents", "doc_date")
    op.drop_column("documents", "doc_number")
    op.drop_column("documents", "doc_type")
    op.create_unique_constraint("documents_storage_key_key", "documents", ["storage_key"])
    op.alter_column(
        "documents",
        "storage_key",
        existing_type=sa.Text(),
        type_=sa.String(length=1024),
        existing_nullable=False,
    )
    op.execute("ALTER TABLE documents RENAME COLUMN mime_type TO content_type")
    op.alter_column("documents", "content_type", nullable=True)
    op.alter_column(
        "documents",
        "filename",
        existing_type=sa.String(length=500),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
    op.drop_constraint("uq_documents_file_hash", "documents", type_="unique")
    op.drop_column("documents", "size_bytes")
    op.drop_column("documents", "file_hash")
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])

    op.drop_column("users", "updated_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "email_verified_at")
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN email TYPE VARCHAR(255)
        USING email::text
        """
    )
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column("users", "last_name", existing_type=sa.String(length=100), nullable=True)
