import { apiGet, apiPost, apiPut, escapeHtml, formatName } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const form = document.getElementById("doctor-form");
const formTitle = document.getElementById("form-title");
const firstNameInput = document.getElementById("first_name");
const lastNameInput = document.getElementById("last_name");
const licenseInput = document.getElementById("license_number");
const phoneInput = document.getElementById("phone");
const emailInput = document.getElementById("email");
const specialtySelect = document.getElementById("specialty_id");
const isActiveGroup = document.getElementById("is-active-group");
const isActiveInput = document.getElementById("is_active");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const submitBtn = document.getElementById("submit-btn");
const cancelBtn = document.getElementById("cancel-btn");
const emptyMessage = document.getElementById("empty-message");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("doctors-tbody");
const filterSpecialty = document.getElementById("filter-specialty");
const filterActive = document.getElementById("filter-active");

let editingId = null;
let doctors = [];
let specialties = [];

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function clearAllFieldErrors() {
    ["first_name", "last_name", "license_number", "specialty_id", "phone", "email", "is_active"]
        .forEach((f) => setFieldError(f, ""));
}

function resetForm() {
    editingId = null;
    form.reset();
    clearAllFieldErrors();
    isActiveGroup.hidden = true;
    isActiveInput.checked = false;
    formTitle.textContent = "Nuevo médico";
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

    const first = firstNameInput.value.trim();
    if (!first) { setFieldError("first_name", "Los nombres son obligatorios."); ok = false; }
    else if (first.length > 100) { setFieldError("first_name", "Máximo 100 caracteres."); ok = false; }

    const last = lastNameInput.value.trim();
    if (!last) { setFieldError("last_name", "Los apellidos son obligatorios."); ok = false; }
    else if (last.length > 100) { setFieldError("last_name", "Máximo 100 caracteres."); ok = false; }

    const license = licenseInput.value.trim();
    if (!license) { setFieldError("license_number", "El registro es obligatorio."); ok = false; }
    else if (license.length > 50) { setFieldError("license_number", "Máximo 50 caracteres."); ok = false; }

    if (!specialtySelect.value) { setFieldError("specialty_id", "Seleccione una especialidad."); ok = false; }

    const phone = phoneInput.value.trim();
    if (phone.length > 20) { setFieldError("phone", "Máximo 20 caracteres."); ok = false; }

    const email = emailInput.value.trim();
    if (email.length > 150) { setFieldError("email", "Máximo 150 caracteres."); ok = false; }
    else if (email && !EMAIL_RE.test(email)) { setFieldError("email", "Formato de email inválido."); ok = false; }

    return ok;
}

function renderTable() {
    if (doctors.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = doctors
        .map((d) => {
            const stateBadge = d.is_active
                ? '<span class="badge badge-ATTENDED">Activo</span>'
                : '<span class="badge badge-CANCELLED">Inactivo</span>';
            return `
            <tr>
                <td>${escapeHtml(formatName(d.first_name, d.last_name))}</td>
                <td>${escapeHtml(d.license_number)}</td>
                <td>${escapeHtml(d.specialty_name)}</td>
                <td>${escapeHtml(d.phone || "")}</td>
                <td>${escapeHtml(d.email || "")}</td>
                <td>${stateBadge}</td>
                <td>
                    <button type="button" class="btn btn-sm btn-secondary"
                            data-edit-id="${d.id}">Editar</button>
                </td>
            </tr>`;
        })
        .join("");

    tbody.querySelectorAll("[data-edit-id]").forEach((btn) => {
        btn.addEventListener("click", () => startEdit(Number(btn.dataset.editId)));
    });
}

function startEdit(id) {
    const doctor = doctors.find((d) => d.id === id);
    if (!doctor) return;
    editingId = id;
    firstNameInput.value = doctor.first_name;
    lastNameInput.value = doctor.last_name;
    licenseInput.value = doctor.license_number;
    phoneInput.value = doctor.phone || "";
    emailInput.value = doctor.email || "";
    specialtySelect.value = String(doctor.specialty_id);
    isActiveInput.checked = doctor.is_active;
    isActiveGroup.hidden = false;
    clearAllFieldErrors();
    formError.hidden = true;
    formSuccess.hidden = true;
    formTitle.textContent = `Editar médico #${id}`;
    submitBtn.textContent = "Guardar";
    cancelBtn.hidden = false;
    firstNameInput.focus();
}

async function loadSpecialties() {
    try {
        specialties = await apiGet("/api/specialties");
        const optionsHtml = specialties
            .map((s) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`)
            .join("");
        specialtySelect.innerHTML = '<option value="">— Seleccione —</option>' + optionsHtml;
        filterSpecialty.innerHTML = '<option value="">Todas</option>' + optionsHtml;
    } catch (err) {
        showError(err.message || "No se pudieron cargar las especialidades.");
    }
}

async function loadDoctors() {
    const params = new URLSearchParams();
    if (filterSpecialty.value) params.set("specialty_id", filterSpecialty.value);
    if (filterActive.value) params.set("is_active", filterActive.value);
    const query = params.toString();
    try {
        doctors = await apiGet(`/api/doctors${query ? "?" + query : ""}`);
        renderTable();
    } catch (err) {
        showError(err.message || "No se pudieron cargar los médicos.");
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
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        license_number: licenseInput.value.trim(),
        phone: phoneInput.value.trim() || null,
        email: emailInput.value.trim() || null,
        specialty_id: Number(specialtySelect.value),
    };

    submitBtn.disabled = true;
    try {
        if (editingId === null) {
            await apiPost("/api/doctors", payload);
            showSuccess("Médico creado.");
        } else {
            payload.is_active = isActiveInput.checked;
            await apiPut(`/api/doctors/${editingId}`, payload);
            showSuccess("Médico actualizado.");
        }
        resetFormKeepMessage();
        await loadDoctors();
    } catch (err) {
        showError(err.message || "No se pudo guardar el médico.");
    } finally {
        submitBtn.disabled = false;
    }
});

cancelBtn.addEventListener("click", () => resetForm());
filterSpecialty.addEventListener("change", loadDoctors);
filterActive.addEventListener("change", loadDoctors);

(async () => {
    await loadSpecialties();
    await loadDoctors();
})();