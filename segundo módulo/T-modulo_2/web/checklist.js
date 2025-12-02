// El objeto 'db' (Firestore) se define en el script del HTML
// y está disponible globalmente aquí.

// ==========================================================
// 1. FUNCIONES ASÍNCRONAS PARA FIREBASE (Guardar y Cargar)
// ==========================================================

/**
 * Carga todas las auditorías guardadas en Firestore.
 * @returns {Promise<Object>} Objeto con las auditorías indexadas por nombre de empresa.
 */
async function getAuditorias() {
    const auditorias = {};
    try {
        // Obtenemos todos los documentos de la colección 'auditorias'
        const snapshot = await db.collection("auditorias").get();
        snapshot.forEach((doc) => {
            const data = doc.data();
            // Usamos el ID de Firestore (que es el nombre de la empresa)
            auditorias[doc.id] = data;
        });
        return auditorias;
    } catch (e) {
        console.error("Error al cargar auditorías desde Firebase: ", e);
        // Si hay un error de conexión, devolvemos un objeto vacío para no romper la app
        return {};
    }
}

/**
 * Guarda o actualiza una auditoría en Firestore.
 * @param {string} nombreEmpresa - Nombre de la empresa (será el ID del documento).
 * @param {Object} data - Datos completos de la auditoría.
 */
async function saveAuditoria(nombreEmpresa, data) {
    try {
        // Guardamos el documento usando el nombre de la empresa como ID
        await db.collection("auditorias").doc(nombreEmpresa).set(data);
        return true;
    } catch (e) {
        console.error("Error al guardar auditoría en Firebase: ", e);
        alert(
            "Error al guardar datos en la nube. Revisa la consola y las reglas de Firebase."
        );
        return false;
    }
}

// ==========================================================
// 2. LÓGICA DE CARGA, RENDERIZADO Y ESTILOS
// ==========================================================

// Opciones disponibles para los SELECT dinámicos (AHORA CON CLASES CSS)
const FASES_OPCIONES = [
    { value: "Pendiente", text: "Pendiente", clase: "estado-pendiente" }, // Azul oscuro
    { value: "En Proceso", text: "En Proceso", clase: "estado-proceso" },   // Amarillo
    { value: "Auditado", text: "Auditado", clase: "estado-auditado" }       // Verde
];

const RESOLUCION_OPCIONES = [
    { value: "Pendiente", text: "Pendiente", clase: "resolucion-pendiente" }, // Azul oscuro
    { value: "No Apto", text: "No Apto", clase: "resolucion-noapto" },          // Rojo
    { value: "Apto", text: "Apto", clase: "resolucion-apto" },                  // Verde
];

/**
 * Función auxiliar para aplicar la clase de color según el valor seleccionado.
 * @param {HTMLElement} select - El elemento <select>
 * @param {Array<Object>} opciones - Array de opciones (FASES_OPCIONES o RESOLUCION_OPCIONES)
 */
function aplicarClase(select, opciones) {
    // 1. Elimina todas las clases de estado/resolución para limpiar
    opciones.forEach(op => select.classList.remove(op.clase));
    
    // 2. Busca la opción actual y aplica su clase de color
    const opcionActual = opciones.find(op => op.value === select.value);
    if (opcionActual) {
        select.classList.add(opcionActual.clase);
    }
}

/**
 * Configura los elementos <select> con las opciones predefinidas y añade lógica de color.
 */
function setupSelects() {
    const faseSelects = document.querySelectorAll(".fase-auditoria");
    const resolucionSelects = document.querySelectorAll(".resolucion");

    // Función auxiliar para rellenar un select
    const fillSelect = (select, opciones) => {
        select.innerHTML = ""; // Limpiar
        opciones.forEach((op) => {
            const option = document.createElement("option");
            option.value = op.value;
            option.textContent = op.text;
            select.appendChild(option);
        });
    };

    faseSelects.forEach((select) => {
        fillSelect(select, FASES_OPCIONES);
        
        // 1. Inicializar clase de color (por defecto será "pendiente")
        aplicarClase(select, FASES_OPCIONES);
        
        // 2. Evento para actualizar el color en el cambio
        select.addEventListener("change", (e) => {
            aplicarClase(e.target, FASES_OPCIONES);
            // Ya no se necesita setAttribute("data-fase"), el valor ya está en select.value
        });
    });

    resolucionSelects.forEach((select) => {
        fillSelect(select, RESOLUCION_OPCIONES);
        
        // 1. Inicializar clase de color (por defecto será "sin_resolver")
        aplicarClase(select, RESOLUCION_OPCIONES);
        
        // 2. Evento para actualizar el color en el cambio
        select.addEventListener("change", (e) => {
            aplicarClase(e.target, RESOLUCION_OPCIONES);
            // Ya no se necesita setAttribute("data-res")
        });
    });
}

