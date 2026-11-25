from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select 
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.products.models import Product
from src.products.schemas import ProductCreate, ProductRead, ProductUpdate
from sqlalchemy import func, select
from src.products.schemas import ProductList
from src.auth.models import User
from src.auth.security import require_admin
from decimal import Decimal


router = APIRouter(prefix="/products", tags=["products"])


async def get_product_or_404(product_id: int, db: AsyncSession) -> Product:
    """Fetch a product by id, or raise a clean 404 if it doesn't exist."""
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.get("", response_model=ProductList)
async def list_products(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Build a list of filters — empty at first, add only what the client sent
    conditions = []
    if search:
        conditions.append(Product.name.ilike(f"%{search}%"))  # case-insensitive
    if min_price is not None:
        conditions.append(Product.price >= min_price)
    if max_price is not None:
        conditions.append(Product.price <= max_price)

    # Count must use the SAME filters — otherwise "total" lies to the frontend
    count_query = select(func.count()).select_from(Product)
    query = select(Product).order_by(Product.id)
    if conditions:
        count_query = count_query.where(*conditions)
        query = query.where(*conditions)

    total = await db.scalar(count_query)
    result = await db.execute(query.limit(limit).offset(offset))

    return {
        "items": result.scalars().all(),
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    return await get_product_or_404(product_id, db)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(product_in: ProductCreate, admin: User = Depends(require_admin),  db: AsyncSession = Depends(get_db)):
    product = Product(**product_in.model_dump())
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
    product = await get_product_or_404(product_id, db)
    # exclude_unset=True → only apply fields the client actually sent
    for field, value in product_in.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int,admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    product = await get_product_or_404(product_id, db)
    await db.delete(product)
    await db.commit()