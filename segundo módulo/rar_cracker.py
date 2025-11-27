import hashlib
import binascii
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# --- CONFIGURACIÓN ---
HASH_FILE = "hash_rar.txt" # Nombre del archivo que contiene el hash RAR5
WORDLIST_FILE = "rockyou.txt" # Nombre del archivo de lista de palabras

# --- LECTURA Y PARSEO DEL HASH RAR5 ---
def parse_rar5_hash(hash_line):
    # El formato del hash es complejo. Esta función lo descompone.
    # Ejemplo: $rar5$16$SAL$15$VERIFICACION_CIFRADA$8$VERIFICACION_PLANA
    parts = hash_line.strip().split('$')
    
    # El salt está en parts[3]
    salt = binascii.unhexlify(parts[3]) 
    
    # La verificación cifrada está en parts[5]
    verification_cifrada = binascii.unhexlify(parts[5])
    
    # El número de iteraciones RAR5 es siempre 32768
    iterations = 32768
    
    return salt, verification_cifrada, iterations

# --- FUNCIÓN PRINCIPAL DE CRACKEO ---
def crack_rar5():
    try:
        with open(HASH_FILE, 'r') as f:
            rar_hash_line = f.readline()
            
        salt, verification_cifrada, iterations = parse_rar5_hash(rar_hash_line)
        print(f"[*] Hash RAR5 cargado. Salt: {binascii.hexlify(salt).decode()}")
        print(f"[*] Iteraciones de PBKDF2: {iterations}")
        print("-" * 30)

    except Exception as e:
        print(f"[-] ERROR al leer o parsear el hash: {e}")
        return

    try:
        with open(WORDLIST_FILE, 'r', encoding='latin-1') as f:
            for i, line in enumerate(f):
                password = line.strip()
                
                # 1. Derivar la clave de prueba (PBKDF2)
                # Esta es la parte lenta que JtR y Hashcat optimizan.
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=16, # El RAR5 usa una clave de 16 bytes (128 bits)
                    salt=salt,
                    iterations=iterations,
                )
                
                # Obtener la clave de prueba usando la palabra candidata
                key = kdf.derive(password.encode('utf-8'))
                
                # 2. Generar la clave de verificación para la comparación
                # RAR usa el inicio de la clave generada para verificar.
                verification_key = key[:1] # Tomamos el primer byte

                # 3. Comparar (Verificación)
                # Si el primer byte de la clave coincide con el primer byte cifrado, ¡es la contraseña!
                if verification_key == verification_cifrada[:1]:
                    print(f"\n[+] ¡Contraseña encontrada después de {i+1} intentos!")
                    print(f"[+] Contraseña: {password}")
                    return

                # Reportar estado cada 100,000 intentos (para no abrumar la consola)
                if (i + 1) % 100000 == 0:
                    print(f"[*] Probando: {i + 1} contraseñas. Última probada: {password}")
                    
            print("\n[-] Ataque de diccionario completado. Contraseña NO encontrada.")

    except FileNotFoundError:
        print(f"[-] ERROR: No se encontró el archivo de lista de palabras: {WORDLIST_FILE}")
    except Exception as e:
        print(f"[-] ERROR durante el crackeo: {e}")


if __name__ == "__main__":
    crack_rar5()