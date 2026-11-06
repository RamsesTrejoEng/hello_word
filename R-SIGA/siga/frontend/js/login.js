/* ===================================================================
   js/login.js — Pantalla de inicio de sesión (login.html).
   Envía usuario y contraseña a la API, guarda el token y redirige
   según el rol: alumno -> dashboard, profesor/admin -> panel docente.
   =================================================================== */

const formLogin = document.getElementById("form-login");

formLogin.addEventListener("submit", async (evento) => {
  evento.preventDefault();                       // evita recargar la página
  const mensaje = document.getElementById("mensaje-error");
  const boton = formLogin.querySelector("button");
  mensaje.textContent = "";
  boton.disabled = true;                         // evita doble clic mientras espera

  try {
    const datos = await peticionJSON("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        usuario: document.getElementById("usuario").value.trim(),
        password: document.getElementById("password").value,
      }),
    });
    guardarSesion(datos);
    window.location.href = datos.rol === "alumno" ? "dashboard.html" : "profesor.html";
  } catch (error) {
    mensaje.textContent = error.message;         // "Usuario o contraseña incorrectos."
  } finally {
    boton.disabled = false;
  }
});
