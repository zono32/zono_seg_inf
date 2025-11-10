(function(){
  const chars = {
    lower: 'abcdefghijklmnopqrstuvwxyz',
    upper: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    digits: '0123456789',
    symbols: '!@#$%^&*()-_=+[]{};:,.<>?'
  };

  function genPw(len, useSymbols) {
    let pool = chars.lower + chars.upper + chars.digits;
    if (useSymbols) pool += chars.symbols;
    const arr = new Uint32Array(len);
    crypto.getRandomValues(arr);
    let pw = '';
    for (let i = 0; i < len; i++) {
      pw += pool[arr[i] % pool.length];
    }
    return pw;
  }

  function pwStrength(pw){
    let score = 0;
    if (pw.length >= 16) score += 3;
    else if (pw.length >= 12) score += 2;
    else if (pw.length >= 8) score += 1;
    if (/[A-Z]/.test(pw)) score += 1;
    if (/[a-z]/.test(pw)) score += 1;
    if (/[0-9]/.test(pw)) score += 1;
    if (/[^A-Za-z0-9]/.test(pw)) score += 1;
    return Math.min(score,7); // 0..7
  }

  function updateMeter(pw){
    const s = pwStrength(pw);
    const pct = Math.round((s / 7) * 100);
    const bar = document.getElementById('pwBar');
    const text = document.getElementById('pwText');
    bar.style.width = pct + '%';
    const labels = ['Muy débil','Débil','Aceptable','Regular','Buena','Fuerte','Muy fuerte','Excelente'];
    text.textContent = 'Fuerza: ' + labels[s];
  }

  document.getElementById('genPwBtn').addEventListener('click', () => {
    const len = parseInt(document.getElementById('pwLen').value, 10) || 16;
    const useSymbols = document.getElementById('useSymbols').checked;
    const pw = genPw(len, useSymbols);
    document.getElementById('pwOutput').value = pw;
    updateMeter(pw);
  });

  document.getElementById('copyPwBtn').addEventListener('click', async () => {
    const txt = document.getElementById('pwOutput').value;
    if (!txt) return;
    try {
      await navigator.clipboard.writeText(txt);
      alert('Contraseña copiada al portapapeles');
    } catch (e) {
      alert('No se pudo copiar automáticamente. Selecciona y copia manualmente.');
    }
  });

  document.getElementById('pwOutput').addEventListener('input', (e) => updateMeter(e.target.value));

})();
