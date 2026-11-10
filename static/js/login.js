import { apiPost, setToken } from "./api.js";

const form = document.getElementById("login-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const formError = document.getElementById("form-error");
const submitBtn = document.getElementById("submit-btn");

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function clearErrors() {
    setFieldError("username", "");
    setFieldError("password", "");
    formError.hidden = true;
    formError.textContent = "";
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    let valid = true;
    if (!username) {
        setFieldError("username", "Ingrese su usuario.");
        valid = false;
    }
    if (!password) {
        setFieldError("password", "Ingrese su contraseña.");
        valid = false;
    }
    if (!valid) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Ingresando...";

    try {
        const data = await apiPost(
            "/api/auth/login",
            { username, password },
            { redirectOn401: false }
        );
        setToken(data.access_token);
        window.location.replace("/admin/appointments.html");
    } catch (err) {
        formError.textContent = err.message || "No se pudo iniciar sesión.";
        formError.hidden = false;
        submitBtn.disabled = false;
        submitBtn.textContent = "Ingresar";
    }
});