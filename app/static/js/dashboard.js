const role = localStorage.getItem("hms_role");
const token = localStorage.getItem("hms_token");
const email = localStorage.getItem("hms_email");

if (!token || !role) {
  window.location.href = "/";
}

let patientProfile = null;
let doctorProfile = null;
let currentAvailability = false;

const byId = id => document.getElementById(id);
const money = amount => `₹${Number(amount || 0).toLocaleString("en-IN")}`;
const dateText = value => value ? new Date(value).toLocaleString() : "—";

function showForRole() {
  document.querySelectorAll("[data-roles]").forEach(section => {
    const roles = section.dataset.roles.split(",").map(item => item.trim());
    section.classList.toggle("hidden", !roles.includes(role));
  });

  const titles = {
    admin: ["Hospital administration", "Manage the hospital team, services and daily operations."],
    doctor: ["Doctor workspace", "Review your appointments, record treatment and manage availability."],
    staff: ["Hospital operations", "Support appointments, admissions, billing and daily operations."],
    patient: ["Patient portal", "View hospital services and manage your own appointments and records."]
  };
  byId("welcome-title").textContent = titles[role][0];
  byId("welcome-copy").textContent = titles[role][1];
  byId("role-label").textContent = `${role[0].toUpperCase()}${role.slice(1)} access`;
  byId("sidebar-email").textContent = email || "Signed in";
  byId("user-avatar").textContent = (email || "H").charAt(0).toUpperCase();
  byId("page-title").textContent = titles[role][0];
  byId("profile-label").textContent = `${role[0].toUpperCase()}${role.slice(1)} workspace`;
  const signedInAt = localStorage.getItem("hms_login_time");
  byId("login-time-label").textContent = signedInAt
    ? `Signed in at ${new Date(signedInAt).toLocaleTimeString("en-IN", {hour: "2-digit", minute: "2-digit"})}`
    : "Current session";
}

function renderList(id, rows, emptyText = "No records found.") {
  const target = byId(id);
  if (!target) return;
  target.innerHTML = rows.length
    ? rows.join("")
    : `<p class="muted empty-state">${escapeHtml(emptyText)}</p>`;
}

function appointmentActions(item) {
  if (!["admin", "staff", "doctor"].includes(role)) return "";
  const buttons = ["Confirmed", "Completed", "Cancelled"].map(status =>
    `<button class="small-action" data-action="appointment-status" data-id="${item.id}" data-status="${status}">${status}</button>`
  ).join("");
  return `<div class="row-actions">${buttons}</div>`;
}

async function loadDoctors() {
  const doctors = await apiRequest("/api/doctors");
  const available = doctors.filter(doctor => doctor.is_available);
  byId("public-doctors-count") && (byId("public-doctors-count").textContent = available.length);

  renderList("doctor-list", doctors.map(doctor => `
    <article class="data-row">
      <div class="row-main">
        <strong>${escapeHtml(doctor.full_name)}</strong>
        <span>${escapeHtml(doctor.specialization)}</span>
        <small>Consultation: ${money(doctor.consultation_fee)}</small>
      </div>
      <span class="status ${doctor.is_available ? "status-good" : "status-muted"}">
        ${doctor.is_available ? "Available" : "Unavailable"}
      </span>
    </article>
  `), "No doctor profiles have been added by the administrator yet.");

  const select = byId("book-doctor");
  if (select) {
    select.innerHTML = `<option value="">Choose an available doctor</option>` +
      available.map(doctor => `<option value="${doctor.id}">${escapeHtml(doctor.full_name)} — ${escapeHtml(doctor.specialization)}</option>`).join("");
  }
}

async function loadAppointments() {
  const appointments = await apiRequest("/api/appointments");
  if (role === "doctor") {
    const now = new Date();
    const upcoming = appointments.filter(item =>
      new Date(item.appointment_at) >= now && !["Completed", "Cancelled"].includes(item.status)
    );
    byId("doctor-appointments-count").textContent = appointments.length;
    byId("doctor-upcoming-count").textContent = upcoming.length;
  }
  renderList("appointment-list", appointments.map(item => `
    <article class="data-row appointment-row">
      <div class="row-main">
        <strong>Appointment #${item.id}</strong>
        <span>${escapeHtml(item.patient_name)} with ${escapeHtml(item.doctor_name)}</span>
        <small>${dateText(item.appointment_at)}</small>
      </div>
      <div class="row-side">
        <span class="status ${item.status === "Completed" ? "status-good" : item.status === "Cancelled" ? "status-muted" : "status-waiting"}">${escapeHtml(item.status)}</span>
        ${appointmentActions(item)}
      </div>
    </article>
  `), "No appointments have been booked yet.");
}

