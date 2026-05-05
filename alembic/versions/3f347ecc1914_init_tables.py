"""init tables

Revision ID: 3f347ecc1914
Revises: 67f6b2e77bb3
Create Date: 2026-03-31 15:01:47.744961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3f347ecc1914'
down_revision: Union[str, Sequence[str], None] = '67f6b2e77bb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

   
    op.drop_table('availability_slots')
    op.drop_table('guide_ratings')
    op.drop_table('branches')
    op.drop_table('colleges')
    op.drop_table('countries')


def downgrade() -> None:

    # countries first create cheyyali (parent table)
    op.create_table(
        'countries',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('countries_pkey')),
        sa.UniqueConstraint('name', name=op.f('countries_name_key'))
    )

    # next colleges (depends on countries)
    op.create_table(
        'colleges',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), nullable=True),
        sa.Column('country_id', sa.INTEGER(), nullable=True),
        sa.ForeignKeyConstraint(
            ['country_id'],
            ['countries.id'],
            name=op.f('colleges_country_id_fkey')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('colleges_pkey')),
        sa.UniqueConstraint('name', name=op.f('colleges_name_key'))
    )

    # next branches (depends on colleges)
    op.create_table(
        'branches',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), nullable=True),
        sa.Column('college_id', sa.INTEGER(), nullable=True),
        sa.ForeignKeyConstraint(
            ['college_id'],
            ['colleges.id'],
            name=op.f('branches_college_id_fkey')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('branches_pkey'))
    )

    # remaining independent tables
    op.create_table(
        'guide_ratings',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('booking_id', sa.INTEGER(), nullable=True),
        sa.Column('guide_id', sa.INTEGER(), nullable=True),
        sa.Column('rating', sa.INTEGER(), nullable=True),
        sa.Column('total_calls', sa.INTEGER(), nullable=True),
        sa.Column('wallet_balance', sa.INTEGER(), nullable=True),
        sa.Column('total_earned', sa.INTEGER(), nullable=True),
        sa.Column('honesty', sa.VARCHAR(), nullable=False),
        sa.Column('recommend', sa.VARCHAR(), nullable=False),
        sa.Column('comments', sa.VARCHAR(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(
            ['booking_id'], ['bookings.id'],
            name=op.f('guide_ratings_booking_id_fkey')
        ),
        sa.ForeignKeyConstraint(
            ['guide_id'], ['senior_guides.id'],
            name=op.f('guide_ratings_guide_id_fkey')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('guide_ratings_pkey')),
        sa.UniqueConstraint('booking_id', name=op.f('guide_ratings_booking_id_key'))
    )

    op.create_table(
        'availability_slots',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('guide_id', sa.INTEGER(), nullable=True),
        sa.Column('start_time', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('end_time', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('is_booked', sa.BOOLEAN(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(
            ['guide_id'], ['senior_guides.id'],
            name=op.f('availability_slots_guide_id_fkey')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('availability_slots_pkey'))
    )
    # ### end Alembic commands ###
