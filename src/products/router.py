from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import User
from src.auth.security import require_admin
from src.categories.models import Category, product_categories
from src.database import get_db
from src.products.models import Product
from src.products.schemas import ProductCreate, ProductList, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


async def get_categories_or_404(
    db: AsyncSession, category_ids: list[int]
) -> list[Category]:
    """Turn a list of ids into real Category objects — or 404 if any is unknown."""
    if not category_ids:
        return []
    result = await db.execute(select(Category).where(Category.id.in_(category_ids)))
    categories = result.scalars().all()
    if len(categories) != len(set(category_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more categories not found",
        )
    return list(categories)


@router.get("", response_model=ProductList)
async def list_products(
    search: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    category_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if search:
        conditions.append(Product.name.ilike(f"%{search}%"))
    if min_price is not None:
        conditions.append(Product.price >= min_price)
    if max_price is not None:
        conditions.append(Product.price <= max_price)
    if category_id is not None:
        conditions.append(product_categories.c.category_id == category_id)

    count_query = select(func.count()).select_from(Product)
    query = select(Product)
    if conditions:
        count_query = count_query.where(*conditions)
        query = query.where(*conditions)
    if category_id is not None:
        # Join through the association table. Each product appears exactly
        # once — (product_id, category_id) is the primary key there, so the
        # database physically cannot hold a duplicate pair.
        count_query = count_query.join(
            product_categories, product_categories.c.product_id == Product.id
        )
        query = query.join(
            product_categories, product_categories.c.product_id == Product.id
        )

    total = await db.scalar(count_query)
    result = await db.execute(
        query.options(selectinload(Product.categories))
        .order_by(Product.id)
        .limit(limit)
        .offset(offset)
    )
    return ProductList(items=result.scalars().all(), total=total)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    # select instead of db.get — because we need to ask for categories too
    product = await db.scalar(
        select(Product)
        .options(selectinload(Product.categories))
        .where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    product = Product(
        name=product_in.name,
        price=product_in.price,
        stock=product_in.stock,
    )
    # Assigning the collection loads it — refresh() later keeps it loaded
    product.categories = await get_categories_or_404(db, product_in.category_ids)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    product = await db.scalar(
        select(Product)
        .options(selectinload(Product.categories))
        .where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    if product_in.name is not None:
        product.name = product_in.name
    if product_in.price is not None:
        product.price = product_in.price
    if product_in.stock is not None:
        product.stock = product_in.stock
    if product_in.category_ids is not None:
        # Replacement semantics: the list you send IS the new complete list
        product.categories = await get_categories_or_404(db, product_in.category_ids)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    await db.delete(product)
    await db.commit()