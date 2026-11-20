let selectedRole = "admin";
let patientMode = false;

const roleOptions = document.getElementById("role-options");
const loginHeading = document.getElementById("login-heading");
const loginSubheading = document.getElementById("login-subheading");
const registerArea = document.getElementById("register-area");
const employeeFields = document.getElementById("employee-fields");
const patientFields = document.getElementById("patient-fields");
const showRegister = document.getElementById("show-register");
const patientAccess = document.getElementById("patient-access");

function setRole(role) {
  selectedRole = role;
  patientMode = role === "patient";
  document.querySelectorAll(".role-option").forEach(button => {
    button.classList.toggle("selected", button.dataset.role === role);
  });

  roleOptions.classList.toggle("hidden", patientMode);
  loginHeading.textContent = patientMode ? "Patient access" : "Choose your workspace";
  loginSubheading.textContent = patientMode
    ? "Sign in to view your own hospital information."
    : "Select your hospital role to continue.";

  patientAccess.textContent = patientMode ? "Hospital employee sign in" : "Patient sign in / register";
  document.getElementById("access-caption").textContent = patientMode
    ? "Hospital team member?"
    : "Are you a patient?";

  showRegister.classList.toggle("hidden", role === "admin");
  showRegister.textContent = patientMode
    ? "New patient? Register here"
    : "Activate an invited employee account";
  employeeFields.classList.toggle("hidden", patientMode);
  patientFields.classList.toggle("hidden", !patientMode);
  document.getElementById("reg-age").required = patientMode;
  document.getElementById("employee-code").required = !patientMode;
  document.getElementById("register-title").textContent = patientMode
    ? "Create your patient account"
    : "Activate your invited employee account";
  document.getElementById("register-hint").textContent = patientMode
    ? "New patients can register directly using their Gmail address, name, age and a password. If the hospital has already created your patient profile, enter the registration code provided by the hospital."
    : "Your hospital administrator must create your employee profile first. Use the exact Gmail address and employee code provided.";
  document.querySelector('#register-form button[type="submit"]').textContent = patientMode
    ? "Create patient account"
    : "Activate employee account";
  registerArea.classList.add("hidden");
}

document.querySelectorAll(".role-option").forEach(button => {
  button.addEventListener("click", () => setRole(button.dataset.role));
});

patientAccess.addEventListener("click", () => {
  setRole(patientMode ? "admin" : "patient");
});

showRegister.addEventListener("click", () => {
  registerArea.classList.remove("hidden");
});

document.getElementById("hide-register").addEventListener("click", () => {
  registerArea.classList.add("hidden");
});

document.getElementById("login-form").addEventListener("submit", async event => {
  event.preventDefault();
  const message = document.getElementById("message");
  message.textContent = "Checking account...";
  message.className = "message";
  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
        role: selectedRole
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Sign in failed.");
    localStorage.setItem("hms_token", data.access_token);
    localStorage.setItem("hms_role", data.role);
    localStorage.setItem("hms_email", data.email);
    localStorage.setItem("hms_login_time", new Date().toISOString());
    window.location.href = "/dashboard";
  } catch (error) {
    message.textContent = error.message;
  }
});

document.getElementById("register-form").addEventListener("submit", async event => {
  event.preventDefault();
  const message = document.getElementById("reg-message");
  message.textContent = "Creating account...";
  message.className = "message";
  const payload = {
    account_type: selectedRole,
    full_name: document.getElementById("reg-name").value.trim(),
    email: document.getElementById("reg-email").value.trim(),
    password: document.getElementById("reg-password").value
  };

  if (selectedRole === "patient") {
    payload.age = Number(document.getElementById("reg-age").value);
    payload.patient_code = document.getElementById("patient-code").value.trim();
  } else {
    payload.employee_code = document.getElementById("employee-code").value.trim();
  }

  try {
    const response = await fetch("/api/auth/register", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Account creation failed.");
    message.textContent = data.message;
    message.classList.add("success-message");
    document.getElementById("email").value = payload.email;
    document.getElementById("password").value = "";
    registerArea.classList.add("hidden");
  } catch (error) {
    message.textContent = error.message;
  }
});