async function loadRecords() {
  if (!["admin", "doctor", "patient"].includes(role)) return;
  const records = await apiRequest("/api/records");
  renderList("record-list", records.map(item => `
    <article class="data-row">
      <div class="row-main">
        <strong>${escapeHtml(item.diagnosis)}</strong>
        <span>${escapeHtml(item.treatment)}</span>
        <small>Patient: ${escapeHtml(item.patient_name)} · Doctor: ${escapeHtml(item.doctor_name)} · ${dateText(item.created_at)}</small>
        <small>Prescription: ${escapeHtml(item.medicines || "No medicine listed")}</small>
        ${item.notes ? `<small>Notes: ${escapeHtml(item.notes)}</small>` : ""}
      </div>
      ${(role === "admin" || (role === "doctor" && doctorProfile && item.doctor_id === doctorProfile.id)) ? `<button class="small-action danger-action" data-action="archive-record" data-id="${item.id}">Archive</button>` : ""}
    </article>
  `), "No medical records are available for this account.");
}

async function loadPublicHospital() {
  const info = await apiRequest("/api/public/hospital");
  byId("public-beds-count").textContent = info.available_beds;
  byId("public-total-beds").textContent = `${info.total_beds} beds in the hospital register`;

  renderList("facility-list", info.facilities.map(item => `
    <article class="facility-card">
      <span class="facility-icon">+</span>
      <strong>${escapeHtml(item.name)}</strong>
      <p>${escapeHtml(item.description || "Hospital service available.")}</p>
      <span class="status status-good">Available</span>
    </article>
  `), "Hospital facilities have not been published yet. Please contact the reception desk.");

  if (role === "patient") {
    const requests = await apiRequest("/api/bed-requests");
    renderList("my-bed-requests", requests.map(item => `
      <article class="data-row">
        <div class="row-main"><strong>Bed request #${item.id}</strong><small>${escapeHtml(item.reason || "No additional note")}</small></div>
        <span class="status ${item.status === "Approved" ? "status-good" : "status-waiting"}">${escapeHtml(item.status)}</span>
      </article>
    `), "You have not made a bed request.");
  }
}

async function loadAdminSummary() {
  const summary = await apiRequest("/api/admin/summary");
  byId("patients-count").textContent = summary.patients;
  byId("doctors-count").textContent = summary.doctors;
  byId("active-doctors-count").textContent = `${summary.active_doctors} available`;
  byId("appointments-count").textContent = summary.appointments;
  byId("beds-count").textContent = summary.available_beds;
  byId("total-beds-count").textContent = `${summary.total_beds} total beds`;
  const occupied = Math.max(0, summary.total_beds - summary.available_beds);
  const occupancy = summary.total_beds ? Math.round((occupied / summary.total_beds) * 100) : 0;
  const level = !summary.total_beds ? "Not set" : occupancy < 40 ? "Low" : occupancy <= 75 ? "Moderate" : "High";
  byId("bed-occupancy-meter").style.width = `${occupancy}%`;
  byId("bed-occupancy-level").textContent = summary.total_beds
    ? `${occupancy}% occupied · ${level} occupancy`
    : "Add beds to view occupancy";
}

