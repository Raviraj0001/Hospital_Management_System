# Hospital Management Portal

A role-based hospital management application built with Python, FastAPI, SQLAlchemy, SQLite/PostgreSQL, HTML, CSS and JavaScript. Local development continues to use SQLite; cloud deployments can use PostgreSQL through `DATABASE_URL`.

The application uses separate access for the hospital administrator, doctors, hospital staff and patients. It does not connect to an external hospital website or use generated patient records.

## 1. Roles and permissions

### Hospital administrator
The administrator is responsible for setting up and managing the portal. The admin can:
- Add doctor profiles and issue employee IDs.
- Add staff profiles and issue employee IDs.
- Create patient records and issue patient registration codes.
- Enable or disable linked employee and patient logins.
- Mark doctors as available or unavailable.
- Add beds and manage the hospital bed inventory.
- Add facilities such as CT Scan, MRI, X-Ray, laboratory or pharmacy and choose which services patients can see.
- View appointments, patient records, bills, bed requests, admissions and staff attendance.
- Manage bed requests, assign beds, discharge patients and manage billing.

The admin account is created automatically on the first run. Admin registration is not available from the public sign-up page. For local development, the default account is `admin@gmail.com` / `Admin@123`. For a new cloud database, set `HMS_ADMIN_EMAIL` and `HMS_ADMIN_PASSWORD` before the first deployment.

### Doctor
A doctor cannot create a doctor account independently. The administrator must first add the doctor profile with the doctor's full name, Gmail address, specialization and employee ID.

The doctor then activates the account using the exact name, Gmail address and employee ID. Once signed in, a doctor can:
- View appointments assigned to their doctor profile.
- Confirm, complete or cancel their own appointments.
- Mark their own attendance once per day.
- Mark themselves available or unavailable for new appointments.
- Create treatment notes and prescriptions for appointments assigned to them.
- Archive their own medical records. Archived records remain stored in the database.

### Hospital staff
Hospital staff must also be added by the administrator before they can activate an account with their assigned employee ID.

Staff can:
- View operational appointments and update their status.
- View patient register information needed for operations.
- Review bed requests and assign available beds.
- Discharge patients and release beds.
- Create bills and mark bills as paid.
- Mark their own attendance once per day.

Staff cannot create or edit clinical treatment records.

### Patient
Patients can register with their Gmail address, or activate a patient profile that was created by the administrator using a patient registration code.

A patient can:
- View the doctor directory, specialties, consultation fees and current availability.
- Book an appointment only with a doctor marked available.
- View only their own appointments.
- View only their own medical records, prescriptions and bills.
- See the number of available beds.
- View facilities that the administrator has marked as available.
- Send a bed request. A request is not a confirmed admission until hospital staff assigns an available bed.

Patients cannot access hospital management, staff information, other patients' data, internal billing registers or attendance reports.

## 2. Login and account setup

The first page shows three hospital login choices:
1. Hospital Admin
2. Doctor
3. Hospital Staff

Patient access is available separately below those choices.

### First administrator login

On the first start, the application creates this local administrator account:

| Field | Value |
|---|---|
| Gmail | `admin@gmail.com` |
| Password | `Admin@123` |

Change the password after the first login through `POST /api/auth/change-password` in the API documentation (`/docs`) using your current bearer token. Keep the local administrator credentials private.

### Add a doctor or staff member

1. Sign in as the administrator.
2. Open Team Management.
3. Add the employee's name, Gmail address and employee ID.
4. Share the employee ID with the employee privately.
5. The employee chooses Doctor or Hospital Staff on the sign-in page.
6. The employee selects account activation and enters the same name, Gmail and employee ID.
7. After activation, the employee can sign in using their selected role.

A person cannot activate a doctor or staff account without a matching invitation created by the administrator.

### Add a patient

The administrator can create a patient profile and provide a patient registration code. The patient uses the Patient access link and enters the same Gmail address and registration code during registration.

A patient who has not been pre-registered by the hospital can create their own patient account directly.

## 3. Database and saved information

For local development, the database file is `hospital_portal.db`. It is created automatically in the project folder when the application starts. User accounts, patient profiles, doctors, staff, appointments, records, prescriptions, beds, admissions, facilities, bills and attendance are stored there.

For cloud deployment, set `DATABASE_URL` to a managed PostgreSQL connection string. The application selects PostgreSQL when this variable is present; otherwise it continues to use the local SQLite file. The PostgreSQL driver is included in `requirements.txt`.

Each account is linked to its own user ID. Logging out does not delete information. When a person signs in again with the same Gmail and password, the backend retrieves the data linked to that account.

**Important:** This is a local SQLite database. It persists on the computer where the application runs. It does not synchronize between different computers. For multi-computer hospital use, deploy the application to a secure server and use a managed database with backups.

Do not delete `hospital_portal.db` if you want to keep the saved records. Back it up before moving or replacing the project. This version uses a new database filename; an older `hospital.db` from the previous project is left untouched and is not automatically migrated. The new portal starts with an empty hospital register, apart from the administrator account, so add your real doctors, beds and facilities from the admin workspace rather than expecting sample records.

## 4. Run on Windows

Python 3.11 is recommended.

**One-click option:** Extract the ZIP, open the `Hospital_Management_System` folder and double-click `RUN_HOSPITAL.bat`. The launcher creates the Python 3.11 virtual environment if needed, installs the listed requirements, opens the browser and starts the local server. Keep the black terminal window open while using the portal. Press `Ctrl + C` to stop it.

**Manual option in VS Code:** Open the project folder, open Terminal and run:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

If PowerShell blocks environment activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

If you already created a virtual environment with Python 3.14, remove only the old `venv` folder and recreate it with `py -3.11 -m venv venv`. Do not delete the database file.

