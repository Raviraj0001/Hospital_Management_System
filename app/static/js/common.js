function getToken() {
  return localStorage.getItem("hms_token");
}

async function apiRequest(url, options = {}) {
  const headers = {...(options.headers || {})};
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (getToken()) {
    headers.Authorization = `Bearer ${getToken()}`;
  }

  const response = await fetch(url, {...options, headers});
  const data = await response.json().catch(() => ({}));

  if (response.status === 401) {
    localStorage.clear();
    window.location.href = "/";
    throw new Error("Your session has expired. Please sign in again.");
  }
  if (!response.ok) {
    throw new Error(data.detail || "The request could not be completed.");
  }
  return data;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);
}

function showMessage(id, message, success = false) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("success-message", success);
}
