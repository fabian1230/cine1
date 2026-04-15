// script.js – Lógica del Frontend – Aurum Cinema
let funcionSeleccionada = null;
let asientosSeleccionados = [];

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('form-validar')) initValidar();
});

function abrirModal(id)  {
  const el = document.getElementById(id);
  if (el) el.classList.remove('hidden');
}
function cerrarModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}
function escapar(str)    { return String(str).replace(/'/g,"\\'").replace(/"/g,'\\"'); }

// ── Modal funciones (index.html) ──────────────────────────────
async function abrirFunciones(peliculaId, titulo) {
  document.getElementById('modal-pelicula-titulo').textContent = titulo;
  const peliculas = await fetch('/api/cartelera').then(r => r.json());
  const peli = peliculas.find(p => p.id === peliculaId);
  const lista = document.getElementById('lista-funciones');

  if (!peli || !peli.funciones.length) {
    lista.innerHTML = '<p style="color:var(--pearl-dim);padding:20px">No hay funciones disponibles.<br><a href="/pelicula/'+peliculaId+'" style="color:var(--gold)">Ver detalle →</a></p>';
  } else {
    const fmtColor = { 'IMAX':'color:var(--gold)', '3D':'color:#25c26e', '2D':'color:var(--pearl-dim)' };
    lista.innerHTML = peli.funciones.map(f =>
      `<button class="funcion-btn" onclick="window.location.href='/asientos?funcion_id=${f.id}'">
        <span>📅 ${f.fecha} &nbsp; 🕐 ${(f.hora||'').slice(0,5)}</span>
        <span>🏛️ ${f.sala} &nbsp; <span style="${fmtColor[f.formato]||''}">${f.formato||'2D'}</span></span>
        <span style="color:var(--gold);font-weight:700">$${Number(f.precio).toLocaleString()}</span>
      </button>`
    ).join('');
    lista.innerHTML += `<a href="/pelicula/${peliculaId}" style="display:block;text-align:center;margin-top:12px;color:var(--pearl-dim);font-size:.8rem;text-decoration:none;">Ver detalles completos →</a>`;
  }
  // En algunas vistas este modal no existe; no debe bloquear la compra.
  cerrarModal('modal-asientos');
  abrirModal('modal-funcion');
}

// ── Validar tiquete ─────────────────────────────────────────
function initValidar() {
  document.getElementById('form-validar').addEventListener('submit', async e => {
    e.preventDefault();
    const codigo = e.target.codigo.value.trim().toUpperCase();
    const div    = document.getElementById('resultado-validacion');
    div.innerHTML = '<p class="loading">Validando...</p>';
    const res  = await fetch('/api/tiquetes/validar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({codigo})
    });
    const data = await res.json();
    if (data.estado === 'valido') {
      div.innerHTML = `<div class="msg-ok">
        <strong>✅ ${data.mensaje}</strong><br>
        🎬 ${data.pelicula || ''}<br>
        📅 ${data.funcion || ''} &nbsp; 🏛️ ${data.sala || ''}<br>
        💺 ${data.asientos || ''} asiento(s)
      </div>`;
    } else {
      const cls = { usado:'msg-warn', invalido:'msg-error' };
      div.innerHTML = `<p class="${cls[data.estado]||'msg-error'}">${data.mensaje}</p>`;
    }
  });
}
