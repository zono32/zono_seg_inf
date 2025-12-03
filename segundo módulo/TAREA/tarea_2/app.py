import os
import subprocess
import threading
import json
import tempfile
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
from time import sleep

# --- CONFIGURACIÓN DE RUTAS ---
# Esta ruta debe apuntar DIRECTAMENTE a la carpeta 'run' que contiene
# 'john.exe', 'rar2john.exe' y 'rockyou.txt'.
RUTA_BASE_JOHN = "./jhon/john-1.9.0-jumbo-1-win64/run"
# -------------------------------------------------------------------------

# Resolvemos la ruta relativa a absoluta para asegurar que John la encuentre
ABSOLUTE_JTR_DIR = os.path.abspath(RUTA_BASE_JOHN)

JTR_PATH = os.path.join(ABSOLUTE_JTR_DIR, "john.exe")
RAR2JOHN_PATH = os.path.join(ABSOLUTE_JTR_DIR, "rar2john.exe")
DICTIONARY_PATH_FULL = os.path.join(ABSOLUTE_JTR_DIR, "rockyou.txt")
DICTIONARY_PATH_TEMP = os.path.join(tempfile.gettempdir(), "temp_passwords_web.txt") 


app = Flask(__name__)
# Permitir archivos RAR de hasta 16 MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Estado global para almacenar resultados y evitar que el servidor se congele
crack_jobs = {} # {job_id: {'status': 'pending/running/finished', 'password': None, 'log': []}}

def create_temp_dictionary(temp_file_path):
    """Crea un diccionario temporal con contraseñas muy comunes para pruebas rápidas."""
    # Incluimos '418' para asegurar el éxito en el modo rápido (quick).
    common_passwords = ["password", "123456", "qwerty", "12345678", "test", "321", "examen", "modulo", "seguridad", "100100", "418"] 
    try:
        with open(temp_file_path, 'w') as f:
            f.write('\n'.join(common_passwords))
        return True
    except Exception:
        return False

def log_message(job_id, message, tag='info'):
    """Agrega un mensaje al registro del trabajo."""
    if job_id in crack_jobs:
        crack_jobs[job_id]['log'].append({'message': message, 'tag': tag})

def extract_hash(rar_file_path, output_hash_file, job_id):
    """Ejecuta rar2john para extraer el hash."""
    log_message(job_id, f"[1/3] Ejecutando rar2john en {os.path.basename(rar_file_path)}...")
    
    try:
        # Usamos comillas dobles para manejar espacios en las rutas
        command = f'"{RAR2JOHN_PATH}" "{rar_file_path}"'
        
        process = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True,
            text=True
        )
        
        with open(output_hash_file, 'w') as f:
            f.write(process.stdout)

        log_message(job_id, f"[2/3] Hash extraído y guardado en {os.path.basename(output_hash_file)}.", 'success')
        return True
    except subprocess.CalledProcessError as e:
        # Captura errores específicos de rar2john, como "No password protected files found"
        log_message(job_id, f"❌ Error rar2john: {e.stderr.strip()}", 'error')
        return False
    except FileNotFoundError:
        log_message(job_id, f"❌ Error: Ejecutable no encontrado: '{RAR2JOHN_PATH}'. Revise la configuración de ruta.", 'error')
        return False

