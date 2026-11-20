from datetime import date, datetime, time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    User, Patient, Doctor, Staff, Bed, BedRequest, Admission,
    Facility, Attendance, Bill, Appointment,
)
from .schemas import (
    DoctorInvite, StaffInvite, PatientInvite, BedInput, BedRequestInput,
    BedAssignmentInput, FacilityInput, FacilityStatusInput, BillInput, AccountStatusInput,
)
from .auth import get_current_user, require_roles, linked_doctor, linked_staff
from .security import hash_password

router = APIRouter(tags=["Hospital management"])


def check_gmail(email: str) -> str:
    email = email.strip().lower()
    if not email.endswith("@gmail.com") or email.count("@") != 1:
        raise HTTPException(400, "Use a Gmail address ending in @gmail.com.")
    return email


def patient_for_user(db: Session, user: User):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise HTTPException(404, "Patient profile not found.")
    return patient


@router.get("/api/doctors")
def public_doctor_directory(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    doctors = db.query(Doctor).order_by(Doctor.full_name).all()
    return [{
        "id": doctor.id,
        "full_name": doctor.full_name,
        "specialization": doctor.specialization,
        "consultation_fee": doctor.consultation_fee,
        "is_available": doctor.is_available,
    } for doctor in doctors]


@router.get("/api/doctors/me")
def doctor_profile(
    db: Session = Depends(get_db),
    user=Depends(require_roles("doctor")),
):
    doctor = linked_doctor(db, user)
    return {
        "id": doctor.id,
        "full_name": doctor.full_name,
        "employee_code": doctor.employee_code,
        "specialization": doctor.specialization,
        "is_available": doctor.is_available,
    }


@router.patch("/api/doctors/me/availability")
def change_own_availability(
    is_available: bool,
    db: Session = Depends(get_db),
    user=Depends(require_roles("doctor")),
):
    doctor = linked_doctor(db, user)
    doctor.is_available = is_available
    db.commit()
    return {"message": "Availability updated.", "is_available": doctor.is_available}


@router.get("/api/patients/me")
def patient_profile(
    db: Session = Depends(get_db),
    user=Depends(require_roles("patient")),
):
    patient = patient_for_user(db, user)
    return {
        "id": patient.id,
        "full_name": patient.full_name,
        "email": patient.email or user.email,
        "age": patient.age,
        "gender": patient.gender,
        "phone": patient.phone,
    }


@router.get("/api/public/hospital")
def public_hospital_information(db: Session = Depends(get_db)):
    total_beds = db.query(Bed).count()
    available_beds = db.query(Bed).filter(Bed.is_occupied.is_(False)).count()
    facilities = db.query(Facility).filter(Facility.is_available.is_(True)).order_by(Facility.name).all()
    return {
        "hospital_name": "Hospital Portal",
        "total_beds": total_beds,
        "available_beds": available_beds,
        "facilities": [{
            "id": item.id,
            "name": item.name,
            "description": item.description,
        } for item in facilities],
    }


@router.get("/api/admin/summary")
def admin_summary(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    return {
        "patients": db.query(Patient).count(),
        "doctors": db.query(Doctor).count(),
        "active_doctors": db.query(Doctor).filter(Doctor.is_available.is_(True)).count(),
        "staff": db.query(Staff).count(),
        "appointments": db.query(Appointment).count(),
        "available_beds": db.query(Bed).filter(Bed.is_occupied.is_(False)).count(),
        "total_beds": db.query(Bed).count(),
        "pending_bed_requests": db.query(BedRequest).filter(BedRequest.status == "Pending").count(),
    }


@router.post("/api/admin/doctors")
def add_doctor(
    data: DoctorInvite,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    email = check_gmail(data.email)
    if (
        db.query(User).filter(User.email == email).first()
        or db.query(Patient).filter(Patient.email == email).first()
        or db.query(Staff).filter((Staff.email == email) | (Staff.employee_code == data.employee_code.strip())).first()
    ):
        raise HTTPException(409, "This Gmail address or employee code is already assigned.")
    if db.query(Doctor).filter(
        (Doctor.email == email) | (Doctor.employee_code == data.employee_code.strip())
    ).first():
        raise HTTPException(409, "A doctor with this Gmail address or employee code already exists.")
    doctor = Doctor(
        full_name=data.full_name.strip(),
        email=email,
        employee_code=data.employee_code.strip(),
        specialization=data.specialization.strip(),
        phone=data.phone.strip(),
        consultation_fee=data.consultation_fee,
        is_available=False,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return {"message": "Doctor invitation created. The doctor can now activate their account.", "doctor_id": doctor.id}


@router.get("/api/admin/doctors")
def admin_doctors(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    return [{
        "id": d.id, "full_name": d.full_name, "email": d.email,
        "employee_code": d.employee_code, "specialization": d.specialization,
        "is_available": d.is_available, "activated": d.user_id is not None, "user_id": d.user_id,
        "account_active": db.get(User, d.user_id).is_active if d.user_id else False,
    } for d in db.query(Doctor).order_by(Doctor.full_name).all()]


@router.patch("/api/admin/doctors/{doctor_id}/availability")
def admin_doctor_availability(
    doctor_id: int,
    is_available: bool,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(404, "Doctor not found.")
    doctor.is_available = is_available
    db.commit()
    return {"message": "Doctor availability updated."}


@router.post("/api/admin/staff")
def add_staff(
    data: StaffInvite,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    email = check_gmail(data.email)
    if (
        db.query(User).filter(User.email == email).first()
        or db.query(Patient).filter(Patient.email == email).first()
        or db.query(Doctor).filter((Doctor.email == email) | (Doctor.employee_code == data.employee_code.strip())).first()
    ):
        raise HTTPException(409, "This Gmail address or employee code is already assigned.")
    if db.query(Staff).filter(
        (Staff.email == email) | (Staff.employee_code == data.employee_code.strip())
    ).first():
        raise HTTPException(409, "A staff member with this Gmail address or employee code already exists.")
    employee = Staff(
        full_name=data.full_name.strip(),
        email=email,
        employee_code=data.employee_code.strip(),
        job_title=data.job_title.strip(),
        phone=data.phone.strip(),
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return {"message": "Staff invitation created. The employee can now activate their account.", "staff_id": employee.id}


@router.get("/api/admin/staff")
def admin_staff(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    return [{
        "id": s.id, "full_name": s.full_name, "email": s.email,
        "employee_code": s.employee_code, "job_title": s.job_title,
        "activated": s.user_id is not None, "user_id": s.user_id,
        "account_active": db.get(User, s.user_id).is_active if s.user_id else False,
    } for s in db.query(Staff).order_by(Staff.full_name).all()]


@router.post("/api/admin/patients")
def add_patient(
    data: PatientInvite,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    email = check_gmail(data.email)
    if (
        db.query(User).filter(User.email == email).first()
        or db.query(Doctor).filter(Doctor.email == email).first()
        or db.query(Staff).filter(Staff.email == email).first()
    ):
        raise HTTPException(409, "This Gmail address is already assigned to another account.")
    if db.query(Patient).filter(
        (Patient.email == email) | (Patient.registration_code == data.registration_code.strip())
    ).first():
        raise HTTPException(409, "A patient with this Gmail address or registration code already exists.")
    patient = Patient(
        full_name=data.full_name.strip(),
        email=email,
        registration_code=data.registration_code.strip(),
        age=data.age,
        gender=data.gender,
        phone=data.phone.strip(),
        address=data.address.strip(),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {"message": "Patient record created. Share the registration code with the patient.", "patient_id": patient.id}


@router.get("/api/admin/patients")
def admin_patients(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "staff")),
):
    return [{
        "id": p.id, "full_name": p.full_name, "email": p.email or "",
        "age": p.age, "phone": p.phone, "registered": p.user_id is not None, "user_id": p.user_id,
        "account_active": db.get(User, p.user_id).is_active if p.user_id else False,
    } for p in db.query(Patient).order_by(Patient.full_name).all()]


@router.post("/api/admin/facilities")
def add_facility(
    data: FacilityInput,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Facility name is required.")
    if db.query(Facility).filter(Facility.name == name).first():
        raise HTTPException(409, "This facility already exists.")
    facility = Facility(name=name, description=data.description.strip(), is_available=data.is_available)
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return {"message": "Facility saved.", "facility_id": facility.id}


@router.get("/api/admin/facilities")
def admin_facilities(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    return db.query(Facility).order_by(Facility.name).all()


@router.patch("/api/admin/facilities/{facility_id}")
def update_facility(
    facility_id: int,
    data: FacilityStatusInput,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    facility = db.get(Facility, facility_id)
    if not facility:
        raise HTTPException(404, "Facility not found.")
    facility.is_available = data.is_available
    db.commit()
    return {"message": "Facility status updated."}


@router.post("/api/admin/beds")
def add_bed(
    data: BedInput,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    if db.query(Bed).filter(Bed.bed_number == data.bed_number.strip()).first():
        raise HTTPException(409, "That bed number already exists.")
    bed = Bed(bed_number=data.bed_number.strip(), ward=data.ward.strip())
    db.add(bed)
    db.commit()
    db.refresh(bed)
    return {"message": "Bed added to inventory.", "bed_id": bed.id}


@router.get("/api/managed/beds")
def managed_beds(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "staff")),
):
    return [{
        "id": b.id, "bed_number": b.bed_number, "ward": b.ward,
        "is_occupied": b.is_occupied,
    } for b in db.query(Bed).order_by(Bed.ward, Bed.bed_number).all()]


@router.post("/api/bed-requests")
def request_bed(
    data: BedRequestInput,
    db: Session = Depends(get_db),
    user=Depends(require_roles("patient")),
):
    patient = patient_for_user(db, user)
    available = db.query(Bed).filter(Bed.is_occupied.is_(False)).count()
    if available < 1:
        raise HTTPException(409, "There are currently no available beds. Please contact hospital staff.")
    pending = db.query(BedRequest).filter(
        BedRequest.patient_id == patient.id,
        BedRequest.status == "Pending",
    ).first()
    if pending:
        raise HTTPException(409, "You already have a pending bed request.")
    request = BedRequest(patient_id=patient.id, reason=data.reason.strip())
    db.add(request)
    db.commit()
    db.refresh(request)
    return {"message": "Bed request sent to hospital staff. A bed is not confirmed until staff assigns one.", "request_id": request.id}


@router.get("/api/bed-requests")
def list_bed_requests(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(BedRequest).join(Patient)
    if user.role == "patient":
        patient = patient_for_user(db, user)
        query = query.filter(BedRequest.patient_id == patient.id)
    elif user.role not in ("admin", "staff"):
        raise HTTPException(403, "Your account cannot view bed requests.")
    rows = query.order_by(BedRequest.requested_at.desc()).all()
    return [{
        "id": row.id, "patient_id": row.patient_id,
        "patient_name": row.patient.full_name,
        "reason": row.reason, "status": row.status,
        "requested_at": row.requested_at,
    } for row in rows]


@router.post("/api/bed-requests/{request_id}/assign")
def assign_bed(
    request_id: int,
    data: BedAssignmentInput,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "staff")),
):
    request = db.get(BedRequest, request_id)
    if not request or request.status != "Pending":
        raise HTTPException(404, "Pending bed request not found.")
    bed = db.get(Bed, data.bed_id)
    if not bed:
        raise HTTPException(404, "Bed not found.")
    if bed.is_occupied:
        raise HTTPException(409, "That bed is already occupied.")
    bed.is_occupied = True
    request.status = "Approved"
    admission = Admission(
        patient_id=request.patient_id,
        bed_id=bed.id,
        bed_request_id=request.id,
    )
    db.add(admission)
    db.commit()
    return {"message": f"Bed {bed.bed_number} assigned to {request.patient.full_name}."}


@router.post("/api/admissions/{admission_id}/discharge")
def discharge_patient(
    admission_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "staff")),
):
    admission = db.get(Admission, admission_id)
    if not admission or admission.discharged_at is not None:
        raise HTTPException(404, "Active admission not found.")
    admission.discharged_at = datetime.utcnow()
    admission.bed.is_occupied = False
    db.commit()
    return {"message": "Patient discharged and bed released."}


@router.post("/api/attendance/me")
def mark_attendance(
    db: Session = Depends(get_db),
    user=Depends(require_roles("doctor", "staff")),
):
    today = date.today()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)

    if user.role == "doctor":
        employee = linked_doctor(db, user)
        existing = db.query(Attendance).filter(
            Attendance.doctor_id == employee.id,
            Attendance.attendance_date >= start,
            Attendance.attendance_date <= end,
        ).first()
        if existing:
            raise HTTPException(409, "You have already marked attendance today.")
        entry = Attendance(doctor_id=employee.id, status="Present")
    else:
        employee = linked_staff(db, user)
        existing = db.query(Attendance).filter(
            Attendance.staff_id == employee.id,
            Attendance.attendance_date >= start,
            Attendance.attendance_date <= end,
        ).first()
        if existing:
            raise HTTPException(409, "You have already marked attendance today.")
        entry = Attendance(staff_id=employee.id, status="Present")

    db.add(entry)
    db.commit()
    return {"message": "Attendance marked successfully."}


@router.get("/api/admin/attendance")
def attendance_report(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    rows = db.query(Attendance).order_by(Attendance.attendance_date.desc()).all()
    result = []
    for row in rows:
        employee = row.doctor or row.staff
        result.append({
            "id": row.id,
            "employee": employee.full_name if employee else "Unknown",
            "employee_type": "Doctor" if row.doctor_id else "Staff",
            "date": row.attendance_date,
            "status": row.status,
        })
    return result


@router.get("/api/billing")
def list_bills(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.role == "patient":
        patient = patient_for_user(db, user)
        rows = db.query(Bill).filter(Bill.patient_id == patient.id).all()
    elif user.role in ("admin", "staff"):
        rows = db.query(Bill).all()
    else:
        raise HTTPException(403, "Your account cannot view billing information.")
    return [{
        "id": bill.id, "patient_id": bill.patient_id,
        "description": bill.description, "amount": bill.amount,
        "status": bill.status, "created_at": bill.created_at,
    } for bill in rows]


@router.post("/api/billing")
def create_bill(
    data: BillInput,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "staff")),
):
    if not db.get(Patient, data.patient_id):
        raise HTTPException(404, "Patient not found.")
    bill = Bill(
        patient_id=data.patient_id,
        description=data.description.strip(),
        amount=data.amount,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return {"message": "Bill created.", "bill_id": bill.id}


@router.patch("/api/billing/{bill_id}/paid")
def mark_bill_paid(
    bill_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "staff")),
):
    bill = db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(404, "Bill not found.")
    bill.status = "Paid"
    db.commit()
    return {"message": "Bill marked as paid."}


@router.patch("/api/admin/accounts/{user_id}/status")
def update_account_status(
    user_id: int,
    data: AccountStatusInput,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    account = db.get(User, user_id)
    if not account:
        raise HTTPException(404, "Account not found.")
    if account.id == user.id:
        raise HTTPException(400, "You cannot deactivate the account you are currently using.")
    if account.role == "admin":
        raise HTTPException(403, "The primary administrator account cannot be changed here.")
    account.is_active = data.is_active
    db.commit()
    return {"message": "Account status updated."}


@router.get("/api/admissions")
def active_admissions(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "staff")),
):
    rows = db.query(Admission).filter(Admission.discharged_at.is_(None)).order_by(Admission.admitted_at.desc()).all()
    return [{
        "id": row.id,
        "patient_id": row.patient_id,
        "patient_name": row.patient.full_name,
        "bed_number": row.bed.bed_number,
        "ward": row.bed.ward,
        "admitted_at": row.admitted_at,
    } for row in rows]
