import eel
import binascii
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os
import subprocess 
import threading 
import sys 
# Nota: ctypes y tempfile ya no son necesarios para la ruta 8.3, 
# pero mantenemos tempfile para la estrategia de copia temporal.
import tempfile 
import shutil # Necesario para copiar archivos

# ----------------------------------------------------
# 1. CONFIGURACIÓN Y VARIABLES GLOBALES
# ----------------------------------------------------
HASH_FILE = "hash_rar.txt"
WORDLIST_FILE = "rockyou.txt"
CRACK_RUNNING = False 

eel.init('web')

def parse_rar5_hash(hash_line):
    """Extrae el Salt, la Verificación Cifrada y las Iteraciones del hash RAR5/RAR4."""
    try:
        parts = hash_line.strip().split('$')
        if not (hash_line.startswith('$rar') and len(parts) >= 6):
            raise ValueError("Línea de hash no tiene el formato RAR esperado.")
            
        salt = binascii.unhexlify(parts[3]) 
        verification_cifrada = binascii.unhexlify(parts[5])
        iterations = 32768 
        return salt, verification_cifrada, iterations
    except Exception as e:
        print(f"--- ERROR al parsear el hash: {e} ---", file=sys.stderr)
        raise ValueError(f"Error al parsear el hash RAR: {e}")


# ----------------------------------------------------
# 2. FUNCIÓN DE CANCELACIÓN
# ----------------------------------------------------

@eel.expose
def stop_cracking():
    """Establece la bandera global para detener el proceso."""
    global CRACK_RUNNING
    if CRACK_RUNNING:
        eel.report_status("\n[!] RECIBIDA SEÑAL DE CANCELACIÓN. Deteniendo...")
        CRACK_RUNNING = False
        return True
    return False


# ----------------------------------------------------
# 3. FUNCIÓN DE CRACKEO (EJECUTADA EN HILO SECUNDARIO)
# ----------------------------------------------------

def crack_rar5_web():
    """Ejecuta el ataque de diccionario sobre el hash RAR (compatible con RAR4/RAR5)."""
    global CRACK_RUNNING
    
    print("--- DEBUG: Iniciando crackeo en hilo secundario ---", file=sys.stderr)

    if not os.path.exists(WORDLIST_FILE):
        eel.report_status(f"ERROR: Lista de palabras '{WORDLIST_FILE}' NO encontrada.")
        CRACK_RUNNING = False
        return
        
    if not os.path.exists(HASH_FILE):
        # Si el hash_rar.txt no existe, es que falló la escritura en el paso 5.
        eel.report_status(f"ERROR: Archivo de Hash '{HASH_FILE}' NO encontrado. (Fallo de escritura en el proceso anterior).")
        CRACK_RUNNING = False
        return

    try:
        with open(HASH_FILE, 'r') as f:
            rar_hash_line = f.readline().strip() 
        
        print(f"--- DEBUG: Hash leído de {HASH_FILE}: {rar_hash_line}", file=sys.stderr)

        salt, verification_cifrada, iterations = parse_rar5_hash(rar_hash_line)

    except Exception as e:
        eel.report_status(f"ERROR Crítico al cargar o parsear el hash: {e}")
        CRACK_RUNNING = False
        return

    eel.report_status(f"\n[+] Iniciando Ataque de Diccionario. Iteraciones: {iterations}")
    CRACK_RUNNING = True 
    
    try:
        with open(WORDLIST_FILE, 'r', encoding='latin-1') as f:
            for i, line in enumerate(f):
                
                if not CRACK_RUNNING:
                    eel.report_status("\n[!] Proceso detenido por el usuario.")
                    break
                
                password = line.strip()
                
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=16,
                    salt=salt,
                    iterations=iterations,
                )
                key = kdf.derive(password.encode('utf-8'))
                verification_key = key[:1] 

                if verification_key == verification_cifrada[:1]:
                    eel.report_status(f"\n[+] ¡CONTRASENA ENCONTRADA: {password}")
                    print(f"--- DEBUG: Contraseña {password} encontrada exitosamente ---", file=sys.stderr)
                    CRACK_RUNNING = False
                    return

                if (i + 1) % 10000 == 0: 
                    eel.sleep(0.01) 
                    eel.report_status(f"Probando: {i + 1} palabras. Última: {password}")
                    
            if CRACK_RUNNING:
                eel.report_status("\n[-] Ataque de diccionario completado. Contraseña NO encontrada en rockyou.txt.")
            
    except Exception as e:
        eel.report_status(f"ERROR inesperado durante el ataque: {e}")
        
    finally:
        CRACK_RUNNING = False


