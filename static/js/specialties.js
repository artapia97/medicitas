import { apiGet, apiPost, apiPut, escapeHtml } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const form = document.getElementById("specialty-form");
const formTitle = document.getElementById("form-title");
const nameInput = document.getElementById("name");
const descriptionInput = document.getElementById("description");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const submitBtn = document.getElementById("submit-btn");
const cancelBtn = document.getElementById("cancel-btn");
const emptyMessage = document.getElementById("empty-message");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("specialties-tbody");

let editingId = null;
let specialties = [];

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function resetForm() {
    editingId = null;
    form.reset();
    setFieldError("name", "");
    setFieldError("description", "");
    formTitle.textContent = "Nueva especialidad";
    submitBtn.textContent = "Crear";
    cancelBtn.hidden = true;
    formError.hidden = true;
    formSuccess.hidden = true;
}

function showSuccess(message) {
    formSuccess.textContent = message;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function showError(message) {
    formError.textContent = message;
    formError.hidden = false;
    formSuccess.hidden = true;
}

function validate() {
    let ok = true;
    setFieldError("name", "");
    setFieldError("description", "");

    const name = nameInput.value.trim();
    if (!name) {
        setFieldError("name", "El nombre es obligatorio.");
        ok = false;
    } else if (name.length > 100) {
        setFieldError("name", "El nombre no puede exceder 100 caracteres.");
        ok = false;
    }

    const description = descriptionInput.value.trim();
    if (description.length > 255) {
        setFieldError("description", "La descripción no puede exceder 255 caracteres.");
        ok = false;
    }
    return ok;
}

function renderTable() {
    if (specialties.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = specialties
        .map(
            (s) => `
        <tr>
            <td>${s.id}</td>
            <td>${escapeHtml(s.name)}</td>
            <td>${escapeHtml(s.description || "")}</td>
            <td>
                <button type="button" class="btn btn-sm btn-secondary"
                        data-edit-id="${s.id}">Editar</button>
            </td>
        </tr>`
        )
        .join("");

    tbody.querySelectorAll("[data-edit-id]").forEach((btn) => {
        btn.addEventListener("click", () => startEdit(Number(btn.dataset.editId)));
    });
}

function startEdit(id) {
    const specialty = specialties.find((s) => s.id === id);
    if (!specialty) return;
    editingId = id;
    nameInput.value = specialty.name;
    descriptionInput.value = specialty.description || "";
    setFieldError("name", "");
    setFieldError("description", "");
    formError.hidden = true;
    formSuccess.hidden = true;
    formTitle.textContent = `Editar especialidad #${id}`;
    submitBtn.textContent = "Guardar";
    cancelBtn.hidden = false;
    nameInput.focus();
}

async function loadSpecialties() {
    try {
        specialties = await apiGet("/api/specialties");
        renderTable();
    } catch (err) {
        showError(err.message || "No se pudieron cargar las especialidades.");
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    formSuccess.hidden = true;

    if (!validate()) return;

    const payload = {
        name: nameInput.value.trim(),
        description: descriptionInput.value.trim() || null,
    };

    submitBtn.disabled = true;
    try {
        if (editingId === null) {
            await apiPost("/api/specialties", payload);
            showSuccess("Especialidad creada.");
        } else {
            await apiPut(`/api/specialties/${editingId}`, payload);
            showSuccess("Especialidad actualizada.");
        }
        resetFormKeepMessage();
        await loadSpecialties();
    } catch (err) {
        showError(err.message || "No se pudo guardar la especialidad.");
    } finally {
        submitBtn.disabled = false;
    }
});

function resetFormKeepMessage() {
    const successText = formSuccess.textContent;
    const showSuccessMsg = !formSuccess.hidden;
    resetForm();
    if (showSuccessMsg) {
        formSuccess.textContent = successText;
        formSuccess.hidden = false;
    }
}

cancelBtn.addEventListener("click", () => {
    resetForm();
});

loadSpecialties();