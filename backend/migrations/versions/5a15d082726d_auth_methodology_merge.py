"""auth_methodology_merge

Revision ID: 5a15d082726d
Revises: 65dfe61824f7, 7f3c5c2b8a1f
Create Date: 2026-05-04 18:22:58.432686

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '5a15d082726d'
down_revision: str | None = ('65dfe61824f7', '7f3c5c2b8a1f')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
