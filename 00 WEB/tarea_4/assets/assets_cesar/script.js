// Función principal del algoritmo César
function cifradoCesar(texto, desplazamiento, cifrar = true) {
    const shift = cifrar ? desplazamiento : -desplazamiento;
    const alfabeto = 26;

    return texto.split('').map(caracter => {
        const codigo = caracter.charCodeAt(0);

        // Mayúsculas (A-Z)
        if (codigo >= 65 && codigo <= 90) {
            return String.fromCharCode(((codigo - 65 + shift) % alfabeto + alfabeto) % alfabeto + 65);
        }
        // Minúsculas (a-z)
        else if (codigo >= 97 && codigo <= 122) {
            return String.fromCharCode(((codigo - 97 + shift) % alfabeto + alfabeto) % alfabeto + 97);
        }
        return caracter;
    }).join('');
}

// Escuchadores de eventos (Listeners)
document.getElementById('btnCifrar').addEventListener('click', () => {
    procesar(true);
});

document.getElementById('btnDescifrar').addEventListener('click', () => {
    procesar(false);
});

document.getElementById('btnCopiar').addEventListener('click', () => {
    const resultado = document.getElementById('resultado');
    resultado.select();
    document.execCommand('copy');
    alert("¡Copiado al portapapeles!");
});

function procesar(esCifrado) {
    const texto = document.getElementById('mensaje').value;
    const clave = parseInt(document.getElementById('desplazamiento').value);
    
    if (isNaN(clave)) {
        alert("Por favor, ingresa un número válido.");
        return;
    }

    const resultado = cifradoCesar(texto, clave, esCifrado);
    document.getElementById('resultado').value = resultado;
}