"""Create table

Revision ID: 1d91f2df3aa2
Revises:
Create Date: 2023-02-21 14:13:17.492582

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1d91f2df3aa2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_table",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("test_col", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("test_table")