async function loadAdminTables() {
  if (role !== "admin") return;
  const [doctors, staff, patients, facilities] = await Promise.all([
    apiRequest("/api/admin/doctors"),
    apiRequest("/api/admin/staff"),
    apiRequest("/api/admin/patients"),
    apiRequest("/api/admin/facilities")
  ]);

  renderList("admin-doctor-list", doctors.map(item => `
    <article class="data-row compact-row">
      <div class="row-main"><strong>${escapeHtml(item.full_name)}</strong><small>${escapeHtml(item.email)} · ${escapeHtml(item.employee_code)}</small><small>${escapeHtml(item.specialization)} · ${item.activated ? "Account activated" : "Invitation pending"}</small></div>
      <div class="row-actions">
        <button class="small-action" data-action="doctor-availability" data-id="${item.id}" data-value="${!item.is_available}">${item.is_available ? "Set unavailable" : "Set available"}</button>
        ${item.user_id ? `<button class="small-action" data-action="account-status" data-id="${item.user_id}" data-value="${!item.account_active}">${item.account_active ? "Disable login" : "Enable login"}</button>` : ""}
      </div>
    </article>
  `), "No doctors added yet.");

  renderList("admin-staff-list", staff.map(item => `
    <article class="data-row compact-row"><div class="row-main"><strong>${escapeHtml(item.full_name)}</strong><small>${escapeHtml(item.email)} · ${escapeHtml(item.employee_code)}</small><small>${escapeHtml(item.job_title)} · ${item.activated ? "Account activated" : "Invitation pending"}</small></div>${item.user_id ? `<button class="small-action" data-action="account-status" data-id="${item.user_id}" data-value="${!item.account_active}">${item.account_active ? "Disable login" : "Enable login"}</button>` : ""}</article>
  `), "No staff profiles added yet.");

  renderList("admin-patient-list", patients.map(item => `
    <article class="data-row compact-row"><div class="row-main"><strong>${escapeHtml(item.full_name)} · Patient #${item.id}</strong><small>${escapeHtml(item.email)} · Age ${item.age}</small><small>${item.registered ? "Portal account active" : "Registration pending"}</small></div>${item.user_id ? `<button class="small-action" data-action="account-status" data-id="${item.user_id}" data-value="${!item.account_active}">${item.account_active ? "Disable login" : "Enable login"}</button>` : ""}</article>
  `), "No patients registered yet.");

  renderList("admin-facility-list", facilities.map(item => `
    <article class="data-row compact-row"><div class="row-main"><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.description)}</small><small>${item.is_available ? "Visible to patients" : "Not published"}</small></div>
      <button class="small-action" data-action="facility-status" data-id="${item.id}" data-value="${!item.is_available}">${item.is_available ? "Hide" : "Publish"}</button>
    </article>
  `), "No facilities added yet.");
}

async function loadOperations() {
  if (!["admin", "staff"].includes(role)) return;
  const [beds, requests, bills, patients, admissions] = await Promise.all([
    apiRequest("/api/managed/beds"),
    apiRequest("/api/bed-requests"),
    apiRequest("/api/billing"),
    apiRequest("/api/admin/patients"),
    apiRequest("/api/admissions")
  ]);

  renderList("managed-bed-list", beds.map(item => `
    <article class="data-row compact-row"><div class="row-main"><strong>${escapeHtml(item.bed_number)} · ${escapeHtml(item.ward)}</strong></div><span class="status ${item.is_occupied ? "status-muted" : "status-good"}">${item.is_occupied ? "Occupied" : "Available"}</span></article>
  `), "No beds have been added to the hospital inventory.");

  renderList("bed-request-list", requests.map(item => `
    <article class="data-row">
      <div class="row-main"><strong>Request #${item.id} · ${escapeHtml(item.patient_name)}</strong><small>Patient #${item.patient_id} · ${escapeHtml(item.reason || "No additional note")}</small><small>${dateText(item.requested_at)}</small></div>
      <div class="row-side"><span class="status ${item.status === "Approved" ? "status-good" : "status-waiting"}">${escapeHtml(item.status)}</span>
      ${item.status === "Pending" ? `<div class="assign-bed"><input type="number" min="1" id="assign-bed-${item.id}" placeholder="Bed ID"><button class="small-action" data-action="assign-bed" data-id="${item.id}">Assign</button></div>` : ""}</div>
    </article>
  `), "No bed requests.");

  renderList("admission-list", admissions.map(item => `
    <article class="data-row compact-row">
      <div class="row-main"><strong>${escapeHtml(item.patient_name)} · ${escapeHtml(item.bed_number)}</strong><small>Patient #${item.patient_id} · ${escapeHtml(item.ward)} ward · ${dateText(item.admitted_at)}</small></div>
      <button class="small-action danger-action" data-action="discharge" data-id="${item.id}">Discharge</button>
    </article>
  `), "No active admissions.");

  renderList("bill-list", bills.map(item => `
    <article class="data-row compact-row"><div class="row-main"><strong>Bill #${item.id} · Patient #${item.patient_id}</strong><small>${escapeHtml(item.description)} · ${money(item.amount)}</small></div><div class="row-side"><span class="status ${item.status === "Paid" ? "status-good" : "status-waiting"}">${escapeHtml(item.status)}</span>${item.status !== "Paid" ? `<button class="small-action" data-action="bill-paid" data-id="${item.id}">Mark paid</button>` : ""}</div></article>
  `), "No bills have been created.");

  const patientSelect = byId("bill-patient");
  if (patientSelect && role === "staff") {
    patientSelect.placeholder = "Patient ID";
  }
  if (role === "admin") {
    const attendance = await apiRequest("/api/admin/attendance");
    renderList("attendance-report", attendance.map(item => `
      <article class="data-row compact-row"><div class="row-main"><strong>${escapeHtml(item.employee)} · ${escapeHtml(item.employee_type)}</strong><small>${dateText(item.date)} · ${escapeHtml(item.status)}</small></div></article>
    `), "No attendance entries yet.");
  }
}

