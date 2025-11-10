"""store documents binary

Revision ID: 6d3b5d7f0df1
Revises: d21b10427c73
Create Date: 2025-11-10 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6d3b5d7f0df1"
down_revision = "d21b10427c73"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("document")
    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_mimetype", sa.String(length=255), nullable=False),
        sa.Column("file_data", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("document")
    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=300), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
