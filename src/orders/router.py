from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import User
from src.auth.security import get_current_user
from src.cart.models import CartItem
from src.database import get_db
from src.orders.models import Order, OrderItem
from src.orders.schemas import OrderRead
from src.products.models import Product

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/checkout", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def checkout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Load the cart, joined with product info
    result = await db.execute(
        select(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .where(CartItem.user_id == current_user.id)
        .order_by(CartItem.id)
    )
    cart_rows = result.all()

    if not cart_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty"
        )

    # 2. Turn the cart into an order — all inside ONE transaction
    order = Order(user_id=current_user.id, total=Decimal("0"))
    for cart_item, product in cart_rows:
        if cart_item.quantity > product.stock:
            # Raised mid-transaction → everything already changed
            # above gets rolled back. The test below proves it.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Not enough stock for '{product.name}': only {product.stock} left",
            )
        order.items.append(
            OrderItem(
                product_id=product.id,
                name=product.name,    # frozen forever
                price=product.price,  # frozen forever
                quantity=cart_item.quantity,
            )
        )
        order.total += product.price * cart_item.quantity
        product.stock -= cart_item.quantity  # take items off the shelf

    # 3. Empty the cart
    await db.execute(delete(CartItem).where(CartItem.user_id == current_user.id))

    # 4. ONE commit: order + items + stock + empty cart — all together or not at all
    db.add(order)
    await db.commit()
    await db.refresh(order, attribute_names=["items"])  # load items for the response
    return order


@router.get("", response_model=list[OrderRead])
async def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(selectinload(Order.items))  # load items eagerly — see tip below
        .order_by(Order.id.desc())  # newest first
    )
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(selectinload(Order.items))
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    return order