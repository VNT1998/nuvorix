"""Initial baseline schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-09 12:00:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Baseline migration: tables are automatically initialized and synchronized with Base.metadata
    pass


def downgrade() -> None:
    pass
