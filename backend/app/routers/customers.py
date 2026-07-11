from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.schemas import CustomerCreate, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
async def list_customers(session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(select(models.Customer).order_by(models.Customer.id.desc()))
    return list(rows)


@router.post("", response_model=CustomerOut, status_code=201)
async def create_customer(body: CustomerCreate, session: AsyncSession = Depends(get_session)):
    customer = models.Customer(name=body.name, external_id=body.external_id, note=body.note)
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer
