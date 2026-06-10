function showAuth(mode) {
    const modal = document.getElementById("auth-modal");

    if (!modal) {
        console.error("auth-modal not found in HTML");
        return;
    }

    modal.style.display = "block";

    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

    if (!loginForm || !registerForm) {
        console.error("login or register form missing");
        return;
    }

    if (mode === "login") {
        loginForm.style.display = "block";
        registerForm.style.display = "none";
    } else {
        loginForm.style.display = "none";
        registerForm.style.display = "block";
    }
}