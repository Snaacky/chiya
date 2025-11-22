"""migrate highlights to one user per row

Revision ID: 7e85e26798a8
Revises:
Create Date: 2025-11-22 06:20:29.660412

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, String, JSON


# revision identifiers, used by Alembic.
revision = "7e85e26798a8"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    ctx = op.get_context()

    with ctx.begin_transaction():
        # add user_id column, user_id is temporary nullable until we're done
        op.add_column("highlights", sa.Column("user_id", sa.Integer(), nullable=True))

        # skeleton table for ease-of-access
        highlights = table(
            "highlights",
            column("id", Integer),
            column("term", String),
            column("users", JSON),
            column("user_id", Integer),
        )

        # grab a handle to the database connection
        conn = op.get_bind()

        # fetch all rows
        rows = conn.execute(sa.select(highlights)).all()

        # insert new rows with one user id per term
        for row in rows:
            for uid in row.users:
                conn.execute(sa.insert(highlights).values(term=row.term, user_id=uid))

        # delete all the old rows now with the old data structure
        conn.execute(sa.delete(highlights).where(highlights.c.users.isnot(None)))

        # delete the legacy users column
        with op.batch_alter_table("highlights") as batch_op:
            batch_op.drop_column("users")

        # make user_id no longer nullable
        with op.batch_alter_table("highlights") as batch_op:
            batch_op.alter_column(
                "user_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
