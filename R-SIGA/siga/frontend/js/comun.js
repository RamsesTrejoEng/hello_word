/* ===================================================================
   js/comun.js — Funciones compartidas por TODAS las pantallas.
   Se carga primero (antes de login.js, dashboard.js o profesor.js).
   =================================================================== */

// Dirección de la API. "" = el mismo servidor que sirve esta página
// (así funciona cuando abres http://localhost:8000).
// CÓMO ADAPTARLO: si algún día separas frontend y backend, pon aquí
// "http://localhost:8000" (y agrega el origen del frontend en CORS_ORIGINS del .env).
const API_URL = "";


/* ---------- Sesión ---------- */

// Guarda lo que devolvió /auth/login. sessionStorage se borra al cerrar la pestaña.
function guardarSesion(datos) {
  sessionStorage.setItem("token", datos.access_token);
  sessionStorage.setItem("rol", datos.rol);
  sessionStorage.setItem("nombre", datos.nombre);
}

function cerrarSesion() {
  sessionStorage.clear();
  window.location.href = "login.html";
}

// Si no hay sesión o el rol no corresponde a esta pantalla, manda al login.
// OJO: esto es solo comodidad visual. La seguridad REAL está en el backend,
// que vuelve a verificar el token en cada petición.
function exigirRol(rolesPermitidos) {
  const token = sessionStorage.getItem("token");
  const rol = sessionStorage.getItem("rol");
  if (!token || !rolesPermitidos.includes(rol)) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}


/* ---------- Comunicación con la API ---------- */

// Envuelve fetch(): agrega el token, y convierte los errores del servidor en
// errores de JavaScript con un mensaje legible (error.message) y, si el
// servidor mandó una lista (como en el Excel), error.errores.
async function peticion(ruta, opciones = {}) {
  const cabeceras = { ...(opciones.headers || {}) };
  const token = sessionStorage.getItem("token");
  if (token) {
    cabeceras["Authorization"] = "Bearer " + token;
  }

  const respuesta = await fetch(API_URL + ruta, { ...opciones, headers: cabeceras });

  // 401 fuera del login = el token expiró o es inválido -> volver a entrar.
  if (respuesta.status === 401 && ruta !== "/auth/login") {
    cerrarSesion();
    throw new Error("Tu sesión expiró. Inicia sesión de nuevo.");
  }

  if (!respuesta.ok) {
    let mensaje = "Error " + respuesta.status;
    let errores = [];
    try {
      const cuerpo = await respuesta.json();
      if (typeof cuerpo.detail === "string") {
        mensaje = cuerpo.detail;                       // errores simples
      } else if (cuerpo.detail && cuerpo.detail.mensaje) {
        mensaje = cuerpo.detail.mensaje;               // errores del Excel
        errores = cuerpo.detail.errores || [];
      } else if (Array.isArray(cuerpo.detail)) {
        mensaje = "Hay datos inválidos en el formulario.";
      }
    } catch (e) { /* la respuesta no era JSON; se queda el mensaje genérico */ }
    const error = new Error(mensaje);
    error.errores = errores;
    throw error;
  }
  return respuesta;
}

// Atajo: hace la petición y devuelve el JSON ya convertido.
async function peticionJSON(ruta, opciones) {
  const respuesta = await peticion(ruta, opciones);
  return respuesta.json();
}


/* ---------- Cálculo y formato ---------- */

// Promedio ignorando huecos (null). Devuelve null si no hay números.
// CÓMO ADAPTARLO: para promedio ponderado, cambia la fórmula aquí.
function calcularPromedio(numeros) {
  const validos = numeros.filter((n) => typeof n === "number");
  if (validos.length === 0) {
    return null;
  }
  return validos.reduce((suma, n) => suma + n, 0) / validos.length;
}

// Número -> "8.5", o "--" si no hay dato.
function formatear(numero) {
  return numero === null || numero === undefined ? "--" : numero.toFixed(1);
}

// Crea una celda <td> con texto seguro (textContent evita inyección de HTML).
function crearCelda(texto) {
  const celda = document.createElement("td");
  celda.textContent = texto;
  return celda;
}

// Escribe un mensaje en <p id="estado">; esError lo pone en rojo.
function mostrarEstado(texto, esError) {
  const parrafo = document.getElementById("estado");
  parrafo.textContent = texto;
  parrafo.classList.toggle("error", Boolean(esError));
}
