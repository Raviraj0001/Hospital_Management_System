from datetime import datetime
from pydantic import BaseModel, Field


class RegisterInput(BaseModel):
    account_type: str = "patient"
    full_name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=100)
    age: int | None = Field(default=None, ge=0, le=120)
    employee_code: str | None = None
    patient_code: str | None = None


class LoginInput(BaseModel):
    email: str
    password: str
    role: str


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)


class DoctorInvite(BaseModel):
    full_name: str
    email: str
    employee_code: str
    specialization: str
    phone: str = ""
    consultation_fee: float = Field(ge=0)


class StaffInvite(BaseModel):
    full_name: str
    email: str
    employee_code: str
    job_title: str
    phone: str = ""


class PatientInvite(BaseModel):
    full_name: str
    email: str
    registration_code: str
    age: int = Field(ge=0, le=120)
    gender: str = "Not specified"
    phone: str = ""
    address: str = ""


class AppointmentInput(BaseModel):
    doctor_id: int
    appointment_at: datetime
    patient_id: int | None = None


class AppointmentStatusInput(BaseModel):
    status: str


class RecordInput(BaseModel):
    patient_id: int
    appointment_id: int | None = None
    diagnosis: str
    treatment: str
    medicines: str = ""
    notes: str = ""


class BillInput(BaseModel):
    patient_id: int
    description: str
    amount: float = Field(gt=0)


class BedInput(BaseModel):
    bed_number: str
    ward: str


class BedRequestInput(BaseModel):
    reason: str = ""


class BedAssignmentInput(BaseModel):
    bed_id: int


class FacilityInput(BaseModel):
    name: str
    description: str = ""
    is_available: bool = False


class FacilityStatusInput(BaseModel):
    is_available: bool


class AccountStatusInput(BaseModel):
    is_active: bool
