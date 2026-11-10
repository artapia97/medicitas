import { apiGet, apiPost, escapeHtml, formatName } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const STATUS_LABELS = {
    SCHEDULED: "Ocupado",
    CANCELLED: "Cancelada",
    ATTENDED: "Atendida",
    NO_SHOW: "No asistió",
};

const state = {
    doctors: [],
    patientResults: [],
    selectedPatient: null,
    selectedDoctorId: null,
    selectedDate: null,
    selectedSlot: null,
    slots: [],
    searchTimer: null,
};

const form = document.getElementById("appointment-form");
const patientSearch = document.getElementById("patient-search");
const patientResults = document.getElementById("patient-results");
const patientPicker = document.getElementById("patient-picker");
const patientChip = document.getElementById("patient-chip");
const patientChipLabel = document.getElementById("patient-chip-label");
const patientChipClear = document.getElementById("patient-chip-clear");
const doctorSelect = document.getElementById("doctor-select");
const dateInput = document.getElementById("date-input");
const slotsPlaceholder = document.getElementById("slots-placeholder");
const slotsSection = document.getElementById("slots-section");
const slotsEmpty = document.getElementById("slots-empty");
const slotGridMorning = document.getElementById("slot-grid-morning");
const slotGridAfternoon = document.getElementById("slot-grid-afternoon");
const reasonInput = document.getElementById("reason");
const submitBtn = document.getElementById("submit-btn");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");

function setFieldError(field, message) {
    const el = document.getElementById(`${field}-error`);
    if (!el) return;
    el.textContent = message || "";
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (group) group.classList.toggle("has-error", Boolean(message));
}

function clearAllErrors() {
    ["patient", "doctor", "date", "reason"].forEach((f) => setFieldError(f, ""));
    document.getElementById("slot-error").textContent = "";
    formError.hidden = true;
}

function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fmtDate(iso) {
    if (!iso) return "";
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
}

function isSunday(iso) {
    return new Date(`${iso}T00:00:00`).getDay() === 0;
}

// --- Datos iniciales ---
async function loadDoctors() {
    try {
        state.doctors = await apiGet("/api/doctors?is_active=true");
        doctorSelect.innerHTML =
            '<option value="">— Seleccione —</option>' +
            state.doctors
                .map(
                    (d) =>
                        `<option value="${d.id}">${escapeHtml(
                            formatName(d.first_name, d.last_name)
                        )} — ${escapeHtml(d.specialty_name)}</option>`
                )
                .join("");
    } catch (err) {
        formError.textContent = err.message || "No se pudieron cargar los médicos.";
        formError.hidden = false;
    }
}

// --- Paciente ---
function renderPatientResults(patients) {
    state.patientResults = patients;
    if (patients.length === 0) {
        patientResults.innerHTML = '<div class="patient-result empty">Sin coincidencias.</div>';
    } else {
        patientResults.innerHTML = patients
            .slice(0, 15)
            .map(
                (p) => `
                <div class="patient-result" data-patient-id="${p.id}">
                    ${escapeHtml(formatName(p.first_name, p.last_name))}
                    <small>${escapeHtml(p.national_id)}</small>
                </div>`
            )
            .join("");
        patientResults.querySelectorAll("[data-patient-id]").forEach((el) => {
            el.addEventListener("click", () => selectPatient(Number(el.dataset.patientId)));
        });
    }
    patientResults.hidden = false;
}

async function performPatientSearch() {
    const q = patientSearch.value.trim();
    if (!q) {
        patientResults.hidden = true;
        return;
    }
    try {
        const results = await apiGet(
            `/api/patients?search=${encodeURIComponent(q)}&is_active=true`
        );
        renderPatientResults(results);
    } catch {
        // Silencioso mientras el usuario escribe.
    }
}

function selectPatient(id) {
    const p = state.patientResults.find((x) => x.id === id);
    if (!p) return;
    state.selectedPatient = p;
    patientChipLabel.textContent = formatName(p.first_name, p.last_name);
    patientChip.hidden = false;
    patientPicker.hidden = true;
    patientResults.hidden = true;
    patientSearch.value = "";
    setFieldError("patient", "");
}

function clearPatientSelection() {
    state.selectedPatient = null;
    patientChip.hidden = true;
    patientPicker.hidden = false;
    patientSearch.focus();
}

patientSearch.addEventListener("input", () => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(performPatientSearch, 250);
});
patientSearch.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        performPatientSearch();
    }
});
patientChipClear.addEventListener("click", clearPatientSelection);

document.addEventListener("click", (e) => {
    if (
        !patientResults.hidden &&
        !patientResults.contains(e.target) &&
        e.target !== patientSearch
    ) {
        patientResults.hidden = true;
    }
});

// --- Turnos ---
function renderSlots() {
    if (!state.selectedDoctorId || !state.selectedDate) {
        slotsPlaceholder.hidden = false;
        slotsSection.hidden = true;
        return;
    }
    slotsPlaceholder.hidden = true;
    slotsSection.hidden = false;

    if (state.slots.length === 0) {
        slotsEmpty.textContent = isSunday(state.selectedDate)
            ? "El centro médico no atiende los domingos. Elija otra fecha."
            : "No hay turnos disponibles para esa fecha.";
        slotsEmpty.hidden = false;
        slotGridMorning.innerHTML = "";
        slotGridAfternoon.innerHTML = "";
        return;
    }
    slotsEmpty.hidden = true;

    const morning = state.slots.filter((s) => s.start_time < "13:00:00");
    const afternoon = state.slots.filter((s) => s.start_time >= "13:00:00");

    slotGridMorning.innerHTML = morning.map(renderSlotButton).join("");
    slotGridAfternoon.innerHTML = afternoon.map(renderSlotButton).join("");

    document.querySelectorAll(".slot[data-time]").forEach((btn) => {
        btn.addEventListener("click", () => selectSlot(btn.dataset.time));
    });
}

