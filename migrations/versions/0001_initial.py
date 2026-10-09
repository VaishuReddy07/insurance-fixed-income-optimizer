"""Create the initial portfolio schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("instruments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("issuer", sa.String(), nullable=False),
        sa.Column("sector", sa.String(), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("maturity_years", sa.Float(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("spread_duration", sa.Float(), nullable=False),
        sa.Column("yield_pct", sa.Float(), nullable=False),
        sa.Column("spread_bps", sa.Float(), nullable=False),
        sa.Column("liquidity_score", sa.Float(), nullable=False),
        sa.Column("esg_score", sa.Float(), nullable=False),
        sa.Column("capital_factor", sa.Float(), nullable=False),
    )
    op.create_index("ix_instruments_issuer", "instruments", ["issuer"])
    op.create_index("ix_instruments_rating", "instruments", ["rating"])
    op.create_table("optimization_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("objective", sa.Float(), nullable=False),
        sa.Column("expected_yield_pct", sa.Float(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
    )
    op.create_table("price_points",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("instrument_id", sa.String(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("total_return", sa.Float(), nullable=False),
    )
    op.create_index("ix_price_points_instrument_id", "price_points", ["instrument_id"])
    op.create_index("ix_price_points_date", "price_points", ["date"])

def downgrade():
    op.drop_index("ix_price_points_date", table_name="price_points")
    op.drop_index("ix_price_points_instrument_id", table_name="price_points")
    op.drop_table("price_points")
    op.drop_table("optimization_runs")
    op.drop_index("ix_instruments_rating", table_name="instruments")
    op.drop_index("ix_instruments_issuer", table_name="instruments")
    op.drop_table("instruments")
