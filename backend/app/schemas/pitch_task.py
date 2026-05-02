from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class PitchTaskCreate(BaseModel):
    name: str
    customer_name: str | None = None
    customer_industry: str | None = None
    budget: Decimal | None = None
    bid_date: date | None = None
    bid_time_limit: int | None = 30
    bid_requirements: str | None = None
    competitor_info: list | None = None
    member_ids: list[int] | None = None


class PitchTaskUpdate(BaseModel):
    name: str | None = None
    customer_name: str | None = None
    customer_industry: str | None = None
    budget: Decimal | None = None
    bid_date: date | None = None
    bid_time_limit: int | None = None
    bid_requirements: str | None = None
    competitor_info: list | None = None
    result: int | None = None


class PitchTaskResponse(BaseModel):
    id: int
    name: str
    customer_name: str | None
    customer_industry: str | None
    budget: Decimal | None
    bid_date: date | None
    bid_time_limit: int | None
    status: int
    result: int | None
    owner_id: int

    model_config = {"from_attributes": True}
