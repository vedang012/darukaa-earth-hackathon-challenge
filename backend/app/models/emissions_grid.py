from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Double,
    Numeric,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmissionsGrid(Base):
    __tablename__ = "emissions_grid"
    __table_args__ = (
        UniqueConstraint(
            "year",
            "lon_center",
            "lat_center",
            name="uq_emissions_grid_year_lon_lat",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    lon_center: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    lat_center: Mapped[Decimal] = mapped_column(Numeric(7, 5), nullable=False)
    co2_tonnes: Mapped[float] = mapped_column(Double, nullable=False)
    geometry = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )
