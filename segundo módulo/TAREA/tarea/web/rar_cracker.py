import subprocess
import os
import sys

# --- CONFIGURACIÓN (Ajusta estas rutas según tu sistema) ---
# John the Ripper (JTR) y sus herramientas deben estar instalados.
# En Windows, es ALTAMENTE RECOMENDABLE usar la ruta ABSOLUTA del ejecutable si no están en el PATH.

# 1. DEFINE LA RUTA BASE (DEBES AJUSTAR ESTA LÍNEA CON LA RUTA COMPLETA DE TU CARPETA 'run')
# EJEMPLO ASUMIDO DE TU CONSOLA:
RUTA_BASE_JOHN = r"C:\Users\kinso\OneDrive\Escritorio\zono_seg_inf\segundo módulo\tarea_2\run"

# 2. DEFINICIÓN DE RUTAS ABSOLUTAS USANDO LA RUTA BASE
# Utilizamos os.path.join para construir rutas robustas
JTR_PATH = os.path.join(RUTA_BASE_JOHN, "john.exe")
RAR2JOHN_PATH = os.path.join(RUTA_BASE_JOHN, "rar2john.exe")
DICTIONARY_PATH = os.path.join(RUTA_BASE_JOHN, "rockyou.txt") 
# -----------------------------------------------------------


def extract_hash(rar_file_path, output_hash_file):
    """
    Ejecuta rar2john para extraer el hash del archivo RAR.
    """
    print(f"[1/3] Ejecutando: {RAR2JOHN_PATH} {rar_file_path}")
    
    try:
        # Comando para ejecutar rar2john y guardar la salida en el archivo de hash
        with open(output_hash_file, 'w') as f:
            # Usamos comillas dobles alrededor de las rutas de los ejecutables y archivos
            # para manejar espacios en los nombres de archivos o directorios de Windows.
            command = f'"{RAR2JOHN_PATH}" "{rar_file_path}"'

            subprocess.run(
                command, 
                shell=True, 
                check=True, 
                stdout=f, 
                stderr=subprocess.PIPE
            )
        print(f"[2/3] Hash guardado exitosamente en: {output_hash_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar {RAR2JOHN_PATH}: El archivo RAR no es válido o {RAR2JOHN_PATH} no se encontró en la ruta especificada.")
        print(f"Detalles del error (stderr): {e.stderr.decode()}")
        # Imprimir la ruta para el diagnóstico
        print(f"[DEBUG] Ruta intentada para rar2john: {RAR2JOHN_PATH}")
        return False
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el ejecutable en la ruta: '{RAR2JOHN_PATH}'. Asegúrate de que la variable RUTA_BASE_JOHN es correcta.")
        return False


def crack_hash(hash_file_path, dictionary_path):
    """
    Ejecuta John the Ripper con el archivo de hash y el diccionario.
    """
    
    print(f"\n[3/3] Ejecutando John the Ripper con ataque de diccionario en hash de '{hash_file_path}'")
    
    try:
        # Comando para iniciar el ataque de diccionario
        command_crack = f'"{JTR_PATH}" --wordlist="{dictionary_path}" "{hash_file_path}"'
        
        subprocess.run(
            command_crack,
            shell=True,
            check=False,
            stderr=subprocess.PIPE
        )
        
        # Comando para mostrar el resultado (siempre con la opción --show)
        command_show = f'"{JTR_PATH}" --show "{hash_file_path}"'
        
        result = subprocess.run(
            command_show,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )

        output_lines = result.stdout.strip().split('\n')

        # Buscar la línea que contiene la contraseña
        cracked_password = None
        for line in output_lines:
            # Una línea crackeada típica luce como: filename:password
            if ":" in line and not line.endswith(':'): 
                # Intentamos parsear solo si hay contenido después de los dos puntos
                parts = line.split(':')
                if len(parts) >= 2 and parts[1].strip():
                    # La contraseña es la segunda parte (índice 1), quitando el formato de John
                    cracked_password = parts[1].split(' ')[0]
                    break

        if cracked_password:
            print("\n🎉 ÉXITO: Contraseña encontrada.")
            print(f"Contraseña: {cracked_password}")
        else:
            print("\n😔 FALLO: Contraseña no encontrada en el diccionario.")
            print("Intenta con un ataque de fuerza bruta o un diccionario diferente.")

    except subprocess.CalledProcessError as e:
        error_output = e.stderr.decode() + e.stdout
        if "No password hashes found" in error_output or "0 password hashes cracked" in error_output:
             print("\n😔 FALLO: Contraseña no encontrada en el diccionario.")
             print("Intenta con un ataque de fuerza bruta o un diccionario diferente.")
        else:
            print(f"❌ Error al ejecutar {JTR_PATH} (Show): Comprueba tu instalación y rutas.")
        return False
    except FileNotFoundError:
        print(f"❌ Error: El comando '{JTR_PATH}' no se encontró. Asegúrate de que la variable RUTA_BASE_JOHN es correcta.")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python rar_cracker.py <ruta_del_archivo.rar>")
        sys.exit(1)

    rar_file = sys.argv[1]
    
    if not os.path.exists(rar_file):
        print(f"❌ Error: El archivo '{rar_file}' no existe.")
        sys.exit(1)
        
    hash_output_name = rar_file.replace('.rar', '').replace('.RAR', '') + '_hash.txt'
    
    # Asegurarse de que el diccionario existe antes de intentar crackear
    if not os.path.exists(DICTIONARY_PATH):
        print(f"⚠️ Advertencia: No se encontró el diccionario en la ruta: '{DICTIONARY_PATH}'.")
        print("Por favor, revisa que la variable RUTA_BASE_JOHN sea correcta.")
        sys.exit(1)


    # --- Flujo principal ---
    if extract_hash(rar_file, hash_output_name):
        crack_hash(hash_output_name, DICTIONARY_PATH)

    # Limpieza opcional: si quieres borrar el archivo hash después
    # if os.path.exists(hash_output_name):
    #     os.remove(hash_output_name)
    #     print(f"\n[INFO] Archivo temporal {hash_output_name} eliminado.")