Open the local application:

- Portal: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs

Keep the terminal running while using the portal. Press `Ctrl + C` to stop the server.

## 5. Deploy from GitHub (Railway + PostgreSQL)

This repository includes a `Procfile` and `railway.json` for a Railway web service. A persistent PostgreSQL database is recommended for cloud hosting; do not rely on a temporary container filesystem for SQLite data.

1. Create a GitHub repository and push the contents of this project folder. Keep `.gitignore` in the repository. Do not upload `venv/`, `.env`, or any `.db` file.
2. In Railway, create a new project from the GitHub repository.
3. Add a PostgreSQL database service to the Railway project.
4. In the web service's Variables, set `DATABASE_URL` to the PostgreSQL service's connection URL. Railway commonly exposes this as a reference variable such as `${{Postgres.DATABASE_URL}}`; select the actual variable from the database service rather than typing a guessed value.
5. Add these web-service variables before the first deployment:
   - `APP_ENV` = `production`
   - `HMS_SECRET_KEY` = a securely generated random secret of at least 32 characters
   - `HMS_ADMIN_EMAIL` = the administrator email you want to use
   - `HMS_ADMIN_PASSWORD` = a unique strong administrator password
6. Deploy the service and open the public domain generated by Railway. Check `/docs` to confirm the API is responding.
7. Sign in using the admin email and password configured above. The initial admin account is created only if that email does not already exist in the database.

Generate a strong secret locally with Python:

```powershell
py -3.11 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output into Railway's `HMS_SECRET_KEY` variable. Never commit the secret or production `.env` file to GitHub.

**Important deployment notes:**
- Environment variables must be set in the hosting dashboard, not committed to the repository.
- If the database already contains an admin account, changing `HMS_ADMIN_PASSWORD` does not reset that existing account's password.
- This project uses `Base.metadata.create_all()` for initial table creation; it does not yet include Alembic migrations. Back up the database before schema changes.
- Before using a public deployment, change the default admin password, use HTTPS, configure backups and review security/privacy requirements. This is an educational prototype, not a certified system for real patient data.
- Do not upload an existing local SQLite database to a public GitHub repository. If you need to migrate existing local records to PostgreSQL, perform a controlled private migration and verify it before switching users to the cloud site.

## 6. Folder structure

```text
Hospital_Management_System/
│
├── RUN_HOSPITAL.bat    # One-click Windows setup and launch
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application and initial admin setup
│   ├── database.py      # SQLite/PostgreSQL connection and database sessions
│   ├── models.py        # Database tables and relationships
│   ├── schemas.py       # Input validation
│   ├── security.py      # Password hashing and JWT token creation
│   ├── auth.py          # Registration, login and role checks
│   ├── hospital.py      # Admin, staff, facilities, beds and attendance
│   ├── care.py          # Appointments, treatment records and prescriptions
│   └── static/
│       ├── login.html
│       ├── dashboard.html
│       ├── css/
│       │   └── style.css
│       └── js/
│           ├── common.js
│           └── dashboard.js
│
├── requirements.txt
├── .gitignore
├── .env.example
├── Procfile
├── railway.json
├── README.md
└── hospital_portal.db   # Created automatically on first run
```

## 7. Important implementation details

- The login form sends the selected role to the backend. The backend checks that the selected role matches the role stored for that Gmail account.
- Passwords are stored as salted PBKDF2-SHA256 hashes, not plain text.
- Signed HS256 JWT tokens protect the API routes after login.
- The doctor workspace displays the name and employee ID issued by the administrator, the successful sign-in time for the current browser session and a live local clock.
- Patient API queries are filtered by the patient profile linked to the logged-in user.
- Doctor API queries are filtered by the doctor profile linked to the logged-in user.
- Staff and admin routes are protected by role checks.
- A database unique constraint prevents two appointments from being booked for the same doctor at the exact same time.
- A patient can request a bed, but staff or admin must assign an actual available bed.
- Archived medical records are retained in the database rather than permanently deleted.

## 8. Project limitations and safety

- Gmail-only registration checks the email suffix. It does not prove mailbox ownership. Real email verification requires an email delivery service.
- The initial admin password and JWT secret are local development values. Set a strong `HMS_SECRET_KEY`, change the admin password and use HTTPS before deployment.
- This project is an educational prototype, not a certified hospital information system. Do not enter real patient information. A real deployment needs a security and privacy review, audit logging, database backups, access monitoring, migrations, HTTPS and applicable healthcare compliance.
- The displayed bed count and facilities reflect only what the administrator has entered into this local database. They are not fetched from a real hospital website.
- The admin dashboard shows current bed occupancy as a descriptive operating range: Low (below 40%), Moderate (40–75%) or High (above 75%). This is a live capacity indicator, not a forecast or clinical risk prediction.
- This version does not contain a machine-learning clinical prediction module. No medical risk score is generated or presented as a diagnosis.
- The appointment availability flag is a simple on/off control. A production scheduler should add doctor working hours, holidays, appointment duration and slot rules.

## 9. How to explain the project in an interview

"I built a role-based Hospital Management Portal using FastAPI, SQLAlchemy and SQLite. The portal has separate access for the administrator, doctors, hospital staff and patients. The administrator creates doctor and staff profiles before they can activate accounts using their assigned employee IDs. Patients can register directly or use a hospital-issued registration code.

After login, the backend issues a JWT token and checks the user's role on protected routes. Patient queries are restricted to the patient profile linked to that account. Doctors can manage their own appointments, attendance, treatment notes and prescriptions. Staff manage operational work such as bed requests, admissions and billing. The administrator manages users, hospital facilities, beds and the overall portal. SQLAlchemy connects the application to SQLite, where records remain saved after logout and application restarts."