/**
 * Carga la lista de empresas guardadas desde Firebase y llena el select.
 */
async function loadEmpresasList() {
    const cargarEmpresaSelect = document.getElementById("cargarEmpresa");
    const auditorias = await getAuditorias(); // Esperamos los datos de Firebase

    cargarEmpresaSelect.innerHTML =
        '<option value="">Selecciona una empresa guardada...</option>';
    let hasData = false;

    // Rellenamos el select con los nombres de las empresas
    for (const empresa in auditorias) {
        const option = document.createElement("option");
        option.value = empresa;
        // Mostramos el nombre de la empresa y la fecha de la auditoría
        option.textContent = `${empresa} (${auditorias[empresa].fecha_auditoria})`;
        cargarEmpresaSelect.appendChild(option);
        hasData = true;
    }

    cargarEmpresaSelect.disabled = !hasData;
}

/**
 * Carga una auditoría guardada y rellena el formulario.
 * @param {string} nombreEmpresa - El nombre de la empresa a cargar (ID del documento).
 */
async function cargarAuditoria(nombreEmpresa) {
    const auditorias = await getAuditorias();
    const data = auditorias[nombreEmpresa];
    const nombreEmpresaInput = document.getElementById("nombreEmpresa");

    if (!data || !data.respuestas) {
        alert("No se encontraron datos para esta auditoría.");
        return;
    }

    // 1. Rellenar el input de la empresa
    nombreEmpresaInput.value = nombreEmpresa;

    // 2. Rellenar las respuestas
    data.respuestas.forEach((respuestaGuardada) => {
        const li = document.querySelector(`li[data-id="${respuestaGuardada.id}"]`);
        if (li) {
            // Rellenar Fase
            const faseSelect = li.querySelector(".fase-auditoria");
            // Usamos FASES_OPCIONES para pasar la lista completa a aplicarClase
            const faseValor = respuestaGuardada.fase || "Pendiente";
            faseSelect.value = faseValor;
            aplicarClase(faseSelect, FASES_OPCIONES);

            // Rellenar Resolución
            const resolucionSelect = li.querySelector(".resolucion");
            const resolucionValor = respuestaGuardada.resolucion || "Sin Resolver";
            resolucionSelect.value = resolucionValor;
            aplicarClase(resolucionSelect, RESOLUCION_OPCIONES);

            // Rellenar Observaciones
            const textarea = li.querySelector("textarea");
            textarea.value = respuestaGuardada.observaciones || "";
        }
    });

    alert(`Auditoría de "${nombreEmpresa}" cargada correctamente.`);
}

// ==========================================================
// 3. EVENT LISTENERS Y LÓGICA PRINCIPAL (DOMContentLoaded)
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {
    const nombreEmpresaInput = document.getElementById("nombreEmpresa");
    const guardarBtn = document.getElementById("guardarBtn");
    const cargarEmpresaSelect = document.getElementById("cargarEmpresa");
    const checklistForm = document.getElementById("checklistForm");

    // --- Configuración Inicial ---
    setupSelects();
    // Cargamos la lista de empresas al inicio (es asíncrona)
    loadEmpresasList();

    // --- Evento de GUARDAR (ASÍNCRONO) ---
    guardarBtn.addEventListener("click", async () => {
        const nombreEmpresa = nombreEmpresaInput.value.trim();
        if (!nombreEmpresa) {
            alert("Por favor, ingresa el nombre de la empresa antes de guardar.");
            return;
        }

        const respuestas = [];
        const listItems = checklistForm.querySelectorAll("li");

        // Recolectar datos del formulario
        listItems.forEach((li) => {
            respuestas.push({
                id: li.getAttribute("data-id"),
                pregunta: li.querySelector(".pregunta").textContent.trim(),
                fase: li.querySelector(".fase-auditoria").value,
                resolucion: li.querySelector(".resolucion").value,
                observaciones: li.querySelector("textarea").value.trim(),
            });
        });

        const datosAuditoria = {
            fecha_auditoria: new Date().toLocaleDateString("es-ES"),
            respuestas: respuestas,
        };

        // Guardar en Firebase y esperar el resultado
        const success = await saveAuditoria(nombreEmpresa, datosAuditoria);

        if (success) {
            alert(`Auditoría de "${nombreEmpresa}" guardada en la nube con éxito.`);
            // Actualizar la lista de selección con el nuevo elemento
            await loadEmpresasList();
        }
    });

    // --- Evento de CARGAR ---
    cargarEmpresaSelect.addEventListener("change", (e) => {
        const selectedEmpresa = e.target.value;
        if (selectedEmpresa) {
            cargarAuditoria(selectedEmpresa);
        }
    });
});