async function loadDoctorProfile() {
  if (role !== "doctor") return;
  doctorProfile = await apiRequest("/api/doctors/me");
  currentAvailability = doctorProfile.is_available;
  byId("availability-button").textContent = currentAvailability ? "Set myself unavailable" : "Set myself available";
  byId("welcome-eyebrow").textContent = `DOCTOR DASHBOARD · ${doctorProfile.employee_code}`;
  const doctorName = doctorProfile.full_name.trim();
  const displayName = /^dr\.?\s/i.test(doctorName) ? doctorName : `Dr. ${doctorName}`;
  byId("welcome-title").textContent = `Welcome, ${displayName}`;
  byId("welcome-copy").textContent = `${doctorProfile.specialization} · Your appointments and clinic tools are ready.`;
  byId("profile-label").textContent = `Doctor login · ${doctorProfile.employee_code}`;
  byId("doctor-availability-value").textContent = currentAvailability ? "Available" : "Unavailable";
  byId("doctor-availability-value").classList.toggle("metric-good", currentAvailability);
  byId("doctor-availability-note").textContent = currentAvailability
    ? "Patients can request an appointment"
    : "New bookings are currently paused";
  showMessage("availability-message", `Current status: ${currentAvailability ? "Available for bookings" : "Not available for bookings"}`, true);
}

async function loadPatientProfile() {
  if (role !== "patient") return;
  patientProfile = await apiRequest("/api/patients/me");
  byId("welcome-eyebrow").textContent = `WELCOME, ${patientProfile.full_name.toUpperCase()}`;
}

async function loadAll() {
  try {
    const account = await apiRequest("/api/auth/me");
    if (account.role !== role) {
      localStorage.clear();
      window.location.href = "/";
      return;
    }
    showForRole();
    if (role === "patient") await loadPatientProfile();
    if (role === "doctor") await loadDoctorProfile();

    await loadDoctors();
    await loadAppointments();
    if (["admin", "doctor", "patient"].includes(role)) await loadRecords();

    if (role === "patient") {
      await loadPublicHospital();
      const bills = await apiRequest("/api/billing");
      renderList("patient-bill-list", bills.map(item => `
        <article class="data-row"><div class="row-main"><strong>Bill #${item.id}</strong><span>${escapeHtml(item.description)}</span><small>${dateText(item.created_at)}</small></div><div class="row-side"><strong>${money(item.amount)}</strong><span class="status ${item.status === "Paid" ? "status-good" : "status-waiting"}">${escapeHtml(item.status)}</span></div></article>
      `), "No bills are linked to your account.");
    }
    if (role === "admin") {
      await loadAdminSummary();
      await loadAdminTables();
      await loadOperations();
    }
    if (role === "staff") {
      await loadOperations();
    }
  } catch (error) {
    console.error(error);
    const messageTarget = byId("book-message");
    if (messageTarget) showMessage("book-message", error.message);
  }
}

byId("logout").addEventListener("click", () => {
  localStorage.removeItem("hms_token");
  localStorage.removeItem("hms_role");
  localStorage.removeItem("hms_email");
  localStorage.removeItem("hms_login_time");
  window.location.href = "/";
});