def crack_hash_thread(rar_file_path, dictionary_path, mode, job_id):
    """
    Función que se ejecuta en un hilo separado para crackear el hash.
    """
    hash_output_name = rar_file_path + '_hash.txt'
    session_name = f"web_session_{job_id}"
    
    try:
        # PASO 1 y 2: Extraer hash
        if not extract_hash(rar_file_path, hash_output_name, job_id):
            crack_jobs[job_id]['status'] = 'finished'
            return
            
        # --- Lógica de Comando de Crackeo ---
        command_crack = None
        
        # Opciones base para todos los ataques con John
        # **IMPORTANTE**: Usamos --remove=abort para forzar a John a empezar de cero si encuentra un hash ya crackeado en el archivo de pot.
        john_base_options = f'--format=rar --noconfig --session={session_name} --force-session --remove=abort'
        
        if mode == 'quick':
            attack_type = f"rápido con {os.path.basename(dictionary_path)}"
            command_crack = f'"{JTR_PATH}" {john_base_options} --wordlist="{dictionary_path}" "{hash_output_name}"'
        elif mode == 'full':
            attack_type = f"completo con {os.path.basename(DICTIONARY_PATH_FULL)}"
            command_crack = f'"{JTR_PATH}" {john_base_options} --wordlist="{DICTIONARY_PATH_FULL}" "{hash_output_name}"'
        elif mode == 'bruteforce':
            attack_type = "fuerza bruta (incremental:all)"
            command_crack = f'"{JTR_PATH}" {john_base_options} --incremental:all "{hash_output_name}"'
        elif mode == 'numeric_mask':
             # Solución específica para la contraseña de 3 dígitos
            attack_type = "por máscara (3 dígitos: ?d?d?d)"
            command_crack = f'"{JTR_PATH}" {john_base_options} --mask="?d?d?d" "{hash_output_name}"'
        else:
             log_message(job_id, "❌ Error: Modo de ataque no reconocido.", 'error')
             crack_jobs[job_id]['status'] = 'finished'
             return
        # --- Fin Lógica de Comando de Crackeo ---
        
        log_message(job_id, f"\n[3/3] Iniciando ataque {attack_type}...", 'info')
        log_message(job_id, "--- ATAQUE EN CURSO. ESPERANDO RESULTADOS ---", 'info')
        
        # Ejecutar el comando de crackeo
        subprocess.run(
            command_crack,
            shell=True,
            check=False, 
            capture_output=True
        )
        
        # Comando de Mostrar (para obtener la contraseña encontrada)
        command_show = f'"{JTR_PATH}" --show --session={session_name} "{hash_output_name}"'
        
        # IMPORTANTE: check=False para evitar el "exit status 1" de John cuando no encuentra nada.
        result = subprocess.run(
            command_show,
            shell=True,
            capture_output=True,
            text=True,
            check=False 
        )

        # DEBUG interno: mostramos la salida completa de John --show
        print(f"[DEBUG JTR SHOW OUTPUT]:\n{result.stdout.strip()}")

        # Parsear la salida de John --show
        password = None
        output_lines = result.stdout.strip().split('\n')
        
        for line in output_lines:
            # Buscamos la línea que contiene el hash y la contraseña (formato: hash:contraseña)
            if ":" in line and not line.endswith(':'): 
                parts = line.split(':')
                # La contraseña está en la segunda parte, y eliminamos cualquier espacio o conteo.
                if len(parts) >= 2 and parts[1].strip():
                    # Solo tomamos la contraseña, ignorando el posible " (1 cracked)" o similar.
                    password = parts[1].split(' ')[0] 
                    break
        
        if password and password != f'{hash_output_name}': # Evitamos el caso donde John no encuentra nada y repite el nombre del archivo
            crack_jobs[job_id]['password'] = password
            log_message(job_id, f"🎉 ÉXITO: Contraseña encontrada: {password}", 'result')
        else:
            log_message(job_id, "😔 FALLO: Contraseña no encontrada con el ataque seleccionado.", 'error')


    except Exception as e:
        log_message(job_id, f"❌ Error inesperado durante el crackeo (General): {str(e)}", 'error')
    finally:
        # Limpieza (incluimos el archivo de sesión .rec)
        if os.path.exists(rar_file_path):
            os.remove(rar_file_path)
        if os.path.exists(hash_output_name):
            os.remove(hash_output_name)
            
        # Limpiamos el archivo de sesión de John
        session_file = os.path.join(ABSOLUTE_JTR_DIR, session_name + '.rec')
        if os.path.exists(session_file):
            os.remove(session_file)
            
        if mode == 'quick' and os.path.exists(DICTIONARY_PATH_TEMP):
            os.remove(DICTIONARY_PATH_TEMP)
            
        crack_jobs[job_id]['status'] = 'finished'
        log_message(job_id, "\n[INFO] Proceso finalizado y archivos temporales eliminados.", 'info')

