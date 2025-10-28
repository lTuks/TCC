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

let __loading = false;
let __loadingSince = 0;
let __minDelay = 400; // ms
const overlay = document.getElementById("loading_overlay");

function __reallyHide() {
  overlay?.classList.add("hidden");
  document.body.classList.remove("loading");
  __loading = false;
  document.querySelectorAll("button[data-disabled-by-loading], .btn[data-disabled-by-loading], a[data-disabled-by-loading]")
    .forEach(el => {
      el.removeAttribute("disabled");
      el.removeAttribute("aria-disabled");
      el.removeAttribute("data-disabled-by-loading");
      el.classList.remove("pointer-events-none");
    });
}

function showLoading(minMs = 400) {
  if (__loading) return;
  __loading = true;
  __loadingSince = performance.now();
  __minDelay = minMs || 0;

  overlay?.classList.remove("hidden");
  document.body.classList.add("loading");

  document.querySelectorAll("button, .btn, a[href]")
    .forEach(el => {
      if (el.tagName === "A") {
        const href = el.getAttribute("href") || "";
        if (href.startsWith("#") || href.startsWith("javascript:")) return;
      }
      if (!el.hasAttribute("disabled")) {
        el.setAttribute("disabled", "disabled");
        el.setAttribute("aria-disabled", "true");
        el.setAttribute("data-disabled-by-loading", "1");
        el.classList.add("pointer-events-none");
      }
    });
}

function hideLoading() {
  const elapsed = performance.now() - __loadingSince;
  if (elapsed < __minDelay) {
    setTimeout(hideLoading, __minDelay - elapsed);
    return;
  }
  __reallyHide();
}

document.addEventListener("submit", (evt) => {
  if (__loading) {
    evt.preventDefault();
    return;
  }
  showLoading(400);
}, true);

document.addEventListener("click", (evt) => {
  const el = evt.target.closest("a, button");
  if (!el) return;

  if (__loading) {
    evt.preventDefault();
    evt.stopPropagation();
    return;
  }

  if (el.tagName === "A") {
    const href = el.getAttribute("href");
    if (href && !href.startsWith("#") && !href.startsWith("javascript:")) {
      showLoading(400);
    }
  }
}, true);

async function withGlobalLoading(fn, minMs = 400) {
  showLoading(minMs);
  try {
    return await fn();
  } finally {
    hideLoading();
  }
}

window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.withGlobalLoading = withGlobalLoading;


async function api(path, method = "GET", body = null, { useLoading = true } = {}) {
  const run = async () => {
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
  };
  return useLoading ? withGlobalLoading(run) : run();
}


async function login() {
  const email = document.getElementById("login_email")?.value?.trim() ?? "";
  const password = document.getElementById("login_pass")?.value ?? "";
  const msg = document.getElementById("login_msg");
  if (msg) msg.textContent = "";

  try {
    const data = await api("/auth/login", "POST", { email, password }, { useLoading: true });
    localStorage.setItem(tokenKey, data.access_token);
    notifyAuthChanged();
    window.location.href = "/tutor";
  } catch (e) {
    hideLoading();
    if (msg) msg.textContent = "Falha ao entrar: " + e.message;
  }
}

async function logout(redirectTo = "/ui") {
  await withGlobalLoading(async () => {
    try { await fetch(window.location.origin + "/auth/logout", { method: "POST" }); } catch { }
    try { localStorage.removeItem(tokenKey); } catch { }
    notifyAuthChanged();
    window.location.href = redirectTo;
  });
}

async function registerUser() {
  const name = document.getElementById("reg_name")?.value?.trim() ?? "";
  const email = document.getElementById("reg_email")?.value?.trim() ?? "";
  const password = document.getElementById("reg_pass")?.value ?? "";
  const msg = document.getElementById("reg_msg");
  if (msg) msg.textContent = "";

  try {
    const data = await api("/auth/register", "POST", { name, email, password }, { useLoading: true });
    localStorage.setItem(tokenKey, data.access_token);
    notifyAuthChanged();
    window.location.href = "/tutor";
  } catch (e) {
    hideLoading();
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

  await withGlobalLoading(async () => {
    try {
      const res = await fetch(API + "/upload/pdf", { method: "POST", headers, body: fd });
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
  });
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