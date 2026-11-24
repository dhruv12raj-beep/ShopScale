from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.security import get_current_user
from src.cart.models import CartItem
from src.cart.schemas import CartItemAdd, CartItemRead, CartItemUpdate, CartRead
from src.database import get_db
from src.products.models import Product

router = APIRouter(prefix="/cart", tags=["cart"])


async def get_cart(db: AsyncSession, user_id: int) -> CartRead:
    """Build the full cart: items joined with product info, plus totals."""
    result = await db.execute(
        select(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id)
    )
    items: list[CartItemRead] = []
    total = Decimal("0")
    for cart_item, product in result.all():
        line_total = product.price * cart_item.quantity
        items.append(
            CartItemRead(
                product_id=product.id,
                name=product.name,
                price=product.price,
                quantity=cart_item.quantity,
                line_total=line_total,
            )
        )
        total += line_total
    return CartRead(items=items, total=total)


async def get_cart_item_or_404(
    db: AsyncSession, user_id: int, product_id: int
) -> CartItem:
    cart_item = await db.scalar(
        select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
    )
    if cart_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not in cart"
        )
    return cart_item


def check_stock(product: Product, quantity: int) -> None:
    if quantity > product.stock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough stock: only {product.stock} left",
        )


@router.get("", response_model=CartRead)
async def view_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_cart(db, current_user.id)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    item_in: CartItemAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, item_in.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    cart_item = await db.scalar(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == item_in.product_id,
        )
    )

    if cart_item:
        cart_item.quantity += item_in.quantity  # already in cart → just add more
        check_stock(product, cart_item.quantity)
    else:
        check_stock(product, item_in.quantity)
        db.add(
            CartItem(
                user_id=current_user.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
            )
        )

    await db.commit()
    return await get_cart(db, current_user.id)


@router.patch("/items/{product_id}", response_model=CartRead)
async def update_quantity(
    product_id: int,
    item_in: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart_item = await get_cart_item_or_404(db, current_user.id, product_id)
    product = await db.get(Product, product_id)
    check_stock(product, item_in.quantity)
    cart_item.quantity = item_in.quantity
    await db.commit()
    return await get_cart(db, current_user.id)


@router.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart_item = await get_cart_item_or_404(db, current_user.id, product_id)
    await db.delete(cart_item)
    await db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(CartItem).where(CartItem.user_id == current_user.id))
    await db.commit()