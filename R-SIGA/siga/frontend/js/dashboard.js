/* ===================================================================
   js/dashboard.js — Panel del alumno (dashboard.html).
   Pide a la API SUS calificaciones (el servidor lo reconoce por el token)
   y dibuja tabla, promedio general, buscador e historial.
   =================================================================== */

let calificaciones = [];   // materias del periodo activo
let historial = [];        // periodos anteriores

// Dibuja la tabla a partir de una lista (así el buscador reutiliza la función).
function mostrarCalificaciones(lista) {
  const cuerpo = document.getElementById("cuerpo-tabla");
  cuerpo.innerHTML = "";

  if (lista.length === 0) {
    const fila = document.createElement("tr");
    const celda = crearCelda("No hay materias que coincidan.");
    celda.colSpan = 5;
    fila.appendChild(celda);
    cuerpo.appendChild(fila);
    return;
  }

  for (const materia of lista) {
    const fila = document.createElement("tr");
    fila.appendChild(crearCelda(materia.materia));
    for (let i = 0; i < 3; i++) {                 // CÓMO ADAPTARLO: 3 = parciales por materia
      fila.appendChild(crearCelda(formatear(materia.parciales[i])));
    }
    const promedio = calcularPromedio(materia.parciales);
    const celdaPromedio = crearCelda(formatear(promedio));
    celdaPromedio.style.fontWeight = "700";
    if (promedio !== null && promedio < 6) {      // CÓMO ADAPTARLO: nota mínima aprobatoria
      celdaPromedio.classList.add("reprobado");
    }
    fila.appendChild(celdaPromedio);
    cuerpo.appendChild(fila);
  }
}

// El promedio general usa SIEMPRE la lista completa (aunque el buscador filtre).
function actualizarPromedioGeneral() {
  const promedios = calificaciones.map((m) => calcularPromedio(m.parciales));
  document.getElementById("promedio-general").textContent = formatear(calcularPromedio(promedios));
}

// Historial: periodos anteriores con el promedio final de cada materia.
function mostrarHistorial() {
  const contenedor = document.getElementById("lista-historial");
  contenedor.innerHTML = "";
  if (historial.length === 0) {
    contenedor.textContent = "Aún no tienes periodos anteriores.";
    return;
  }
  for (const periodo of historial) {
    const titulo = document.createElement("h3");
    titulo.textContent = "Periodo " + periodo.periodo;
    contenedor.appendChild(titulo);

    const lista = document.createElement("ul");
    for (const m of periodo.materias) {
      const item = document.createElement("li");
      item.textContent = m.materia + ": " + formatear(m.promedio);
      lista.appendChild(item);
    }
    contenedor.appendChild(lista);
  }
}

// Evento "input" del buscador: filtra mientras escribes.
function filtrarMaterias() {
  const texto = document.getElementById("buscador").value.toLowerCase().trim();
  mostrarCalificaciones(calificaciones.filter((m) => m.materia.toLowerCase().includes(texto)));
}

async function iniciarDashboard() {
  document.getElementById("usuario-actual").textContent = sessionStorage.getItem("nombre");
  document.getElementById("buscador").addEventListener("input", filtrarMaterias);
  document.getElementById("btn-cerrar-sesion").addEventListener("click", cerrarSesion);

  mostrarEstado("Cargando datos...", false);
  try {
    const datos = await peticionJSON("/alumno/calificaciones");
    calificaciones = datos.calificaciones;
    historial = datos.historial;
    mostrarEstado(datos.periodo_actual ? "Periodo actual: " + datos.periodo_actual : "", false);
    mostrarCalificaciones(calificaciones);
    actualizarPromedioGeneral();
    mostrarHistorial();
  } catch (error) {
    mostrarEstado(error.message, true);
  }
}

if (exigirRol(["alumno"])) {
  iniciarDashboard();
}