# ----------------------------------------------------
# 4. FUNCIÓN AUXILIAR PARA SUBPROCESS (RAR4/RAR5 CHECK)
# ----------------------------------------------------

def ejecutar_rar2john(comando_list, formato_rar):
    """Ejecuta un comando subprocess (rar2john) y devuelve la línea de hash si es exitoso."""
    
    
    # comando_list ya es la lista base: [rar2john_path, rar_path_temp]
    if formato_rar == 'RAR4':
        comando_list.append("$OLD$") # Añadir el argumento para RAR4
    
    # Mostrar el comando completo en la interfaz (solo para debug)
    eel.report_status(f"  [>] Ejecutando comando ({formato_rar}): {' '.join(comando_list)}")
    
    try:
        # Ejecutar sin shell=True, que es más seguro y fiable
        resultado = subprocess.run(
            comando_list, # Pasamos la lista de argumentos directamente
            shell=False,  # Deshabilitamos el shell
            capture_output=True,
            text=True,
            check=False,
            encoding='utf-8',
            timeout=15 
        )
        
        # Si el código de retorno es distinto de cero, hubo un error de ejecución
        if resultado.returncode != 0:
            error_msg = resultado.stderr.strip() or "Error desconocido (sin salida)."
            eel.report_status(f"  [!] Herramienta falló con Código de Salida {resultado.returncode}. Mensaje: {error_msg}")
            print(f"--- ERROR: Subprocess falló (Return Code {resultado.returncode}): {error_msg} ---", file=sys.stderr)
            return "" 
        
        hash_line = resultado.stdout.strip()
        if hash_line and hash_line.startswith('$rar'):
            return hash_line
        
        # DEBUG Adicional: Si no se encuentra el hash, mostramos el estado de salida.
        # Esto ocurre cuando rar2john se ejecuta, pero no encuentra hash (e.g., archivo RAR no cifrado)
        print(f"--- DEBUG: Falla al obtener hash. Código de retorno: {resultado.returncode}", file=sys.stderr)
        if resultado.stderr.strip():
            print(f"--- DEBUG: STDERR (No Hash): {resultado.stderr.strip()}", file=sys.stderr)
            
        return ""
        
    except subprocess.TimeoutExpired:
        eel.report_status("  [!] Error: Herramienta tardó demasiado. Tiempo límite agotado.")
        return ""
    except FileNotFoundError:
        # Esto ocurre si el sistema no puede encontrar/ejecutar el archivo
        eel.report_status("  [!!!] ERROR CRÍTICO DE EJECUCIÓN: 'rar2john.exe' no se pudo iniciar. (Revisa Antivirus).")
        return ""
    except Exception as e:
        eel.report_status(f"  [!] Error: Fallo inesperado durante la ejecución: {e}")
        return ""


# ----------------------------------------------------
# 5. FUNCIÓN DE PROCESO COMPLETO (LANZA EN UN HILO)
# ----------------------------------------------------

