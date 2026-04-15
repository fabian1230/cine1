
function showTab(id, btn) {
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+id).classList.add('active');
  btn.classList.add('active');
  if (id==='ocupacion') cargarDashboard();
  if (id==='usuarios') cargarUsuarios();
}

// ── Dashboard ──
async function cargarDashboard() {
  const d = await fetch('/api/admin/dashboard').then(r=>r.json());
  document.getElementById('s-ventas').textContent = '$'+Number(d.total_ventas||0).toLocaleString();
  document.getElementById('s-hoy').textContent    = d.tiquetes_hoy||0;
  document.getElementById('s-pelis').textContent  = d.peliculas_activas||0;
  document.getElementById('s-func').textContent   = d.funciones_hoy||0;
  // Gráfico géneros
  const maxG = Math.max(1, ...( d.ventas_por_genero||[]).map(g=>g.cantidad));
  document.getElementById('genero-chart').innerHTML = (d.ventas_por_genero||[]).length
    ? (d.ventas_por_genero).map(g=>`
      <div class="genero-bar">
        <span style="min-width:100px;color:var(--pearl)">${g.genero}</span>
        <div class="genero-fill" style="width:${Math.round(g.cantidad/maxG*200)}px"></div>
        <span>${g.cantidad}</span>
      </div>`).join('')
    : '<p style="color:var(--pearl-dim)">Sin datos aún.</p>';
  // Tabla ocupación
  const oc = d.ocupacion_por_funcion || [];
  document.getElementById('tabla-ocup').innerHTML = oc.length
    ? `<table class="tabla">
        <thead><tr><th>Película</th><th>Fecha</th><th>Hora</th><th>Sala</th><th>Vendidos</th><th>Disponibles</th></tr></thead>
        <tbody>${oc.map(r=>`<tr>
          <td style="color:var(--pearl)">${r.pelicula}</td><td>${r.fecha}</td>
          <td>${(r.hora||'').slice(0,5)}</td><td>${r.sala||'—'}</td>
          <td>${r.vendidos}</td>
          <td class="${r.disponibles<20?'alerta':''}">${r.disponibles}</td>
        </tr>`).join('')}</tbody></table>`
    : '<p style="color:var(--pearl-dim)">Sin ventas en funciones próximas.</p>';
}

// ── Películas ──
async function cargarPelis() {
  const data = await fetch('/api/admin/peliculas').then(r=>r.json());
  document.getElementById('s-pelis').textContent = data.length;
  const sel = document.getElementById('sel-peli');
  sel.innerHTML = data.length
    ? data.map(p=>`<option value="${p.id}">${p.titulo}</option>`).join('')
    : '<option value="">No hay películas activas</option>';
  document.getElementById('lista-pelis').innerHTML = data.length
    ? data.map(p=>`
      <div class="peli-item">
        <img class="peli-thumb" src="${p.imagen_url||''}" onerror="this.style.opacity=.2" loading="lazy"/>
        <div style="flex:1;min-width:0">
          <strong style="color:var(--pearl)">${p.titulo}</strong>
          <span style="font-size:.75rem;color:var(--pearl-dim);display:block">${p.clasificacion||''} · ${p.duracion}min · ${p.genero||'—'}</span>
          <div class="chips">${(p.funciones||[]).map(f=>`
            <span class="chip">${f.fecha} ${(f.hora||'').slice(0,5)} ${f.formato||''}
              <button onclick="delFunc(${f.id})">✕</button>
            </span>`).join('') || '<span style="font-size:.75rem;color:var(--crimson-bright)">Sin funciones</span>'}
          </div>
        </div>
        <button onclick="delPeli(${p.id})" class="btn-danger btn-sm" style="flex-shrink:0">Desactivar</button>
      </div>`).join('')
    : '<p style="color:var(--pearl-dim)">Sin películas.</p>';
}

async function delPeli(id) {
  if(!confirm('¿Desactivar esta película?')) return;
  await fetch(`/api/peliculas/${id}`,{method:'DELETE'});
  cargarPelis(); cargarDashboard();
}
async function delFunc(id) {
  if(!confirm('¿Eliminar esta función?')) return;
  await fetch(`/api/funciones/${id}`,{method:'DELETE'});
  cargarPelis(); cargarDashboard();
}
async function regenerar() {
  if(!confirm('¿Regenerar funciones para todas las películas?')) return;
  await fetch('/api/admin/funciones-aleatorias',{method:'POST'});
  cargarPelis(); cargarDashboard();
}

document.getElementById('form-peli').addEventListener('submit', async e => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  body.duracion = parseInt(body.duracion);
  const res  = await fetch('/api/peliculas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await res.json();
  const msg  = document.getElementById('msg-peli');
  msg.className = res.ok?'msg-ok':'msg-err';
  msg.textContent = res.ok ? '✓ '+data.mensaje : '✗ '+(data.error||'Error');
  if(res.ok){ e.target.reset(); cargarPelis(); cargarDashboard(); }
});

document.getElementById('form-func').addEventListener('submit', async e => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  body.pelicula_id = parseInt(body.pelicula_id);
  body.precio = parseFloat(body.precio);
  const res  = await fetch('/api/funciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await res.json();
  const msg  = document.getElementById('msg-func');
  msg.className = res.ok?'msg-ok':'msg-err';
  msg.textContent = res.ok ? '✓ '+data.mensaje : '✗ '+(data.error||data.mensaje||'Error');
  if(res.ok){ e.target.reset(); cargarPelis(); cargarDashboard(); }
});

// ── Usuarios ──
async function cargarUsuarios() {
  const data = await fetch('/api/admin/usuarios').then(r=>r.json());
  document.getElementById('tabla-usuarios').innerHTML = data.length
    ? `<table class="usuarios-table">
        <thead><tr><th>Nombre</th><th>Email</th><th>Tel?fono</th><th>Registro</th><th>Tiquetes</th><th>Acci?n</th></tr></thead>
        <tbody>${data.map(u=>`<tr>
          <td style="color:var(--pearl)">${u.nombre}</td>
          <td>${u.email}</td><td>${u.telefono}</td><td>${u.fecha}</td>
          <td>${u.tiquetes}</td>
          <td><button class="btn-danger btn-sm" onclick='eliminarUsuario(${u.id}, ${JSON.stringify(u.nombre)})'>Eliminar</button></td>
        </tr>`).join('')}</tbody></table>`
    : '<p style="color:var(--pearl-dim)">Sin clientes registrados.</p>';
}

async function eliminarUsuario(id, nombre) {
  if (!confirm(`?Eliminar la cuenta de ${nombre}? Esta acci?n no se puede deshacer.`)) return;
  const res = await fetch(`/api/admin/usuarios/${id}`, { method: 'DELETE' });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || 'No se pudo eliminar la cuenta');
    return;
  }
  cargarUsuarios();
  cargarDashboard();
}

// ?? Init ??
cargarPelis();
cargarDashboard();
