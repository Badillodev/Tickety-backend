from pydantic import BaseModel

class UpdateUserRequest(BaseModel):
    name: str | None = None
    surname: str | None = None
    company: str | None = None
    address: str | None = None
    phone: str | None = None
    is_company: bool | None = None