byId("book-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const payload = {
      doctor_id: Number(byId("book-doctor").value),
      appointment_at: new Date(byId("book-time").value).toISOString()
    };
    if (role !== "patient") payload.patient_id = Number(byId("book-patient").value);
    await apiRequest("/api/appointments", {method: "POST", body: JSON.stringify(payload)});
    showMessage("book-message", "Appointment booked successfully.", true);
    event.target.reset();
    await loadAppointments();
  } catch (error) {
    showMessage("book-message", error.message);
  }
});

byId("bed-request-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const result = await apiRequest("/api/bed-requests", {
      method: "POST",
      body: JSON.stringify({reason: byId("bed-reason").value})
    });
    showMessage("bed-request-message", result.message, true);
    byId("bed-reason").value = "";
    await loadPublicHospital();
  } catch (error) {
    showMessage("bed-request-message", error.message);
  }
});

byId("record-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const payload = {
      patient_id: Number(byId("record-patient").value),
      appointment_id: Number(byId("record-appointment").value),
      diagnosis: byId("record-diagnosis").value,
      treatment: byId("record-treatment").value,
      medicines: byId("record-medicines").value,
      notes: byId("record-notes").value
    };
    await apiRequest("/api/records", {method: "POST", body: JSON.stringify(payload)});
    showMessage("record-message", "Treatment and prescription saved.", true);
    event.target.reset();
    await loadRecords();
  } catch (error) {
    showMessage("record-message", error.message);
  }
});

byId("doctor-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const payload = {
      full_name: byId("new-doctor-name").value,
      email: byId("new-doctor-email").value,
      employee_code: byId("new-doctor-code").value,
      specialization: byId("new-doctor-specialty").value,
      phone: byId("new-doctor-phone").value,
      consultation_fee: Number(byId("new-doctor-fee").value)
    };
    const result = await apiRequest("/api/admin/doctors", {method: "POST", body: JSON.stringify(payload)});
    showMessage("doctor-message", `${result.message} Employee ID: ${payload.employee_code}`, true);
    event.target.reset();
    await loadAdminTables();
    await loadDoctors();
  } catch (error) { showMessage("doctor-message", error.message); }
});

byId("staff-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const payload = {
      full_name: byId("new-staff-name").value,
      email: byId("new-staff-email").value,
      employee_code: byId("new-staff-code").value,
      job_title: byId("new-staff-title").value,
      phone: byId("new-staff-phone").value
    };
    const result = await apiRequest("/api/admin/staff", {method: "POST", body: JSON.stringify(payload)});
    showMessage("staff-message", `${result.message} Employee ID: ${payload.employee_code}`, true);
    event.target.reset();
    await loadAdminTables();
  } catch (error) { showMessage("staff-message", error.message); }
});

byId("patient-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const payload = {
      full_name: byId("new-patient-name").value,
      email: byId("new-patient-email").value,
      registration_code: byId("new-patient-code").value,
      age: Number(byId("new-patient-age").value),
      phone: byId("new-patient-phone").value,
      address: byId("new-patient-address").value
    };
    const result = await apiRequest("/api/admin/patients", {method: "POST", body: JSON.stringify(payload)});
    showMessage("patient-message", `${result.message} Registration code: ${payload.registration_code}`, true);
    event.target.reset();
    await loadAdminTables();
  } catch (error) { showMessage("patient-message", error.message); }
});

byId("facility-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const payload = {
      name: byId("facility-name").value,
      description: byId("facility-description").value,
      is_available: byId("facility-available").checked
    };
    await apiRequest("/api/admin/facilities", {method: "POST", body: JSON.stringify(payload)});
    showMessage("facility-message", "Facility saved.", true);
    event.target.reset();
    await loadAdminTables();
  } catch (error) { showMessage("facility-message", error.message); }
});

byId("bed-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await apiRequest("/api/admin/beds", {
      method: "POST",
      body: JSON.stringify({bed_number: byId("bed-number").value, ward: byId("bed-ward").value})
    });
    showMessage("bed-message", "Bed added to the hospital inventory.", true);
    event.target.reset();
    await loadOperations();
    await loadAdminSummary();
  } catch (error) { showMessage("bed-message", error.message); }
});