function renderSlotButton(slot) {
    const time = slot.start_time.slice(0, 5);
    const isSelected = state.selectedSlot === slot.start_time;
    let cls = "slot";
    let label = "";
    let disabled = false;

    if (isSelected) {
        cls += " selected";
        label = "Seleccionado";
    } else if (slot.available) {
        label = "Libre";
    } else if (slot.appointment_id) {
        cls += " is-occupied";
        label = STATUS_LABELS[slot.status] || "Ocupado";
        disabled = true;
    } else {
        cls += " is-past";
        label = "No disponible";
        disabled = true;
    }

    return `
        <button type="button" class="${cls}" data-time="${slot.start_time}"
                ${disabled ? "disabled" : ""}>
            <span class="slot-time">${time}</span>
            <span class="slot-meta">${escapeHtml(label)}</span>
        </button>`;
}

function selectSlot(time) {
    state.selectedSlot = time;
    document.getElementById("slot-error").textContent = "";
    renderSlots();
}

async function refreshSlots() {
    state.selectedSlot = null;
    state.slots = [];
    renderSlots();

    if (!state.selectedDoctorId || !state.selectedDate) return;
    if (state.selectedDate < todayIso()) {
        slotsPlaceholder.hidden = true;
        slotsSection.hidden = false;
        slotsEmpty.textContent = "La fecha seleccionada ya pasó.";
        slotsEmpty.hidden = false;
        slotGridMorning.innerHTML = "";
        slotGridAfternoon.innerHTML = "";
        return;
    }

    try {
        const url = `/api/doctors/${state.selectedDoctorId}/availability?date=${state.selectedDate}`;
        state.slots = await apiGet(url);
        renderSlots();
    } catch (err) {
        formError.textContent = err.message;
        formError.hidden = false;
    }
}

doctorSelect.addEventListener("change", () => {
    state.selectedDoctorId = doctorSelect.value ? Number(doctorSelect.value) : null;
    setFieldError("doctor", "");
    refreshSlots();
});

dateInput.addEventListener("change", () => {
    state.selectedDate = dateInput.value || null;
    setFieldError("date", "");
    refreshSlots();
});

// --- Submit ---
function validate() {
    clearAllErrors();
    let ok = true;

    if (!state.selectedPatient) {
        setFieldError("patient", "Seleccione un paciente.");
        ok = false;
    }
    if (!state.selectedDoctorId) {
        setFieldError("doctor", "Seleccione un médico.");
        ok = false;
    }
    if (!state.selectedDate) {
        setFieldError("date", "Seleccione una fecha.");
        ok = false;
    } else if (state.selectedDate < todayIso()) {
        setFieldError("date", "La fecha no puede ser pasada.");
        ok = false;
    }
    if (!state.selectedSlot) {
        document.getElementById("slot-error").textContent = "Seleccione un turno.";
        ok = false;
    }

    const reason = reasonInput.value.trim();
    if (!reason) {
        setFieldError("reason", "El motivo es obligatorio.");
        ok = false;
    } else if (reason.length > 500) {
        setFieldError("reason", "El motivo no puede exceder 500 caracteres.");
        ok = false;
    }

    return ok;
}

function showSuccess(appointment) {
    const patientName = formatName(appointment.patient_first_name, appointment.patient_last_name);
    const doctorName = formatName(appointment.doctor_first_name, appointment.doctor_last_name);
    const time = appointment.start_time.slice(0, 5);
    formSuccess.innerHTML = `
        Cita registrada: <strong>${escapeHtml(patientName)}</strong> con
        <strong>${escapeHtml(doctorName)}</strong> el ${fmtDate(appointment.date)} a las ${time}.
    `;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function resetForm() {
    state.selectedPatient = null;
    state.selectedDoctorId = null;
    state.selectedDate = null;
    state.selectedSlot = null;
    state.slots = [];
    patientSearch.value = "";
    patientResults.hidden = true;
    patientChip.hidden = true;
    patientPicker.hidden = false;
    doctorSelect.value = "";
    dateInput.value = "";
    reasonInput.value = "";
    renderSlots();
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formSuccess.hidden = true;

    if (!validate()) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Registrando...";

    try {
        const appointment = await apiPost("/api/appointments", {
            patient_id: state.selectedPatient.id,
            doctor_id: state.selectedDoctorId,
            date: state.selectedDate,
            start_time: state.selectedSlot,
            reason: reasonInput.value.trim(),
        });
        showSuccess(appointment);
        resetForm();
    } catch (err) {
        formError.textContent = err.message || "No se pudo registrar la cita.";
        formError.hidden = false;
        // El turno pudo haber quedado ocupado; refresca la grilla.
        refreshSlots();
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Registrar cita";
    }
});

// --- Inicio ---
(async () => {
    await loadDoctors();
    dateInput.min = todayIso();
})();