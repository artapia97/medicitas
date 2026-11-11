import { apiGet, apiPatch, escapeHtml, formatName, fmtDate, fmtTime } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const STATUS_LABELS = {
    SCHEDULED: "Agendada",
    CANCELLED: "Cancelada",
    ATTENDED: "Atendida",
    NO_SHOW: "No asistió",
};

const state = {
    specialties: [],
    doctors: [],
    patientResults: [],
    selectedPatientId: null,
    appointments: [],
    editingNotesFor: null,
    searchTimer: null,
};

// Filtros
const filterSpecialty = document.getElementById("filter-specialty");
const filterDoctor = document.getElementById("filter-doctor");
const filterPatientSearch = document.getElementById("filter-patient-search");
const filterPatientResults = document.getElementById("filter-patient-results");
const filterPatientChip = document.getElementById("filter-patient-chip");
const filterPatientChipLabel = document.getElementById("filter-patient-chip-label");
const filterPatientClear = document.getElementById("filter-patient-clear");
const patientPicker = document.getElementById("patient-picker");
const filterDate = document.getElementById("filter-date");
const filterStatus = document.getElementById("filter-status");
const clearFiltersBtn = document.getElementById("clear-filters");

// Tabla y mensajes
const tbody = document.getElementById("appointments-tbody");
const tableWrap = document.getElementById("table-wrap");
const emptyMessage = document.getElementById("empty-message");
const pageError = document.getElementById("page-error");

// Modal de observaciones
const notesModal = document.getElementById("notes-modal");
const notesTextarea = document.getElementById("notes-textarea");
const notesError = document.getElementById("notes-error");
const notesSave = document.getElementById("notes-save");
const notesCancel = document.getElementById("notes-cancel");

// --- Helpers ---
function showPageError(msg) { pageError.textContent = msg; pageError.hidden = false; }
function clearPageError() { pageError.hidden = true; }

function startsAt(a) {
    return new Date(`${a.date}T${fmtTime(a.start_time)}:00`);
}
function hasStarted(a) {
    return new Date() >= startsAt(a);
}

