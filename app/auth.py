from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, Patient, Doctor, Staff
from .schemas import RegisterInput, LoginInput, ChangePasswordInput
from .security import (
    hash_password, verify_password, create_access_token, read_access_token,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def clean_gmail(email: str) -> str:
    email = email.strip().lower()
    if not email.endswith("@gmail.com") or email.count("@") != 1:
        raise HTTPException(400, "Please use a valid Gmail address ending in @gmail.com")
    return email


@router.post("/register")
def register(data: RegisterInput, db: Session = Depends(get_db)):
    email = clean_gmail(data.email)
    role = data.account_type.strip().lower()

    if role not in ("patient", "doctor", "staff"):
        raise HTTPException(400, "Admin accounts are created only by the system setup.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "This Gmail address already has an account.")

    if role == "patient":
        if data.age is None:
            raise HTTPException(400, "Age is required for patient registration.")

        invited = db.query(Patient).filter(Patient.email == email).first()
        if not invited and (
            db.query(Doctor).filter(Doctor.email == email).first()
            or db.query(Staff).filter(Staff.email == email).first()
        ):
            raise HTTPException(409, "This Gmail address is reserved for a hospital employee account.")
        if invited:
            if invited.user_id is not None:
                raise HTTPException(409, "This patient profile is already linked to an account.")
            if not data.patient_code or data.patient_code.strip() != invited.registration_code:
                raise HTTPException(403, "Enter the patient registration code provided by the hospital.")
            if invited.full_name.strip().casefold() != data.full_name.strip().casefold():
                raise HTTPException(403, "Your name does not match the patient profile created by the hospital.")
            invited.full_name = data.full_name.strip()
            invited.age = data.age
        user = User(email=email, password_hash=hash_password(data.password), role="patient")
        db.add(user)
        db.flush()
        if invited:
            invited.user_id = user.id
        else:
            db.add(Patient(
                user_id=user.id,
                full_name=data.full_name.strip(),
                email=email,
                age=data.age,
            ))
        db.commit()
        return {"message": "Patient account created. You can now sign in."}

    if not data.employee_code:
        raise HTTPException(400, "Your hospital employee code is required.")

    if db.query(Patient).filter(Patient.email == email).first():
        raise HTTPException(409, "This Gmail address is linked to a patient profile.")
    if role == "doctor" and db.query(Staff).filter(Staff.email == email).first():
        raise HTTPException(409, "This Gmail address is reserved for a staff profile.")
    if role == "staff" and db.query(Doctor).filter(Doctor.email == email).first():
        raise HTTPException(409, "This Gmail address is reserved for a doctor profile.")

    if role == "doctor":
        employee = db.query(Doctor).filter(
            Doctor.email == email,
            Doctor.employee_code == data.employee_code.strip(),
        ).first()
    else:
        employee = db.query(Staff).filter(
            Staff.email == email,
            Staff.employee_code == data.employee_code.strip(),
        ).first()

    if not employee:
        raise HTTPException(403, "No matching hospital invitation was found. Contact the administrator.")
    if employee.user_id is not None:
        raise HTTPException(409, "This employee profile is already activated.")
    if employee.full_name.strip().casefold() != data.full_name.strip().casefold():
        raise HTTPException(403, "Your name does not match the employee record created by the administrator.")

    user = User(email=email, password_hash=hash_password(data.password), role=role)
    db.add(user)
    db.flush()
    employee.user_id = user.id
    db.commit()
    return {"message": f"{role.title()} account activated. You can now sign in."}


@router.post("/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    email = clean_gmail(data.email)
    selected_role = data.role.strip().lower()
    if selected_role not in ("admin", "doctor", "staff", "patient"):
        raise HTTPException(400, "Choose a valid account type.")

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Incorrect Gmail address or password.")
    if not user.is_active:
        raise HTTPException(403, "This account has been disabled. Contact the administrator.")
    if user.role != selected_role:
        raise HTTPException(403, f"This Gmail address is registered as {user.role.title()}, not {selected_role.title()}.")

    return {
        "access_token": create_access_token(user.id, user.role),
        "token_type": "bearer",
        "role": user.role,
        "email": user.email,
    }


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    payload = read_access_token(token)
    if not payload:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "Account not found or inactive.")
    return user


def require_roles(*roles):
    def check_role(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Your account does not have permission for this action.")
        return user
    return check_role


def linked_doctor(db: Session, user: User):
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(403, "Your doctor profile is not linked. Contact the administrator.")
    return doctor


def linked_staff(db: Session, user: User):
    employee = db.query(Staff).filter(Staff.user_id == user.id).first()
    if not employee:
        raise HTTPException(403, "Your staff profile is not linked. Contact the administrator.")
    return employee


@router.get("/me")
def my_account(user=Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/change-password")
def change_password(
    data: ChangePasswordInput,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Your current password is incorrect.")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated successfully."}