byId("bill-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await apiRequest("/api/billing", {
      method: "POST",
      body: JSON.stringify({
        patient_id: Number(byId("bill-patient").value),
        description: byId("bill-description").value,
        amount: Number(byId("bill-amount").value)
      })
    });
    showMessage("bill-message", "Bill created.", true);
    event.target.reset();
    await loadOperations();
  } catch (error) { showMessage("bill-message", error.message); }
});

byId("attendance-button").addEventListener("click", async () => {
  try {
    const result = await apiRequest("/api/attendance/me", {method: "POST"});
    showMessage("attendance-message", result.message, true);
  } catch (error) { showMessage("attendance-message", error.message); }
});

byId("availability-button").addEventListener("click", async () => {
  try {
    const nextStatus = !currentAvailability;
    const result = await apiRequest(`/api/doctors/me/availability?is_available=${nextStatus}`, {method: "PATCH"});
    currentAvailability = result.is_available;
    byId("availability-button").textContent = currentAvailability ? "Set myself unavailable" : "Set myself available";
    byId("doctor-availability-value").textContent = currentAvailability ? "Available" : "Unavailable";
    byId("doctor-availability-value").classList.toggle("metric-good", currentAvailability);
    byId("doctor-availability-note").textContent = currentAvailability
      ? "Patients can request an appointment"
      : "New bookings are currently paused";
    showMessage("availability-message", result.message, true);
    await loadDoctors();
  } catch (error) { showMessage("availability-message", error.message); }
});

document.addEventListener("click", async event => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const id = button.dataset.id;
  try {
    if (button.dataset.action === "appointment-status") {
      await apiRequest(`/api/appointments/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({status: button.dataset.status})
      });
      await loadAppointments();
    }
    if (button.dataset.action === "archive-record") {
      if (!window.confirm("Archive this record? It will be hidden from normal patient history but retained in the database.")) return;
      await apiRequest(`/api/records/${id}/archive`, {method: "POST"});
      await loadRecords();
    }
    if (button.dataset.action === "doctor-availability") {
      await apiRequest(`/api/admin/doctors/${id}/availability?is_available=${button.dataset.value}`, {method: "PATCH"});
      await loadAdminTables();
      await loadDoctors();
    }
    if (button.dataset.action === "facility-status") {
      await apiRequest(`/api/admin/facilities/${id}`, {
        method: "PATCH",
        body: JSON.stringify({is_available: button.dataset.value === "true"})
      });
      await loadAdminTables();
    }
    if (button.dataset.action === "assign-bed") {
      const bedId = Number(byId(`assign-bed-${id}`).value);
      if (!bedId) throw new Error("Enter an available bed ID from the bed inventory.");
      const result = await apiRequest(`/api/bed-requests/${id}/assign`, {
        method: "POST",
        body: JSON.stringify({bed_id: bedId})
      });
      window.alert(result.message);
      await loadOperations();
      if (role === "admin") await loadAdminSummary();
    }
    if (button.dataset.action === "bill-paid") {
      await apiRequest(`/api/billing/${id}/paid`, {method: "PATCH"});
      await loadOperations();
    }
    if (button.dataset.action === "discharge") {
      if (!window.confirm("Discharge this patient and release the bed?")) return;
      await apiRequest(`/api/admissions/${id}/discharge`, {method: "POST"});
      await loadOperations();
      if (role === "admin") await loadAdminSummary();
    }
    if (button.dataset.action === "account-status") {
      const nextStatus = button.dataset.value === "true";
      await apiRequest(`/api/admin/accounts/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({is_active: nextStatus})
      });
      await loadAdminTables();
    }
  } catch (error) {
    window.alert(error.message);
  }
});

function updateLiveClock() {
  const now = new Date();
  byId("live-time").textContent = now.toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true
  });
  byId("live-date").textContent = now.toLocaleDateString("en-IN", {
    weekday: "short", day: "2-digit", month: "short", year: "numeric"
  });
}

document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", () => {
    document.querySelectorAll(".nav-link").forEach(item => item.classList.remove("active"));
    link.classList.add("active");
  });
});

updateLiveClock();
window.setInterval(updateLiveClock, 1000);
showForRole();
loadAll();