// --- Carga inicial ---
async function loadSpecialties() {
    try {
        state.specialties = await apiGet("/api/specialties");
        filterSpecialty.innerHTML =
            '<option value="">Todas</option>' +
            state.specialties
                .map((s) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`)
                .join("");
    } catch (err) {
        showPageError(err.message);
    }
}

async function loadDoctors() {
    try {
        state.doctors = await apiGet("/api/doctors");
        renderDoctorOptions();
    } catch (err) {
        showPageError(err.message);
    }
}

function renderDoctorOptions() {
    const specId = filterSpecialty.value;
    const filtered = specId
        ? state.doctors.filter((d) => String(d.specialty_id) === specId)
        : state.doctors;
    const previous = filterDoctor.value;
    filterDoctor.innerHTML =
        '<option value="">Todos</option>' +
        filtered
            .map((d) => `<option value="${d.id}">${escapeHtml(formatName(d.first_name, d.last_name))}</option>`)
            .join("");
    if (previous && filtered.some((d) => String(d.id) === previous)) {
        filterDoctor.value = previous;
    }
}

async function loadAppointments() {
    clearPageError();
    const params = new URLSearchParams();
    if (filterSpecialty.value) params.set("specialty_id", filterSpecialty.value);
    if (filterDoctor.value) params.set("doctor_id", filterDoctor.value);
    if (state.selectedPatientId) params.set("patient_id", state.selectedPatientId);
    if (filterDate.value) params.set("date", filterDate.value);
    if (filterStatus.value) params.set("status", filterStatus.value);
    const q = params.toString();
    try {
        state.appointments = await apiGet(`/api/appointments${q ? "?" + q : ""}`);
        renderTable();
    } catch (err) {
        showPageError(err.message);
    }
}

// --- Tabla ---
function renderTable() {
    if (state.appointments.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = state.appointments.map((a) => {
        const statusBadge = `<span class="badge badge-${a.status}">${STATUS_LABELS[a.status] || a.status}</span>`;
        return `
            <tr>
                <td>${fmtDate(a.date)}</td>
                <td>${fmtTime(a.start_time)} – ${fmtTime(a.end_time)}</td>
                <td>${escapeHtml(formatName(a.patient_first_name, a.patient_last_name))}</td>
                <td>${escapeHtml(formatName(a.doctor_first_name, a.doctor_last_name))}</td>
                <td>${escapeHtml(a.specialty_name)}</td>
                <td>${escapeHtml(a.reason)}</td>
                <td>${statusBadge}</td>
                <td><div class="row-actions">${renderActions(a)}</div></td>
            </tr>
        `;
    }).join("");

    tbody.querySelectorAll("[data-action]").forEach((btn) => {
        btn.addEventListener("click", () =>
            handleAction(btn.dataset.action, Number(btn.dataset.id))
        );
    });
}

function renderActions(a) {
    const buttons = [];
    if (a.status === "SCHEDULED") {
        const started = hasStarted(a);
        const disabledAttr = started
            ? ""
            : ' disabled title="Disponible cuando llegue la hora de inicio"';
        buttons.push(`<button type="button" class="btn btn-sm btn-secondary" data-action="attended" data-id="${a.id}"${disabledAttr}>Atendida</button>`);
        buttons.push(`<button type="button" class="btn btn-sm btn-secondary" data-action="no_show" data-id="${a.id}"${disabledAttr}>No asistió</button>`);
        buttons.push(`<button type="button" class="btn btn-sm btn-danger" data-action="cancel" data-id="${a.id}">Cancelar</button>`);
    }
    buttons.push(`<button type="button" class="btn btn-sm btn-secondary" data-action="notes" data-id="${a.id}">Observaciones</button>`);
    return buttons.join("");
}

async function handleAction(action, id) {
    if (action === "cancel") {
        if (!confirm("¿Confirmar la cancelación de esta cita?")) return;
        await updateStatus(id, "CANCELLED");
    } else if (action === "attended") {
        await updateStatus(id, "ATTENDED");
    } else if (action === "no_show") {
        await updateStatus(id, "NO_SHOW");
    } else if (action === "notes") {
        const appointment = state.appointments.find((x) => x.id === id);
        if (appointment) openNotesModal(appointment);
    }
}

async function updateStatus(id, status) {
    clearPageError();
    try {
        await apiPatch(`/api/appointments/${id}`, { status });
        await loadAppointments();
    } catch (err) {
        showPageError(err.message);
    }
}

// --- Modal de observaciones ---
function openNotesModal(a) {
    state.editingNotesFor = a;
    notesTextarea.value = a.notes || "";
    notesError.hidden = true;
    notesModal.hidden = false;
    notesTextarea.focus();
}
function closeNotesModal() {
    state.editingNotesFor = null;
    notesModal.hidden = true;
}
async function saveNotes() {
    const a = state.editingNotesFor;
    if (!a) return;
    const text = notesTextarea.value.trim();
    notesSave.disabled = true;
    notesError.hidden = true;
    try {
        await apiPatch(`/api/appointments/${a.id}`, { notes: text || null });
        closeNotesModal();
        await loadAppointments();
    } catch (err) {
        notesError.textContent = err.message;
        notesError.hidden = false;
    } finally {
        notesSave.disabled = false;
    }
}

// --- Filtro de paciente con buscador ---
function renderPatientResults(patients) {
    state.patientResults = patients;
    if (patients.length === 0) {
        filterPatientResults.innerHTML = '<div class="patient-result empty">Sin coincidencias.</div>';
    } else {
        filterPatientResults.innerHTML = patients.slice(0, 15).map((p) => `
            <div class="patient-result" data-patient-id="${p.id}">
                ${escapeHtml(formatName(p.first_name, p.last_name))}
                <small>${escapeHtml(p.national_id)}</small>
            </div>
        `).join("");
        filterPatientResults.querySelectorAll("[data-patient-id]").forEach((el) => {
            el.addEventListener("click", () => selectPatient(Number(el.dataset.patientId)));
        });
    }
    filterPatientResults.hidden = false;
}

function selectPatient(id) {
    const p = state.patientResults.find((x) => x.id === id);
    if (!p) return;
    state.selectedPatientId = id;
    filterPatientChipLabel.textContent = formatName(p.first_name, p.last_name);
    filterPatientChip.hidden = false;
    patientPicker.hidden = true;
    filterPatientResults.hidden = true;
    filterPatientSearch.value = "";
    loadAppointments();
}

function clearPatientFilter() {
    state.selectedPatientId = null;
    filterPatientChip.hidden = true;
    patientPicker.hidden = false;
    filterPatientResults.hidden = true;
    loadAppointments();
}

filterPatientSearch.addEventListener("input", () => {
    clearTimeout(state.searchTimer);
    const q = filterPatientSearch.value.trim();
    if (!q) {
        filterPatientResults.hidden = true;
        return;
    }
    state.searchTimer = setTimeout(async () => {
        try {
            const results = await apiGet(`/api/patients?search=${encodeURIComponent(q)}`);
            renderPatientResults(results);
        } catch {
            // Silencioso: el usuario sigue escribiendo.
        }
    }, 250);
});

document.addEventListener("click", (e) => {
    if (
        !filterPatientResults.hidden &&
        !filterPatientResults.contains(e.target) &&
        e.target !== filterPatientSearch
    ) {
        filterPatientResults.hidden = true;
    }
});

filterPatientClear.addEventListener("click", clearPatientFilter);

// --- Otros filtros ---
filterSpecialty.addEventListener("change", () => {
    renderDoctorOptions();
    loadAppointments();
});
filterDoctor.addEventListener("change", loadAppointments);
filterDate.addEventListener("change", loadAppointments);
filterStatus.addEventListener("change", loadAppointments);

clearFiltersBtn.addEventListener("click", () => {
    filterSpecialty.value = "";
    filterDoctor.value = "";
    filterDate.value = "";
    filterStatus.value = "";
    state.selectedPatientId = null;
    filterPatientChip.hidden = true;
    patientPicker.hidden = false;
    filterPatientSearch.value = "";
    filterPatientResults.hidden = true;
    renderDoctorOptions();
    loadAppointments();
});

// --- Modal handlers ---
notesSave.addEventListener("click", saveNotes);
notesCancel.addEventListener("click", closeNotesModal);
notesModal.addEventListener("click", (e) => {
    if (e.target === notesModal) closeNotesModal();
});

// --- Inicio ---
(async () => {
    await loadSpecialties();
    await loadDoctors();
    await loadAppointments();
})();