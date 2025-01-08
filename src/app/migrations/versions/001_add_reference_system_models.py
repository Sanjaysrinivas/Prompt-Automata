"""Add reference system models

Revision ID: 001
Revises:
Create Date: 2024-01-09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create persistent_variables table
    op.create_table(
        "persistent_variables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create allowed_directories table
    op.create_table(
        "allowed_directories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path"),
    )

    # Create api_endpoints table
    op.create_table(
        "api_endpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create fence_references table
    op.create_table(
        "fence_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fence_id", sa.Integer(), nullable=False),
        sa.Column("reference_type", sa.String(length=50), nullable=False),
        sa.Column("reference_value", sa.String(length=1024), nullable=False),
        sa.Column("resolved_value", sa.Text(), nullable=True),
        sa.Column("last_resolved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["fence_id"], ["fences.id"], ondelete="CASCADE"),
    )

    # Add indices for better query performance
    op.create_index("idx_persistent_variables_name", "persistent_variables", ["name"])
    op.create_index("idx_allowed_directories_path", "allowed_directories", ["path"])
    op.create_index("idx_api_endpoints_name", "api_endpoints", ["name"])
    op.create_index("idx_fence_references_fence_id", "fence_references", ["fence_id"])
    op.create_index("idx_fence_references_type", "fence_references", ["reference_type"])


def downgrade():
    # Drop indices
    op.drop_index("idx_fence_references_type")
    op.drop_index("idx_fence_references_fence_id")
    op.drop_index("idx_api_endpoints_name")
    op.drop_index("idx_allowed_directories_path")
    op.drop_index("idx_persistent_variables_name")

    # Drop tables
    op.drop_table("fence_references")
    op.drop_table("api_endpoints")
    op.drop_table("allowed_directories")
    op.drop_table("persistent_variables")
