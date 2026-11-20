from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import get_db
from .models import User, Patient, Doctor, Appointment, MedicalRecord
from .schemas import AppointmentInput, AppointmentStatusInput, RecordInput
from .auth import get_current_user, require_roles, linked_doctor

router = APIRouter(tags=["Appointments and clinical records"])


def patient_for_user(db: Session, user: User):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise HTTPException(404, "Patient profile not found.")
    return patient


def appointment_row(item: Appointment):
    return {
        "id": item.id,
        "patient_id": item.patient_id,
        "patient_name": item.patient.full_name,
        "doctor_id": item.doctor_id,
        "doctor_name": item.doctor.full_name,
        "appointment_at": item.appointment_at,
        "status": item.status,
    }


@router.get("/api/appointments")
def list_appointments(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(Appointment)
    if user.role == "patient":
        patient = patient_for_user(db, user)
        query = query.filter(Appointment.patient_id == patient.id)
    elif user.role == "doctor":
        doctor = linked_doctor(db, user)
        query = query.filter(Appointment.doctor_id == doctor.id)
    elif user.role not in ("admin", "staff"):
        raise HTTPException(403, "Your account cannot view appointments.")
    rows = query.order_by(Appointment.appointment_at.desc()).all()
    return [appointment_row(item) for item in rows]


@router.post("/api/appointments")
def book_appointment(
    data: AppointmentInput,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.role == "patient":
        patient = patient_for_user(db, user)
    elif user.role in ("admin", "staff"):
        patient = db.get(Patient, getattr(data, "patient_id", None))
        # Admin/staff booking uses the explicit patient_id supplied by the UI.
        if not patient:
            raise HTTPException(404, "Patient not found.")
    else:
        raise HTTPException(403, "Only patients, staff or admin can book appointments.")

    doctor = db.get(Doctor, data.doctor_id)
    if not doctor:
        raise HTTPException(404, "Doctor not found.")
    if not doctor.is_available:
        raise HTTPException(409, "This doctor is currently marked unavailable.")

    appointment_time = data.appointment_at
    if appointment_time.tzinfo is not None:
        appointment_time = appointment_time.astimezone(timezone.utc).replace(tzinfo=None)
    if appointment_time <= datetime.utcnow():
        raise HTTPException(400, "Choose a future appointment time.")

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_at=appointment_time,
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This doctor already has an appointment at that time. Choose another time.")
    db.refresh(appointment)
    return {"message": "Appointment booked successfully.", "appointment_id": appointment.id}


@router.patch("/api/appointments/{appointment_id}/status")
def update_appointment_status(
    appointment_id: int,
    data: AppointmentStatusInput,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(404, "Appointment not found.")
    if user.role == "doctor":
        doctor = linked_doctor(db, user)
        if appointment.doctor_id != doctor.id:
            raise HTTPException(403, "You can only update appointments assigned to you.")
    elif user.role not in ("admin", "staff"):
        raise HTTPException(403, "Patients cannot change appointment status.")

    if data.status not in ("Booked", "Confirmed", "Completed", "Cancelled"):
        raise HTTPException(400, "Choose Booked, Confirmed, Completed or Cancelled.")
    appointment.status = data.status
    db.commit()
    return {"message": "Appointment status updated."}


@router.get("/api/records")
def list_records(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(MedicalRecord).filter(MedicalRecord.is_archived.is_(False))
    if user.role == "patient":
        patient = patient_for_user(db, user)
        query = query.filter(MedicalRecord.patient_id == patient.id)
    elif user.role == "doctor":
        doctor = linked_doctor(db, user)
        # A doctor can review history for patients who have an appointment with them.
        patient_ids = db.query(Appointment.patient_id).filter(
            Appointment.doctor_id == doctor.id
        ).subquery()
        query = query.filter(MedicalRecord.patient_id.in_(patient_ids))
    elif user.role != "admin":
        raise HTTPException(403, "Your account cannot view medical records.")
    rows = query.order_by(MedicalRecord.created_at.desc()).all()
    return [{
        "id": row.id,
        "patient_id": row.patient_id,
        "patient_name": row.patient.full_name,
        "doctor_id": row.doctor_id,
        "doctor_name": row.doctor.full_name,
        "appointment_id": row.appointment_id,
        "diagnosis": row.diagnosis,
        "treatment": row.treatment,
        "medicines": row.medicines,
        "notes": row.notes,
        "created_at": row.created_at,
    } for row in rows]


@router.post("/api/records")
def create_record(
    data: RecordInput,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "doctor")),
):
    patient = db.get(Patient, data.patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found.")

    if user.role == "doctor":
        doctor = linked_doctor(db, user)
        doctor_id = doctor.id
        if data.appointment_id is None:
            raise HTTPException(400, "Select one of your appointments before writing a treatment record.")
        appointment = db.get(Appointment, data.appointment_id)
        if not appointment or appointment.doctor_id != doctor.id or appointment.patient_id != patient.id:
            raise HTTPException(403, "The selected appointment is not assigned to your doctor account.")
    else:
        if data.appointment_id is None:
            doctor_id = None
        else:
            appointment = db.get(Appointment, data.appointment_id)
            if not appointment or appointment.patient_id != patient.id:
                raise HTTPException(400, "Appointment does not match this patient.")
            doctor_id = appointment.doctor_id
        if doctor_id is None:
            raise HTTPException(400, "Select a valid appointment so the doctor can be identified.")

    record = MedicalRecord(
        patient_id=patient.id,
        doctor_id=doctor_id,
        appointment_id=data.appointment_id,
        diagnosis=data.diagnosis.strip(),
        treatment=data.treatment.strip(),
        medicines=data.medicines.strip(),
        notes=data.notes.strip(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": "Treatment and prescription saved to the patient's record.", "record_id": record.id}


@router.post("/api/records/{record_id}/archive")
def archive_record(
    record_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    record = db.get(MedicalRecord, record_id)
    if not record or record.is_archived:
        raise HTTPException(404, "Active medical record not found.")
    if user.role == "doctor":
        doctor = linked_doctor(db, user)
        if record.doctor_id != doctor.id:
            raise HTTPException(403, "You can only archive records you created.")
    elif user.role != "admin":
        raise HTTPException(403, "Only the treating doctor or admin can archive a record.")
    # Keep the clinical history in the database; hide it from normal patient views.
    record.is_archived = True
    db.commit()
    return {"message": "Record archived. The original entry remains in the database."}
