from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=10, max_length=128)
