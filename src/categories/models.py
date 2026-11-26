from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

# The association table: pure many-to-many, no extra columns.
# The two-column primary key means a product-category pair can exist
# exactly ONCE — the database itself refuses duplicates.
product_categories = Table(
    "product_categories",
    Base.metadata,
    Column(
        "product_id",
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # "Product" as a string — SQLAlchemy resolves it later, no import needed
    # (that's how we avoid a circular import: products → categories only)
    products: Mapped[list["Product"]] = relationship(
        secondary=product_categories, back_populates="categories"
    )