// Auth guard + common admin navigation bar.
// Call initAdminPage() once at the top of each admin page script:
//   if (!initAdminPage()) throw new Error("Redirecting to login");

import { clearToken, getToken } from "./api.js";

const NAV_ITEMS = [
    { href: "/admin/appointments.html",     label: "Citas" },
    { href: "/admin/new-appointment.html",  label: "Nueva cita" },
    { href: "/admin/patients.html",         label: "Pacientes" },
    { href: "/admin/doctors.html",          label: "Médicos" },
    { href: "/admin/specialties.html",      label: "Especialidades" },
];

function buildNav() {
    const current = window.location.pathname;
    const nav = document.createElement("nav");
    nav.className = "admin-nav";

    const links = NAV_ITEMS.map((item) => {
        const cls = current === item.href ? "nav-link active" : "nav-link";
        return `<a class="${cls}" href="${item.href}">${item.label}</a>`;
    }).join("");

    nav.innerHTML = `
        <span class="nav-brand">MediCitas</span>
        <div class="nav-links">${links}</div>
        <button type="button" class="nav-logout" id="nav-logout">Cerrar sesión</button>
    `;

    nav.querySelector("#nav-logout").addEventListener("click", () => {
        clearToken();
        window.location.replace("/login.html");
    });

    return nav;
}

export function initAdminPage() {
    if (!getToken()) {
        window.location.replace("/login.html");
        return false;
    }
    document.body.prepend(buildNav());
    return true;
}