@eel.expose
def iniciar_proceso_completo(rar_path):
    """
    Recibe la ruta, extrae el hash probando primero RAR5 y luego RAR4, y lanza el crackeo.
    Utiliza una copia temporal del archivo RAR para máxima compatibilidad con rar2john.
    """
    
    # Ruta crítica: Busca rar2john.exe dentro de la subcarpeta 'run'
    rar2john_path = os.path.join(os.path.dirname(__file__), 'run', 'rar2john.exe')
    
    # Convertir la ruta relativa (si es que se usó) a absoluta
    rar_path_abs = os.path.abspath(rar_path)
    
    # ------------------ DEBUG CRÍTICO: RUTA REAL ------------------
    print(f"--- DEBUG PATH: Buscando rar2john en: {rar2john_path} ---", file=sys.stderr)
    # ------------------------------------------------------------
    
    if not os.path.exists(rar2john_path):
         eel.report_status(f"ERROR: No se encontró 'rar2john.exe' en la ruta esperada: {rar2john_path}")
         return

    if not os.path.exists(rar_path_abs):
        eel.report_status(f"ERROR: El archivo RAR de origen NO existe: {rar_path_abs}")
        return

    # ----------------------------------------------------------
    # ESTRATEGIA DE COPIA TEMPORAL para compatibilidad de rutas
    # ----------------------------------------------------------
    rar_path_temp = None
    try:
        # 1. Crear un nombre de archivo temporal en el directorio temporal del sistema
        temp_dir = tempfile.gettempdir()
        temp_filename = os.path.basename(rar_path_abs) 
        rar_path_temp = os.path.join(temp_dir, temp_filename)
        
        # Asegurarse de que el archivo temporal no exista antes de copiar
        if os.path.exists(rar_path_temp):
            os.remove(rar_path_temp)

        # 2. Copiar el archivo RAR al directorio temporal
        shutil.copy2(rar_path_abs, rar_path_temp)
        
        print(f"--- DEBUG: Archivo copiado temporalmente a: {rar_path_temp} ---", file=sys.stderr)

    except Exception as e:
        eel.report_status(f"ERROR: No se pudo copiar el archivo RAR a la carpeta temporal. ¿Problema de permisos?: {e}")
        return
        
    eel.report_status(f"[*] Archivo RAR copiado a ruta temporal para compatibilidad. Iniciando extracción de hash...")
    hash_line = ""
    
    # ----------------------------------------------------------
    # Definir el comando usando la RUTA TEMPORAL
    # ----------------------------------------------------------
    comando_base_list = [rar2john_path, rar_path_temp]
    
    try:
        # Intentos de extracción (RAR5 y luego RAR4)
        hash_line = ejecutar_rar2john(list(comando_base_list), 'RAR5') 
        
        if not hash_line:
            eel.report_status("-> Falló el RAR5. Intentando con la configuración RAR4/Clásica...")
            hash_line = ejecutar_rar2john(list(comando_base_list), 'RAR4')

        # Manejo del fallo de extracción
        if not hash_line:
            eel.report_status("\n[!!!] ERROR CRÍTICO: No se pudo extraer el hash con ninguna configuración.")
            return

        # 2. Guardar el hash extraído en hash_rar.txt
        with open(HASH_FILE, 'w') as f:
            f.write(hash_line)
        
        print(f"--- DEBUG: Hash extraído y escrito en {HASH_FILE}: {hash_line}", file=sys.stderr)
        
        # 3. DOBLE COMPROBACIÓN: Confirmar que el archivo se creó y es legible
        if not os.path.exists(HASH_FILE):
             eel.report_status("\n[!!!] ERROR CRÍTICO DE PERMISOS: El sistema NO PERMITIÓ escribir 'hash_rar.txt'.")
             return

        eel.report_status("[*] Hash extraído y guardado con éxito. Iniciando ataque de fuerza bruta...")
        
        # 4. Iniciar el ataque de cracking en un hilo separado
        crack_thread = threading.Thread(target=crack_rar5_web)
        crack_thread.start()

    except Exception as e:
        eel.report_status(f"ERROR: Fallo durante el proceso de cracking o escritura: {e}")
        print(f"--- ERROR CRÍTICO: Fallo al escribir {HASH_FILE} o durante el crackeo: {e} ---", file=sys.stderr)
        
    finally:
        # 5. Limpieza: Eliminar el archivo temporal
        if rar_path_temp and os.path.exists(rar_path_temp):
            try:
                os.remove(rar_path_temp)
                print(f"--- DEBUG: Archivo temporal eliminado: {rar_path_temp} ---", file=sys.stderr)
            except Exception as e:
                print(f"--- ADVERTENCIA: No se pudo eliminar el archivo temporal {rar_path_temp}: {e} ---", file=sys.stderr)


# ----------------------------------------------------
# 6. INICIO DE LA APLICACIÓN
# ----------------------------------------------------
# CAMBIO CRÍTICO: Usamos el puerto 8001 en lugar del 8000 predeterminado
eel.start('index.html', size=(1000, 700), port=8001)