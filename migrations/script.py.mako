"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# リビジョン識別子は Alembic で利用される
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """スキーマをアップグレードする。"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """スキーマをダウングレードする。"""
    ${downgrades if downgrades else "pass"}
