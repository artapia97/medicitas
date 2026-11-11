import { apiGet, apiPost, apiPut, escapeHtml, formatName, fmtDate, todayIso } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const form = document.getElementById("patient-form");
const formTitle = document.getElementById("form-title");
const nationalIdInput = document.getElementById("national_id");
const birthDateInput = document.getElementById("birth_date");
const firstNameInput = document.getElementById("first_name");
const lastNameInput = document.getElementById("last_name");
const phoneInput = document.getElementById("phone");
const emailInput = document.getElementById("email");
const isActiveGroup = document.getElementById("is-active-group");
const isActiveInput = document.getElementById("is_active");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const submitBtn = document.getElementById("submit-btn");
const cancelBtn = document.getElementById("cancel-btn");
const emptyMessage = document.getElementById("empty-message");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("patients-tbody");
const searchInput = document.getElementById("search");
const filterActive = document.getElementById("filter-active");

let editingId = null;
let patients = [];

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function clearAllFieldErrors() {
    ["national_id", "birth_date", "first_name", "last_name", "phone", "email", "is_active"]
        .forEach((f) => setFieldError(f, ""));
}

function resetForm() {
    editingId = null;
    form.reset();
    clearAllFieldErrors();
    isActiveGroup.hidden = true;
    isActiveInput.checked = false;
    formTitle.textContent = "Nuevo paciente";
    submitBtn.textContent = "Crear";
    cancelBtn.hidden = true;
    formError.hidden = true;
    formSuccess.hidden = true;
}

function showError(message) {
    formError.textContent = message;
    formError.hidden = false;
    formSuccess.hidden = true;
}

function showSuccess(message) {
    formSuccess.textContent = message;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function validate() {
    clearAllFieldErrors();
    let ok = true;

    const nid = nationalIdInput.value.trim();
    if (!nid) { setFieldError("national_id", "La cédula es obligatoria."); ok = false; }
    else if (nid.length > 20) { setFieldError("national_id", "Máximo 20 caracteres."); ok = false; }

    const first = firstNameInput.value.trim();
    if (!first) { setFieldError("first_name", "Los nombres son obligatorios."); ok = false; }
    else if (first.length > 100) { setFieldError("first_name", "Máximo 100 caracteres."); ok = false; }

    const last = lastNameInput.value.trim();
    if (!last) { setFieldError("last_name", "Los apellidos son obligatorios."); ok = false; }
    else if (last.length > 100) { setFieldError("last_name", "Máximo 100 caracteres."); ok = false; }

    const phone = phoneInput.value.trim();
    if (!phone) { setFieldError("phone", "El teléfono es obligatorio."); ok = false; }
    else if (phone.length > 20) { setFieldError("phone", "Máximo 20 caracteres."); ok = false; }

    const email = emailInput.value.trim();
    if (email.length > 150) { setFieldError("email", "Máximo 150 caracteres."); ok = false; }
    else if (email && !EMAIL_RE.test(email)) { setFieldError("email", "Formato de email inválido."); ok = false; }

    const birth = birthDateInput.value;
    if (birth && birth > todayIso()) {
        setFieldError("birth_date", "La fecha de nacimiento no puede ser futura.");
        ok = false;
    }

    return ok;
}

function renderTable() {
    if (patients.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = patients
        .map((p) => {
            const stateBadge = p.is_active
                ? '<span class="badge badge-ATTENDED">Activo</span>'
                : '<span class="badge badge-CANCELLED">Inactivo</span>';
            return `
            <tr>
                <td>${escapeHtml(p.national_id)}</td>
                <td>${escapeHtml(formatName(p.first_name, p.last_name))}</td>
                <td>${escapeHtml(fmtDate(p.birth_date))}</td>
                <td>${escapeHtml(p.phone)}</td>
                <td>${escapeHtml(p.email || "")}</td>
                <td>${stateBadge}</td>
                <td>
                    <button type="button" class="btn btn-sm btn-secondary"
                            data-edit-id="${p.id}">Editar</button>
                </td>
            </tr>`;
        })
        .join("");

    tbody.querySelectorAll("[data-edit-id]").forEach((btn) => {
        btn.addEventListener("click", () => startEdit(Number(btn.dataset.editId)));
    });
}

function startEdit(id) {
    const patient = patients.find((p) => p.id === id);
    if (!patient) return;
    editingId = id;
    nationalIdInput.value = patient.national_id;
    birthDateInput.value = patient.birth_date || "";
    firstNameInput.value = patient.first_name;
    lastNameInput.value = patient.last_name;
    phoneInput.value = patient.phone;
    emailInput.value = patient.email || "";
    isActiveInput.checked = patient.is_active;
    isActiveGroup.hidden = false;
    clearAllFieldErrors();
    formError.hidden = true;
    formSuccess.hidden = true;
    formTitle.textContent = `Editar paciente #${id}`;
    submitBtn.textContent = "Guardar";
    cancelBtn.hidden = false;
    nationalIdInput.focus();
}

async function loadPatients() {
    const params = new URLSearchParams();
    const search = searchInput.value.trim();
    if (search) params.set("search", search);
    if (filterActive.value) params.set("is_active", filterActive.value);
    const query = params.toString();
    try {
        patients = await apiGet(`/api/patients${query ? "?" + query : ""}`);
        renderTable();
    } catch (err) {
        showError(err.message || "No se pudieron cargar los pacientes.");
    }
}

function resetFormKeepMessage() {
    const successText = formSuccess.textContent;
    const showSuccessMsg = !formSuccess.hidden;
    resetForm();
    if (showSuccessMsg) {
        formSuccess.textContent = successText;
        formSuccess.hidden = false;
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    formSuccess.hidden = true;

    if (!validate()) return;

    const payload = {
        national_id: nationalIdInput.value.trim(),
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        birth_date: birthDateInput.value || null,
        phone: phoneInput.value.trim(),
        email: emailInput.value.trim() || null,
    };

    submitBtn.disabled = true;
    try {
        if (editingId === null) {
            await apiPost("/api/patients", payload);
            showSuccess("Paciente creado.");
        } else {
            payload.is_active = isActiveInput.checked;
            await apiPut(`/api/patients/${editingId}`, payload);
            showSuccess("Paciente actualizado.");
        }
        resetFormKeepMessage();
        await loadPatients();
    } catch (err) {
        showError(err.message || "No se pudo guardar el paciente.");
    } finally {
        submitBtn.disabled = false;
    }
});

cancelBtn.addEventListener("click", () => resetForm());

let searchTimer = null;
searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadPatients, 250);
});
filterActive.addEventListener("change", loadPatients);

loadPatients();