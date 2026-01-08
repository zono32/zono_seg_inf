// Espera a que el HTML esté cargado completamente
document.addEventListener('DOMContentLoaded', () => {
    
    const btn = document.getElementById('theme-toggle');
    const html = document.documentElement;

    // Verificamos si el botón existe para evitar errores en consola
    if (btn) {
        btn.addEventListener('click', () => {
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            html.setAttribute('data-theme', newTheme);
            
            // Opcional: Guardar la preferencia en el navegador
            localStorage.setItem('theme', newTheme);
        });
    }

    // Opcional: Cargar el tema guardado al recargar la página
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        html.setAttribute('data-theme', savedTheme);
    }
});

function toggleMenu(id) {
  const menu = document.getElementById(id);

  // cerrar otros menús
  document.querySelectorAll('.dropdown').forEach(m => {
    if (m !== menu) m.style.display = 'none';
  });

  // abrir / cerrar el actual
  menu.style.display =
    menu.style.display === 'block' ? 'none' : 'block';
}

// cerrar menús al hacer clic fuera
document.addEventListener('click', function (e) {
  if (!e.target.classList.contains('hamburger')) {
    document.querySelectorAll('.dropdown').forEach(m => {
      m.style.display = 'none';
    });
  }
});
