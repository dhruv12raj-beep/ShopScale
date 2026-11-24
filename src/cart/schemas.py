from decimal import Decimal

from pydantic import BaseModel, Field



class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemRead(BaseModel):
    product_id: int
    name: str
    price: Decimal
    quantity: int
    line_total: Decimal  # price × quantity, for this line


class CartRead(BaseModel):
    items: list[CartItemRead]
    total: Decimal  # the whole cart