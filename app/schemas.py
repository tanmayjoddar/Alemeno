from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobCreate(BaseModel):
    pass


class JobResponse(BaseModel):
    id: int
    filename: str
    status: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    summary: Optional[dict] = None

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: int
    txn_id: Optional[str]
    date: str
    merchant: str
    amount: float
    currency: str
    status: str
    category: str
    account_id: str
    is_anomaly: bool
    anomaly_reason: Optional[str]
    llm_category: Optional[str]

    class Config:
        from_attributes = True


class CategoryBreakdown(BaseModel):
    category: str
    count: int
    total: float


class JobResultResponse(BaseModel):
    job_id: int
    status: str
    transactions: list[TransactionResponse]
    anomalies: list[TransactionResponse]
    category_breakdown: list[CategoryBreakdown]
    summary: Optional[dict] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    id: int
    filename: str
    status: str
    row_count_raw: int
    created_at: datetime

    class Config:
        from_attributes = True
