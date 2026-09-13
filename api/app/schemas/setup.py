from pydantic import BaseModel, EmailStr


class SetupRequest(BaseModel):
    # Empresa
    company_name: str
    company_email: EmailStr
    # Superadmin
    full_name: str
    email: EmailStr
    password: str


class SetupResponse(BaseModel):
    message: str
    company_id: int
    user_id: int
    access_token: str
    token_type: str = "bearer"
