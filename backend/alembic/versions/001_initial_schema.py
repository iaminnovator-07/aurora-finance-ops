"""Initial schema — all Aurora TIA tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables created via Base.metadata.create_all in seed for hackathon speed.
    # This migration is a placeholder for production Alembic workflow.
    pass


def downgrade() -> None:
    pass
