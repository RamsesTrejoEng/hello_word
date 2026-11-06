/* ===================================================================
   js/profesor.js — Panel docente (profesor.html).
   Permite: elegir un grupo, ver sus calificaciones, descargar la plantilla
   de Excel y subir calificaciones. Los administradores también entran aquí.
   =================================================================== */

const selector = document.getElementById("selector-curso");

// Pinta la tabla de un grupo.
async function cargarTablaGrupo(idGrupo) {
  const datos = await peticionJSON(`/profesor/materias/${idGrupo}/calificaciones`);
  document.getElementById("titulo-curso").textContent = "Calificaciones: " + datos.curso;

  const cuerpo = document.getElementById("cuerpo-tabla");
  cuerpo.innerHTML = "";
  for (const alumno of datos.alumnos) {
    const fila = document.createElement("tr");
    fila.appendChild(crearCelda(alumno.matricula));
    fila.appendChild(crearCelda(alumno.nombre));
    for (let i = 0; i < 3; i++) {
      fila.appendChild(crearCelda(formatear(alumno.parciales[i])));
    }
    const celdaPromedio = crearCelda(formatear(alumno.promedio));
    celdaPromedio.style.fontWeight = "700";
    if (alumno.promedio !== null && alumno.promedio < 6) {
      celdaPromedio.classList.add("reprobado");
    }
    fila.appendChild(celdaPromedio);
    cuerpo.appendChild(fila);
  }
}

// Llena el selector con los grupos del periodo activo.
async function cargarGrupos() {
  const grupos = await peticionJSON("/profesor/materias");
  selector.innerHTML = "";
  if (grupos.length === 0) {
    mostrarEstado("No tienes grupos asignados en el periodo activo.", false);
    return;
  }
  for (const g of grupos) {
    const opcion = document.createElement("option");
    opcion.value = g.id;
    opcion.textContent = `${g.materia} (${g.periodo}) · ${g.alumnos} alumnos`;
    selector.appendChild(opcion);
  }
  await cargarTablaGrupo(selector.value);
}

// Descarga la plantilla: hay que pedirla con fetch (lleva el token) y
// convertirla en un archivo descargable con un enlace temporal.
async function descargarPlantilla() {
  try {
    const respuesta = await peticion("/profesor/plantilla");
    const blob = await respuesta.blob();
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = "plantilla_calificaciones.xlsx";
    enlace.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    mostrarEstado(error.message, true);
  }
}

// Sube el Excel. FormData arma el envío de archivo; NO se pone Content-Type
// a mano porque el navegador lo calcula (incluye un "boundary" necesario).
async function subirExcel(evento) {
  evento.preventDefault();
  const resultado = document.getElementById("resultado");
  const listaErrores = document.getElementById("lista-errores");
  resultado.textContent = "";
  resultado.classList.remove("error");
  listaErrores.innerHTML = "";

  const archivo = document.getElementById("archivo").files[0];
  if (!archivo || !selector.value) {
    return;
  }
  const formulario = new FormData();
  formulario.append("archivo", archivo);

  try {
    const datos = await peticionJSON(`/profesor/materias/${selector.value}/excel`, {
      method: "POST",
      body: formulario,
    });
    resultado.textContent = datos.mensaje;
    await cargarTablaGrupo(selector.value);       // refresca la tabla con lo nuevo
  } catch (error) {
    resultado.textContent = error.message;
    resultado.classList.add("error");
    for (const texto of error.errores || []) {    // una línea por error del Excel
      const item = document.createElement("li");
      item.textContent = texto;
      listaErrores.appendChild(item);
    }
  }
}

async function iniciarPanel() {
  document.getElementById("usuario-actual").textContent = sessionStorage.getItem("nombre");
  document.getElementById("btn-cerrar-sesion").addEventListener("click", cerrarSesion);
  document.getElementById("btn-plantilla").addEventListener("click", descargarPlantilla);
  document.getElementById("form-excel").addEventListener("submit", subirExcel);
  selector.addEventListener("change", () => cargarTablaGrupo(selector.value));

  if (sessionStorage.getItem("rol") === "admin") {
    document.getElementById("enlace-admin").hidden = false;
  }
  try {
    await cargarGrupos();
  } catch (error) {
    mostrarEstado(error.message, true);
  }
}

if (exigirRol(["profesor", "admin"])) {
  iniciarPanel();
}