@app.route('/crack', methods=['POST'])
def start_crack():
    """Ruta para iniciar el proceso de crackeo."""
    if 'rar_file' not in request.files:
        return jsonify({'error': 'No se encontró el archivo RAR.'}), 400
    
    rar_file = request.files['rar_file']
    # El valor por defecto es 'numeric_mask' ya que ahora está checked
    mode = request.form.get('mode', 'numeric_mask') 
    
    # DEBUG: Logueamos el modo que recibió Flask
    print(f"[DEBUG FLASK] Modo de ataque recibido: {mode}")

    if rar_file.filename == '':
        return jsonify({'error': 'Nombre de archivo no válido.'}), 400
    
    if rar_file and rar_file.filename.endswith('.rar'):
        try:
            filename = secure_filename(rar_file.filename)
            job_id = os.urandom(8).hex()
            rar_file_path = os.path.join(app.config['UPLOAD_FOLDER'], job_id + "_" + filename)
            rar_file.save(rar_file_path)

            crack_jobs[job_id] = {'status': 'running', 'password': None, 'log': []}
            
            dictionary_to_use = None
            if mode == 'quick':
                if not create_temp_dictionary(DICTIONARY_PATH_TEMP):
                    return jsonify({'error': 'Error al crear diccionario temporal.'}), 500
                dictionary_to_use = DICTIONARY_PATH_TEMP
            elif mode == 'full':
                dictionary_to_use = DICTIONARY_PATH_FULL 
            # 'bruteforce' y 'numeric_mask' no usan diccionario

            
            thread = threading.Thread(target=crack_hash_thread, args=(rar_file_path, dictionary_to_use, mode, job_id))
            thread.start()
            
            return jsonify({'job_id': job_id, 'message': 'Crackeo iniciado. Use /status para seguir el progreso.'}), 202
        
        except Exception as e:
            return jsonify({'error': f'Error al guardar o procesar el archivo: {str(e)}'}), 500

    return jsonify({'error': 'Formato de archivo no soportado. Debe ser .rar'}), 400

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Ruta para obtener el estado actual y el log del trabajo."""
    job = crack_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'ID de trabajo no encontrado.'}), 404
    
    return jsonify(job)

@app.route('/', methods=['GET'])
def index():
    """Sirve el frontend HTML."""
    return RENDER_HTML

# Pre-carga del HTML para que Flask lo sirva.
RENDER_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crackeador RAR Web (John The Ripper)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
        .log-area { max-height: 400px; overflow-y: auto; background: #1f2937; padding: 1rem; }
        /* Colores para el log */
        .info { color: #60a5fa; }
        .success { color: #10b981; }
        .error { color: #ef4444; }
        .result { color: #facc15; font-weight: bold; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white p-8 rounded-xl shadow-2xl w-full max-w-4xl">
        <h1 class="text-3xl font-bold text-gray-800 mb-6 text-center">
            🔒 Crackeador RAR Web (John The Ripper)
        </h1>
        <p class="text-sm text-gray-600 mb-6 text-center">
            Interfaz Web para el Módulo de Seguridad Informática. El proceso se ejecuta en el servidor local (tu PC).
        </p>

        <!-- Sección de Carga de Archivo -->
        <div class="mb-6 p-4 border border-gray-200 rounded-lg">
            <h2 class="text-xl font-semibold text-gray-700 mb-3">1. Seleccionar Archivo y Modo</h2>

            <input type="file" id="rarFile" accept=".rar" class="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-full file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100 mb-4 cursor-pointer"
            >

            <!-- Modos de Ataque -->
            <div class="flex flex-col space-y-2 mt-4">
                <span class="font-medium text-gray-700">Modo de Ataque:</span>
                
                <label class="inline-flex items-center">
                    <input type="radio" name="attackMode" value="quick" class="form-radio text-green-600 h-4 w-4">
                    <span class="ml-2 text-gray-700 text-sm">Rápido (Prueba - Diccionario de 10 palabras + "418")</span>
                </label>
                
                <label class="inline-flex items-center">
                    <input type="radio" name="attackMode" value="full" class="form-radio text-red-600 h-4 w-4">
                    <span class="ml-2 text-gray-700 text-sm">Diccionario Completo (rockyou.txt - LENTO)</span>
                </label>
                
                <label class="inline-flex items-center">
                    <!-- Es la opción checked por defecto -->
                    <input type="radio" name="attackMode" value="numeric_mask" checked class="form-radio text-purple-600 h-4 w-4">
                    <span class="ml-2 text-gray-700 text-sm font-bold">🎯 ATAQUE POR MÁSCARA (3 Dígitos: 000 a 999 - ¡ÓPTIMO PARA '418'!)</span>
                </label>

                <label class="inline-flex items-center">
                    <input type="radio" name="attackMode" value="bruteforce" class="form-radio text-indigo-600 h-4 w-4">
                    <span class="ml-2 text-gray-700 text-sm">Fuerza Bruta (Incremental:All - MUY LENTO)</span>
                </label>
                
            </div>
        </div>

        <!-- Botón de Crackeo -->
        <button id="crackButton" onclick="startCrack()" 
                class="w-full bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-4 rounded-lg 
                       transition duration-300 shadow-md disabled:bg-gray-400">
            Iniciar Crackeo
        </button>

        <div id="loadingIndicator" class="mt-4 text-center hidden">
            <div class="animate-spin inline-block w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-600">Procesando... Esperando que John termine.</p>
        </div>

        <!-- Sección de Resultado -->
        <div class="mt-8">
            <h2 class="text-xl font-semibold text-gray-700 mb-3">2. Contraseña Encontrada</h2>
            <div id="resultBox" class="bg-gray-50 p-4 rounded-lg border-2 border-dashed border-gray-300 text-center">
                <span id="passwordResult" class="text-3xl font-mono text-gray-500">
                    N/A
                </span>
            </div>
        </div>

        <!-- Sección de Log -->
        <div class="mt-8">
            <h2 class="text-xl font-semibold text-gray-700 mb-3">3. Log de Operaciones</h2>
            <div id="logArea" class="log-area rounded-lg text-white">
                <p class="info">Esperando el inicio del proceso...</p>
            </div>
        </div>
    </div>

    <script>
        let jobId = null;
        let intervalId = null;
        const logArea = document.getElementById('logArea');
        const crackButton = document.getElementById('crackButton');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const passwordResult = document.getElementById('passwordResult');

        function appendLog(message, tag) {
            const p = document.createElement('p');
            p.innerHTML = message;
            p.className = tag;
            logArea.appendChild(p);
            logArea.scrollTop = logArea.scrollHeight;
        }

        function clearUI() {
            logArea.innerHTML = '';
            passwordResult.textContent = 'N/A';
            passwordResult.className = 'text-3xl font-mono text-gray-500';
        }

        async function startCrack() {
            clearUI();
            
            const fileInput = document.getElementById('rarFile');
            // Obtiene el valor del radio button seleccionado
            const mode = document.querySelector('input[name="attackMode"]:checked').value;
            
            if (!fileInput.files.length) {
                appendLog("❌ Error: Por favor, selecciona un archivo RAR.", 'error');
                return;
            }

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('rar_file', file);
            formData.append('mode', mode);
            
            // Log para verificar el modo justo antes de enviar
            appendLog(`[INFO DEBUG] Modo seleccionado en el navegador: ${mode}`, 'info');
            

            // UI Feedback: Bloquear botón e iniciar indicador
            crackButton.disabled = true;
            crackButton.textContent = 'Iniciando...';
            loadingIndicator.classList.remove('hidden');

            appendLog(`[INFO] Enviando archivo (Modo: ${mode})...`, 'info');

            try {
                const response = await fetch('/crack', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.status === 202) {
                    jobId = data.job_id;
                    appendLog(`[INFO] Proceso iniciado con ID: ${jobId}. Esperando resultados...`, 'success');
                    crackButton.textContent = 'Procesando...';
                    
                    // Iniciar sondeo de estado
                    intervalId = setInterval(checkStatus, 1500); // Sondear cada 1.5 segundos

                } else {
                    const errorMessage = data.error || `Error desconocido (Status: ${response.status})`;
                    appendLog(`❌ Error del Servidor: ${errorMessage}`, 'error');
                    crackButton.disabled = false;
                    crackButton.textContent = 'Iniciar Crackeo';
                    loadingIndicator.classList.add('hidden');
                }
            } catch (error) {
                appendLog(`❌ Error de Conexión: No se pudo conectar al servidor Flask. Asegúrate de que app.py está corriendo.`, 'error');
                crackButton.disabled = false;
                crackButton.textContent = 'Iniciar Crackeo';
                loadingIndicator.classList.add('hidden');
            }
        }

        async function checkStatus() {
            if (!jobId) return;

            try {
                const response = await fetch(`/status/${jobId}`);
                const job = await response.json();

                if (response.status !== 200) {
                     clearInterval(intervalId);
                     appendLog(`❌ Error al obtener estado: ${job.error}`, 'error');
                     return;
                }

                // Actualizar log
                logArea.innerHTML = ''; 
                job.log.forEach(item => {
                    appendLog(item.message, item.tag);
                });

                if (job.status === 'finished') {
                    clearInterval(intervalId);
                    loadingIndicator.classList.add('hidden');
                    crackButton.disabled = false;
                    crackButton.textContent = 'Iniciar Crackeo';
                    
                    if (job.password) {
                        passwordResult.textContent = job.password;
                        passwordResult.className = 'text-3xl font-mono text-green-600 font-bold';
                    } else {
                        passwordResult.textContent = 'FALLIDO';
                        passwordResult.className = 'text-3xl font-mono text-red-600 font-bold';
                    }
                }

            } catch (error) {
                clearInterval(intervalId);
                appendLog(`❌ Error de Red durante el sondeo.`, 'error');
                crackButton.disabled = false;
                crackButton.textContent = 'Iniciar Crackeo';
                loadingIndicator.classList.add('hidden');
            }
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # --- Verificación de Rutas Cruciales ANTES de iniciar Flask ---
    executables_ok = True
    
    print(f"\n[INFO] Directorio base de John The Ripper (ABSOLUTO): {ABSOLUTE_JTR_DIR}")
    
    for tool_path in [JTR_PATH, RAR2JOHN_PATH]:
        if not os.path.exists(tool_path):
            print(f"\n❌ ERROR DE CONFIGURACIÓN: No se encontró el ejecutable: {tool_path}")
            print(f"❌ Por favor, revisa que la ruta '{RUTA_BASE_JOHN}' apunte a la carpeta que contiene los archivos 'john.exe' y 'rar2john.exe'.")
            executables_ok = False
    
    if not os.path.exists(DICTIONARY_PATH_FULL):
         print(f"\n⚠️ ADVERTENCIA: No se encontró el diccionario completo rockyou.txt en: {DICTIONARY_PATH_FULL}")
         print("⚠️ Solo funcionará el modo 'Rápido', 'Fuerza Bruta' y 'Máscara'. El modo 'Diccionario Completo' fallará.")

    if not executables_ok:
        import sys
        sys.exit(1)
    # ---------------------------------------------------------------
    
    try:
        create_temp_dictionary(DICTIONARY_PATH_TEMP)
        if os.path.exists(DICTIONARY_PATH_TEMP):
            os.remove(DICTIONARY_PATH_TEMP)
        
        print("--- SERVIDOR FLASK INICIADO ---")
        print("Abre tu navegador en: http://127.0.0.1:5000")
        app.run(debug=True, use_reloader=False)

    except Exception as e:
        print("\n" + "="*50)
        print("❌ ERROR CRÍTICO AL INICIAR EL SERVIDOR FLASK ❌")
        print("Asegúrate de tener Flask instalado (pip install Flask).")
        print(f"Detalle del error: {e}")
        print("="*50 + "\n")