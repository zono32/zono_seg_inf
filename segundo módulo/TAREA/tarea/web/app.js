let rutaArchivoRAR = null;
const btnIniciar = document.getElementById('btn-iniciar');
const btnCancelar = document.getElementById('btn-cancelar');

document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('drop-area');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        let dt = e.dataTransfer;
        let files = dt.files;

        if (files.length > 0) {
            // SOLUCIÓN: Usamos el nombre del archivo.
            rutaArchivoRAR = files[0].name; 
            
            document.getElementById('archivo-seleccionado').innerText = `Archivo Cargado: ${rutaArchivoRAR} (¡Cópialo a la carpeta tarea_2!)`;
            btnIniciar.disabled = false;
            
        } else {
             rutaArchivoRAR = null; 
             document.getElementById('archivo-seleccionado').innerText = `Error: No se detectó archivo.`;
             btnIniciar.disabled = true;
        }
    }
});

// Función llamada por el botón "Iniciar Ataque"
function iniciarCrackeo() {
    if (rutaArchivoRAR) {
        
        // Habilitar y deshabilitar botones
        btnIniciar.disabled = true;
        btnCancelar.disabled = false;
        btnIniciar.innerText = "PROCESANDO... (Revisa la Salida)";

        document.getElementById('resultado-output').innerText = "Iniciando proceso completo (Extracción de Hash + Crackeo)...";
        
        // Llama a la función de Python
        eel.iniciar_proceso_completo(rutaArchivoRAR);
    } else {
        alert("Por favor, arrastra un archivo .rar primero a la zona indicada.");
    }
}

// NUEVA FUNCIÓN: Llama a Python para detener el proceso
function cancelarCrackeo() {
    btnCancelar.disabled = true; // Deshabilita de inmediato para evitar clics múltiples
    btnCancelar.innerText = "CANCELANDO...";
    eel.stop_cracking()((success) => {
        // La función report_status se encargará de actualizar el estado final
        if(success) {
            // Si la señal fue enviada con éxito, report_status se encargará de reestablecer los botones
        } else {
            // Si el proceso ya había terminado (raro, pero posible), reestablece los botones
            resetBotones();
        }
    });
}

// Función para reestablecer los botones al estado inicial (llamada al finalizar o cancelar)
function resetBotones() {
    btnIniciar.disabled = false;
    btnCancelar.disabled = true;
    btnIniciar.innerText = "1. Iniciar Ataque con RockYou.txt";
    btnCancelar.innerText = "2. Cancelar Proceso";
}


// Función expuesta por Python para enviar actualizaciones de estado al HTML
eel.expose(report_status);
function report_status(mensaje) {
    const output = document.getElementById('resultado-output');
    
    // Si la operación ha finalizado (éxito, fracaso o cancelación)
    if (mensaje.includes("CONTRASENA ENCONTRADA") || mensaje.includes("ERROR") || mensaje.includes("Ataque de diccionario completado") || mensaje.includes("Proceso detenido")) {
        
        output.innerText += "\n\n" + mensaje;
        resetBotones(); // Reestablece los botones al estado inicial
        
    } else {
        // Añade el mensaje de progreso
        output.innerText += "\n" + mensaje;
    }
    
    output.scrollTop = output.scrollHeight;
}