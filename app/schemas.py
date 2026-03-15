from datetime import datetime
from pydantic import BaseModel, HttpUrl


class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LinkCreate(BaseModel):
    url: HttpUrl
    custom_alias: str | None = None
    expires_at: datetime | None = None


class LinkUpdate(BaseModel):
    url: HttpUrl


class LinkResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class LinkStats(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    redirect_count: int
    last_used_at: datetime | None = None
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}
