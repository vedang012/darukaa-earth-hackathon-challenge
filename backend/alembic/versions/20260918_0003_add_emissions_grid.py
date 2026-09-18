"""add EDGAR emissions grid

Revision ID: 20260918_0003
Revises: 20260918_0002
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op
import geoalchemy2
import sqlalchemy as sa


revision: str = "20260918_0003"
down_revision: str | Sequence[str] | None = "20260918_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emissions_grid",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("lon_center", sa.Numeric(precision=8, scale=5), nullable=False),
        sa.Column("lat_center", sa.Numeric(precision=7, scale=5), nullable=False),
        sa.Column("co2_tonnes", sa.Double(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POLYGON", srid=4326, spatial_index=False
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "year",
            "lon_center",
            "lat_center",
            name="uq_emissions_grid_year_lon_lat",
        ),
    )
    op.create_index("ix_emissions_grid_year", "emissions_grid", ["year"], unique=False)
    op.create_index(
        "emissions_grid_geometry_idx",
        "emissions_grid",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("emissions_grid_geometry_idx", table_name="emissions_grid")
    op.drop_index("ix_emissions_grid_year", table_name="emissions_grid")
    op.drop_table("emissions_grid")
