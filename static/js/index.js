import { apiGet, escapeHtml, formatName, fmtTime, todayIso } from "./api.js";

const dateInput = document.getElementById("date-input");
const doctorSelect = document.getElementById("doctor-select");
const doctorFilterGroup = document.getElementById("doctor-filter-group");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("schedule-tbody");
const emptyMsg = document.getElementById("empty-msg");
const errorMsg = document.getElementById("error-msg");

let appointments = [];

function clearMessages() {
    errorMsg.hidden = true;
    emptyMsg.hidden = true;
}

function showError(message) {
    tableWrap.hidden = true;
    errorMsg.textContent = message;
    errorMsg.hidden = false;
}

function showEmpty(message) {
    tableWrap.hidden = true;
    emptyMsg.textContent = message;
    emptyMsg.hidden = false;
}

function doctorKey(a) {
    return `${a.doctor_first_name}|${a.doctor_last_name}`;
}

function renderDoctorOptions() {
    if (appointments.length === 0) {
        doctorFilterGroup.hidden = true;
        doctorSelect.innerHTML = '<option value="">Todos</option>';
        return;
    }
    doctorFilterGroup.hidden = false;

    const seen = new Map();
    for (const a of appointments) {
        const key = doctorKey(a);
        if (!seen.has(key)) {
            seen.set(key, formatName(a.doctor_first_name, a.doctor_last_name));
        }
    }
    const options = [...seen.entries()]
        .map(([key, label]) => ({ key, label }))
        .sort((a, b) => a.label.localeCompare(b.label, "es"));

    const previous = doctorSelect.value;
    doctorSelect.innerHTML =
        '<option value="">Todos</option>' +
        options
            .map(
                (o) =>
                    `<option value="${escapeHtml(o.key)}">${escapeHtml(o.label)}</option>`
            )
            .join("");

    if (previous && options.some((o) => o.key === previous)) {
        doctorSelect.value = previous;
    }
}

function renderTable() {
    const selected = doctorSelect.value;
    const filtered = selected
        ? appointments.filter((a) => doctorKey(a) === selected)
        : appointments;

    if (filtered.length === 0) {
        if (appointments.length === 0) {
            showEmpty("No hay citas registradas para esta fecha.");
        } else {
            showEmpty("No hay citas del médico seleccionado para esta fecha.");
        }
        return;
    }
    emptyMsg.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = filtered
        .map(
            (a) => `
            <tr>
                <td>${fmtTime(a.start_time)} – ${fmtTime(a.end_time)}</td>
                <td>${escapeHtml(formatName(a.doctor_first_name, a.doctor_last_name))}</td>
                <td>${escapeHtml(a.specialty_name)}</td>
                <td>${escapeHtml(formatName(a.patient_first_name, a.patient_last_name))}</td>
            </tr>`
        )
        .join("");
}

async function loadSchedule() {
    clearMessages();
    const dateStr = dateInput.value;
    if (!dateStr) {
        appointments = [];
        renderDoctorOptions();
        showEmpty("Seleccione una fecha para consultar la agenda.");
        return;
    }
    try {
        appointments = await apiGet(
            `/api/public-schedule?date=${encodeURIComponent(dateStr)}`
        );
    } catch (err) {
        appointments = [];
        renderDoctorOptions();
        showError(err.message || "No se pudo cargar la agenda.");
        return;
    }
    renderDoctorOptions();
    renderTable();
}

dateInput.addEventListener("change", loadSchedule);
doctorSelect.addEventListener("change", renderTable);

// --- Inicio ---
dateInput.value = todayIso();
loadSchedule();