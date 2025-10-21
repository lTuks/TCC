const API = window.location.origin;
const tokenKey = "ar_jwt";

function isLoggedIn() {
  try { return !!localStorage.getItem(tokenKey); } catch { return false; }
}

function setAuthStatus() {
  const t = localStorage.getItem(tokenKey);
  const el = document.getElementById("auth_status");
  if (el) el.textContent = t ? "Autenticado" : "Não autenticado";
}

function updateAuthUI() {
  const logged = isLoggedIn();
  document.querySelectorAll('[data-auth="in"]').forEach(el => el.style.display = logged ? "" : "none");
  document.querySelectorAll('[data-auth="out"]').forEach(el => el.style.display = logged ? "none" : "");
}

window.updateAuthUI = updateAuthUI;

function notifyAuthChanged() {
  try { setAuthStatus(); } catch { }
  try { updateAuthUI(); } catch { }
  window.dispatchEvent(new Event("auth:changed"));
}

async function api(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  const t = localStorage.getItem(tokenKey);
  if (t) headers["Authorization"] = "Bearer " + t;
  const res = await fetch(API + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "Erro de API");
  }
  return res.json();
}

async function login() {
  const email = document.getElementById("login_email")?.value?.trim() ?? "";
  const password = document.getElementById("login_pass")?.value ?? "";
  const msg = document.getElementById("login_msg");
  if (msg) msg.textContent = "";
  try {
    const data = await api("/auth/login", "POST", { email, password });
    localStorage.setItem(tokenKey, data.access_token);
    notifyAuthChanged();
    window.location.href = "/tutor";
  } catch (e) {
    if (msg) msg.textContent = "Falha ao entrar: " + e.message;
  }
}

async function logout(redirectTo = "/ui") {
  try { await fetch(window.location.origin + "/auth/logout", { method: "POST" }); } catch { }
  try { localStorage.removeItem("ar_jwt"); } catch { }
  notifyAuthChanged();
  window.location.href = redirectTo;
}

async function registerUser() {
  const name = document.getElementById("reg_name")?.value?.trim() ?? "";
  const email = document.getElementById("reg_email")?.value?.trim() ?? "";
  const password = document.getElementById("reg_pass")?.value ?? "";
  const msg = document.getElementById("reg_msg");
  if (msg) msg.textContent = "";
  try {
    const data = await api("/auth/register", "POST", { name, email, password });
    localStorage.setItem(tokenKey, data.access_token);
    notifyAuthChanged();
    window.location.href = "/tutor";
  } catch (e) {
    if (msg) msg.textContent = "Falha ao cadastrar: " + e.message;
  }
}

async function uploadPdfTutor() {
  const inp = document.getElementById("pdf_file_tutor");
  const msg = document.getElementById("pdf_msg_tutor");
  const textArea = document.getElementById("input_text_tutor");
  if (msg) msg.textContent = "";

  if (!inp || !inp.files || !inp.files[0]) {
    if (msg) msg.textContent = "Selecione um arquivo PDF.";
    return;
  }

  const file = inp.files[0];
  const fd = new FormData();
  fd.append("file", file);

  const t = localStorage.getItem(tokenKey);
  const headers = {};
  if (t) headers["Authorization"] = "Bearer " + t;

  try {
    const res = await fetch(API + "/upload/pdf", {
      method: "POST",
      headers,
      body: fd
    });
    if (!res.ok) {
      const errText = await res.text();
      if (msg) msg.textContent = "Falha ao importar: " + errText;
      return;
    }
    const data = await res.json();
    if (textArea) textArea.value = data.text || "";
    if (msg) msg.textContent = `Importado: ${data.title} (${data.chars} caracteres). Documento #${data.document_id}`;
  } catch (e) {
    if (msg) msg.textContent = "Erro de rede: " + e.message;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  try { setAuthStatus(); } catch { }
  try { updateAuthUI(); } catch { }
  window.addEventListener("auth:changed", updateAuthUI);
});

window.login = login;
window.logout = logout;
window.registerUser = registerUser;
window.uploadPdfTutor = uploadPdfTutor;
