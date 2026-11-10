// Common API client and small helpers shared by all pages.

const TOKEN_KEY = "medicitas_token";

export function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    sessionStorage.removeItem(TOKEN_KEY);
}

async function request(method, path, body, options) {
    const opts = options || {};
    const redirectOn401 = opts.redirectOn401 !== false;

    const headers = {};
    if (body !== undefined) {
        headers["Content-Type"] = "application/json";
    }
    const token = getToken();
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    let response;
    try {
        response = await fetch(path, {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
    } catch {
        throw new Error("No se pudo conectar con el servidor.");
    }

    if (response.status === 401 && token && redirectOn401) {
        clearToken();
        window.location.replace("/login.html");
        throw new Error("Sesión expirada.");
    }

    const text = await response.text();
    let data = null;
    if (text) {
        try { data = JSON.parse(text); } catch { data = null; }
    }

    if (!response.ok) {
        const detail = data && data.detail ? String(data.detail) : `Error ${response.status}.`;
        throw new Error(detail);
    }
    return data;
}

export function apiGet(path, options) {
    return request("GET", path, undefined, options);
}
export function apiPost(path, body, options) {
    return request("POST", path, body, options);
}
export function apiPut(path, body, options) {
    return request("PUT", path, body, options);
}
export function apiPatch(path, body, options) {
    return request("PATCH", path, body, options);
}

export function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

// "Apellidos Nombres" (sección 12).
export function formatName(firstName, lastName) {
    return [lastName, firstName]
        .filter((part) => part && String(part).trim())
        .join(" ")
        .trim();
}