# app.py – Backend Flask – Sistema de Gestión de Cine
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from config import Config
from datetime import datetime, date, timedelta
from functools import wraps
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import uuid, qrcode, io, base64, hashlib, random

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# ============================================================
#  CACHE SIMPLE EN MEMORIA (evita re-generar QRs en cada llamada)
# ============================================================
_qr_cache = {}
BRAND_NAME = 'Aurum Cinema'
BRAND_ADMIN_NAME = 'Aurum Cinema Studio'
BRAND_TAGLINE = 'Experiencias de cine premium'
POSTERS_CANONICOS = {
    'jurassic park': 'https://upload.wikimedia.org/wikipedia/en/e/e7/Jurassic_Park_poster.jpg',
    'terrifier': 'https://upload.wikimedia.org/wikipedia/en/thumb/1/1b/Terrifier-final-poster.jpg/250px-Terrifier-final-poster.jpg',
}

@app.context_processor
def inject_brand():
    return {
        'brand_name': BRAND_NAME,
        'brand_admin_name': BRAND_ADMIN_NAME,
        'brand_tagline': BRAND_TAGLINE,
    }

def generar_qr(codigo):
    if codigo in _qr_cache:
        return _qr_cache[codigo]
    try:
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(codigo)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        _qr_cache[codigo] = b64
        return b64
    except Exception as e:
        print(f"[ERROR] QR: {e}")
        return ''

def enviar_correo_bienvenida(destinatario, nombre):
    if not app.config.get('MAIL_ENABLED'):
        return False, 'mail_disabled'

    remitente = app.config.get('MAIL_FROM')
    usuario   = app.config.get('MAIL_USERNAME')
    password  = app.config.get('MAIL_PASSWORD')
    host      = app.config.get('MAIL_HOST')
    port      = app.config.get('MAIL_PORT')

    if not all([remitente, usuario, password, host, port]):
        return False, 'mail_incomplete'

    subject = f"Bienvenido a {BRAND_NAME}, {nombre}"
    html = f"""
    <html>
      <body style="margin:0;padding:0;background:#0b1019;font-family:Arial,sans-serif;color:#e8e4d4;">
        <div style="max-width:640px;margin:0 auto;padding:32px 20px;">
          <div style="background:linear-gradient(135deg,#111825 0%,#1a2233 100%);border:1px solid rgba(212,168,67,.2);border-radius:22px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.35);">
            <div style="padding:28px 32px;background:linear-gradient(90deg,#d4a843,#f0c96a);color:#080b12;font-family:Georgia,serif;font-size:28px;font-weight:700;">
              {BRAND_NAME}
            </div>
            <div style="padding:36px 32px;">
              <p style="margin:0 0 8px;font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:#d4a843;">Registro confirmado</p>
              <h1 style="margin:0 0 16px;font-family:Georgia,serif;font-size:34px;line-height:1.15;color:#ffffff;">Tu acceso premium ya está activo</h1>
              <p style="margin:0 0 16px;font-size:16px;line-height:1.7;color:#d7d2c2;">Hola <strong>{nombre}</strong>, gracias por registrarte en <strong>{BRAND_NAME}</strong>.</p>
              <a href="/" style="display:inline-block;padding:14px 24px;border-radius:999px;background:#d4a843;color:#080b12;text-decoration:none;font-weight:700;">Entrar a {BRAND_NAME}</a>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    plain = f"Hola {nombre},\n\nTu registro en {BRAND_NAME} fue exitoso.\n{BRAND_TAGLINE}.\n"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f"{app.config.get('MAIL_FROM_NAME')} <{remitente}>"
    msg['To']      = destinatario
    msg.attach(MIMEText(plain, 'plain', 'utf-8'))
    msg.attach(MIMEText(html,  'html',  'utf-8'))

    try:
        if app.config.get('MAIL_USE_SSL'):
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
        with server:
            if app.config.get('MAIL_USE_TLS') and not app.config.get('MAIL_USE_SSL'):
                server.starttls()
            server.login(usuario, password)
            server.sendmail(remitente, [destinatario], msg.as_string())
        return True, 'sent'
    except Exception as e:
        print(f"[WARN] No se pudo enviar correo a {destinatario}: {e}")
        return False, 'send_failed'

# ============================================================
#  SEGURIDAD
# ============================================================
def hash_password(password):
    salt   = uuid.uuid4().hex
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def check_password(password, stored):
    try:
        salt, hashed = stored.split(':')
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except Exception:
        return False

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'admin':
            return redirect(url_for('admin_login_page'))
        return f(*args, **kwargs)
    return decorated

def api_response(data, status=200, cache_seconds=0):
    resp = make_response(jsonify(data), status)
    if cache_seconds > 0:
        resp.headers['Cache-Control'] = f'public, max-age={cache_seconds}'
    else:
        resp.headers['Cache-Control'] = 'no-store'
    return resp

# ============================================================
#  MODELOS
# ============================================================
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id             = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    email          = db.Column(db.String(150), unique=True, nullable=False)
    contrasena     = db.Column(db.String(255), nullable=False)
    rol            = db.Column(db.Enum('admin', 'cliente'), default='cliente')
    telefono       = db.Column(db.String(20))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Pelicula(db.Model):
    __tablename__ = 'peliculas'
    id            = db.Column(db.Integer, primary_key=True)
    titulo        = db.Column(db.String(200), nullable=False)
    descripcion   = db.Column(db.Text)
    duracion      = db.Column(db.Integer, nullable=False)
    genero        = db.Column(db.String(80))
    clasificacion = db.Column(db.String(10))
    imagen_url    = db.Column(db.String(300))
    trailer_url   = db.Column(db.String(300))
    estado        = db.Column(db.Enum('activa', 'inactiva'), default='activa')

class Funcion(db.Model):
    __tablename__ = 'funciones'
    id          = db.Column(db.Integer, primary_key=True)
    pelicula_id = db.Column(db.Integer, db.ForeignKey('peliculas.id'), nullable=False)
    fecha       = db.Column(db.Date, nullable=False)
    hora        = db.Column(db.Time, nullable=False)
    sala        = db.Column(db.String(50), default='Sala Principal')
    precio      = db.Column(db.Numeric(10, 2), nullable=False)
    formato     = db.Column(db.String(10), default='2D')
    estado      = db.Column(db.Enum('disponible', 'cancelada'), default='disponible')
    pelicula    = db.relationship('Pelicula', backref='funciones')

class Asiento(db.Model):
    __tablename__ = 'asientos'
    id      = db.Column(db.Integer, primary_key=True)
    numero  = db.Column(db.Integer, nullable=False)
    fila    = db.Column(db.String(1), nullable=False)
    columna = db.Column(db.Integer, nullable=False)
    tipo    = db.Column(db.String(10), default='normal')
    estado  = db.Column(db.Enum('activo', 'inactivo'), default='activo')

class Tiquete(db.Model):
    __tablename__ = 'tiquetes'
    id             = db.Column(db.Integer, primary_key=True)
    codigo         = db.Column(db.String(50), unique=True, nullable=False)
    usuario_id     = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    funcion_id     = db.Column(db.Integer, db.ForeignKey('funciones.id'), nullable=False)
    fecha_compra   = db.Column(db.DateTime, default=datetime.utcnow)
    total          = db.Column(db.Numeric(10, 2), nullable=False)
    nombre_cliente = db.Column(db.String(100))
    estado         = db.Column(db.Enum('activo', 'usado', 'cancelado'), default='activo')
    funcion        = db.relationship('Funcion', backref='tiquetes')
    detalles       = db.relationship('DetalleTiquete', backref='tiquete', cascade='all, delete-orphan')
    usuario        = db.relationship('Usuario', backref='tiquetes')

class DetalleTiquete(db.Model):
    __tablename__ = 'detalle_tiquete'
    id              = db.Column(db.Integer, primary_key=True)
    tiquete_id      = db.Column(db.Integer, db.ForeignKey('tiquetes.id'), nullable=False)
    asiento_id      = db.Column(db.Integer, db.ForeignKey('asientos.id'), nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    asiento         = db.relationship('Asiento')

def asegurar_columnas_compatibles():
    inspector = inspect(db.engine)
    columnas_por_tabla = {
        tabla: {col['name'] for col in inspector.get_columns(tabla)}
        for tabla in inspector.get_table_names()
    }
    alter_statements = []
    if 'usuarios' in columnas_por_tabla and 'telefono' not in columnas_por_tabla['usuarios']:
        alter_statements.append("ALTER TABLE usuarios ADD COLUMN telefono VARCHAR(20) NULL")
    if 'peliculas' in columnas_por_tabla and 'trailer_url' not in columnas_por_tabla['peliculas']:
        alter_statements.append("ALTER TABLE peliculas ADD COLUMN trailer_url VARCHAR(300) NULL")
    if 'funciones' in columnas_por_tabla and 'formato' not in columnas_por_tabla['funciones']:
        alter_statements.append("ALTER TABLE funciones ADD COLUMN formato VARCHAR(10) DEFAULT '2D'")
    if 'asientos' in columnas_por_tabla and 'tipo' not in columnas_por_tabla['asientos']:
        alter_statements.append("ALTER TABLE asientos ADD COLUMN tipo VARCHAR(10) NOT NULL DEFAULT 'normal'")
        alter_statements.append("UPDATE asientos SET tipo = 'vip' WHERE fila IN ('I', 'J')")
    if 'tiquetes' in columnas_por_tabla and 'nombre_cliente' not in columnas_por_tabla['tiquetes']:
        alter_statements.append("ALTER TABLE tiquetes ADD COLUMN nombre_cliente VARCHAR(100) NULL")
    for statement in alter_statements:
        db.session.execute(text(statement))
    if alter_statements:
        db.session.commit()
        print("Esquema actualizado para compatibilidad.")

def normalizar_catalogo():
    cambios = False
    for pelicula in Pelicula.query.all():
        poster_canonico = POSTERS_CANONICOS.get((pelicula.titulo or '').strip().lower())
        if poster_canonico and pelicula.imagen_url != poster_canonico:
            pelicula.imagen_url = poster_canonico
            cambios = True
    if cambios:
        db.session.commit()
        print("Catálogo normalizado.")

# ============================================================
#  PÁGINAS PÚBLICAS
# ============================================================
@app.route('/')
def index():
    return render_template('index.html',
                           usuario=session.get('nombre'),
                           logueado='usuario_id' in session,
                           rol=session.get('rol'))

@app.route('/resultado')
def resultado():
    return render_template('resultado.html',
                           logueado='usuario_id' in session,
                           usuario=session.get('nombre'))

@app.route('/validar')
def validar():
    return render_template('consultar.html',
                           logueado='usuario_id' in session,
                           usuario=session.get('nombre'))

@app.route('/pago')
def pago():
    return render_template('pago.html',
                           logueado='usuario_id' in session,
                           usuario=session.get('nombre'))

@app.route('/asientos')
def asientos():
    return render_template('asientos.html',
                           logueado='usuario_id' in session,
                           usuario=session.get('nombre'))

@app.route('/pelicula/<int:pid>')
def detalle_pelicula(pid):
    p = Pelicula.query.get_or_404(pid)
    return render_template('detalle_pelicula.html',
                           pelicula=p,
                           logueado='usuario_id' in session,
                           usuario=session.get('nombre'),
                           rol=session.get('rol'))

# ============================================================
#  AUTH
# ============================================================
@app.route('/login')
def login_page():
    if 'usuario_id' in session:
        return redirect('/')
    return render_template('login.html')

@app.route('/registro-usuario')
def registro_usuario_page():
    if 'usuario_id' in session:
        return redirect('/')
    return render_template('registro_usuario.html')

@app.route('/historial')
@login_required
def historial():
    return render_template('historial.html',
                           usuario=session.get('nombre'),
                           logueado=True)

@app.route('/perfil')
@login_required
def perfil():
    if session.get('rol') == 'admin':
        return redirect('/admin/panel')
    return render_template('perfil.html',
                           usuario=session.get('nombre'),
                           logueado=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/auth/registro', methods=['POST'])
def api_registro():
    data     = request.get_json()
    nombre   = data.get('nombre', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    telefono = data.get('telefono', '').strip()
    if not nombre or not email or not password:
        return api_response({'error': 'Todos los campos son obligatorios'}, 400)
    if len(password) < 6:
        return api_response({'error': 'La contraseña debe tener al menos 6 caracteres'}, 400)
    if Usuario.query.filter_by(email=email).first():
        return api_response({'error': 'Ya existe una cuenta con ese correo'}, 409)
    u = Usuario(nombre=nombre, email=email,
                contrasena=hash_password(password),
                telefono=telefono, rol='cliente')
    db.session.add(u)
    db.session.commit()
    correo_enviado, correo_estado = enviar_correo_bienvenida(u.email, u.nombre)
    session['usuario_id'] = u.id
    session['nombre']     = u.nombre
    session['rol']        = u.rol
    return api_response({
        'mensaje': 'Cuenta creada',
        'nombre': u.nombre,
        'correo_bienvenida': correo_enviado,
        'correo_estado': correo_estado
    }, 201)

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    u = Usuario.query.filter_by(email=email).first()
    if not u or not check_password(password, u.contrasena):
        return api_response({'error': 'Correo o contraseña incorrectos'}, 401)
    session['usuario_id'] = u.id
    session['nombre']     = u.nombre
    session['rol']        = u.rol
    return api_response({'mensaje': 'Bienvenido', 'nombre': u.nombre, 'rol': u.rol})

@app.route('/api/auth/me', methods=['GET'])
def api_me():
    if 'usuario_id' not in session:
        return api_response({'logueado': False})
    u = Usuario.query.get(session['usuario_id'])
    return api_response({
        'logueado': True,
        'nombre': session['nombre'],
        'rol': session['rol'],
        'email': u.email if u else '',
        'telefono': u.telefono if u else ''
    })

@app.route('/api/auth/perfil', methods=['PUT'])
@login_required
def actualizar_perfil():
    data = request.get_json()
    u = Usuario.query.get(session['usuario_id'])
    if data.get('nombre'):
        u.nombre = data['nombre'].strip()
        session['nombre'] = u.nombre
    if data.get('telefono') is not None:
        u.telefono = data['telefono'].strip()
    if data.get('password_nueva') and data.get('password_actual'):
        if not check_password(data['password_actual'], u.contrasena):
            return api_response({'error': 'Contraseña actual incorrecta'}, 400)
        if len(data['password_nueva']) < 6:
            return api_response({'error': 'La nueva contraseña debe tener al menos 6 caracteres'}, 400)
        u.contrasena = hash_password(data['password_nueva'])
    db.session.commit()
    return api_response({'mensaje': 'Perfil actualizado'})

# ============================================================
#  ADMIN
# ============================================================
@app.route('/gestion-interna')
def admin_login_page():
    if session.get('rol') == 'admin':
        return redirect('/admin/panel')
    return render_template('admin_login.html')

@app.route('/admin/panel')
@admin_required
def admin_panel():
    return render_template('admin_panel.html', admin_nombre=session.get('nombre'))

@app.route('/api/auth/admin-login', methods=['POST'])
def api_admin_login():
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    u = Usuario.query.filter_by(email=email, rol='admin').first()
    if not u or not check_password(password, u.contrasena):
        return api_response({'error': 'Credenciales incorrectas'}, 401)
    session['usuario_id'] = u.id
    session['nombre']     = u.nombre
    session['rol']        = 'admin'
    return api_response({'mensaje': 'Acceso concedido'})

# ============================================================
#  API PELÍCULAS
# ============================================================
@app.route('/api/peliculas', methods=['GET'])
def get_peliculas():
    peliculas = Pelicula.query.filter_by(estado='activa').all()
    return api_response([{
        'id': p.id, 'titulo': p.titulo, 'descripcion': p.descripcion,
        'duracion': p.duracion, 'genero': p.genero,
        'clasificacion': p.clasificacion, 'imagen_url': p.imagen_url,
        'trailer_url': p.trailer_url
    } for p in peliculas], cache_seconds=30)

@app.route('/api/admin/peliculas', methods=['GET'])
@admin_required
def get_peliculas_admin():
    peliculas = Pelicula.query.filter_by(estado='activa').order_by(Pelicula.titulo.asc()).all()
    hoy = date.today()
    return api_response([{
        'id': p.id, 'titulo': p.titulo, 'descripcion': p.descripcion,
        'duracion': p.duracion, 'genero': p.genero,
        'clasificacion': p.clasificacion, 'imagen_url': p.imagen_url,
        'trailer_url': p.trailer_url,
        'funciones': [{
            'id': f.id, 'fecha': str(f.fecha), 'hora': str(f.hora),
            'sala': f.sala, 'precio': float(f.precio), 'formato': f.formato
        } for f in sorted(
            [fn for fn in p.funciones if fn.estado == 'disponible' and fn.fecha >= hoy],
            key=lambda fn: (fn.fecha, fn.hora)
        )]
    } for p in peliculas], cache_seconds=5)

@app.route('/api/peliculas', methods=['POST'])
@admin_required
def crear_pelicula():
    data = request.get_json()
    if not data.get('titulo') or not data.get('duracion'):
        return api_response({'error': 'Título y duración son obligatorios'}, 400)
    p = Pelicula(
        titulo=data['titulo'].strip(),
        descripcion=data.get('descripcion', '').strip(),
        duracion=int(data['duracion']),
        genero=data.get('genero', '').strip(),
        clasificacion=data.get('clasificacion', 'ATP'),
        imagen_url=data.get('imagen_url', '').strip() or None,
        trailer_url=data.get('trailer_url', '').strip() or None
    )
    db.session.add(p)
    db.session.flush()
    _generar_funciones_para(p.id)
    db.session.commit()
    return api_response({'mensaje': 'Película creada', 'id': p.id}, 201)

@app.route('/api/peliculas/<int:pid>', methods=['PUT'])
@admin_required
def editar_pelicula(pid):
    p = Pelicula.query.get_or_404(pid)
    data = request.get_json()
    for campo in ['titulo','descripcion','duracion','genero','clasificacion','imagen_url','trailer_url','estado']:
        if campo in data:
            setattr(p, campo, data[campo])
    db.session.commit()
    return api_response({'mensaje': 'Película actualizada'})

@app.route('/api/peliculas/<int:pid>', methods=['DELETE'])
@admin_required
def eliminar_pelicula(pid):
    p = Pelicula.query.get_or_404(pid)
    p.estado = 'inactiva'
    db.session.commit()
    return api_response({'mensaje': 'Película desactivada'})

# ============================================================
#  API CARTELERA
# ============================================================
@app.route('/api/cartelera', methods=['GET'])
def api_cartelera():
    hoy    = date.today()
    genero = request.args.get('genero')
    peliculas = Pelicula.query.filter_by(estado='activa')
    if genero:
        peliculas = peliculas.filter(Pelicula.genero.ilike(f'%{genero}%'))
    peliculas = peliculas.all()

    cartelera_por_titulo = {}
    for p in peliculas:
        funciones = [
            {
                'id': f.id, 'pelicula_id': p.id, 'pelicula': p.titulo,
                'fecha': str(f.fecha), 'hora': str(f.hora),
                'sala': f.sala, 'precio': float(f.precio),
                'formato': f.formato, 'pasado': f.fecha < hoy
            }
            for f in p.funciones
            if f.estado == 'disponible' and f.fecha >= hoy
        ]
        if not funciones:
            continue
        item  = {
            'id': p.id, 'titulo': p.titulo, 'descripcion': p.descripcion,
            'duracion': p.duracion, 'genero': p.genero,
            'clasificacion': p.clasificacion, 'imagen_url': p.imagen_url,
            'trailer_url': p.trailer_url, 'funciones': funciones
        }
        clave    = (p.titulo or '').strip().lower()
        existente = cartelera_por_titulo.get(clave)
        if not existente:
            cartelera_por_titulo[clave] = item
            continue
        existente['funciones'].extend(funciones)
        existente['funciones'].sort(key=lambda f: (f['fecha'], f['hora']))
        if not existente.get('imagen_url') and item.get('imagen_url'):
            existente['imagen_url'] = item['imagen_url']
        if not existente.get('descripcion') and item.get('descripcion'):
            existente['descripcion'] = item['descripcion']

    resultado = sorted(
        cartelera_por_titulo.values(),
        key=lambda p: (p['titulo'].lower(), p['id'])
    )
    return api_response(resultado, cache_seconds=20)

# ============================================================
#  API FUNCIONES
# ============================================================
@app.route('/api/funciones', methods=['GET'])
def get_funciones():
    hoy = date.today()
    funciones = Funcion.query.filter(
        Funcion.estado == 'disponible',
        Funcion.fecha >= hoy
    ).all()
    return api_response([{
        'id': f.id, 'pelicula_id': f.pelicula_id,
        'pelicula': f.pelicula.titulo,
        'fecha': str(f.fecha), 'hora': str(f.hora),
        'sala': f.sala, 'precio': float(f.precio), 'formato': f.formato
    } for f in funciones])

@app.route('/api/funciones', methods=['POST'])
@admin_required
def crear_funcion():
    data = request.get_json()
    sala = data.get('sala', 'Sala Principal')
    if Funcion.query.filter_by(sala=sala, fecha=data['fecha'], hora=data['hora']).first():
        return api_response({'error': 'Ya existe una función en esa sala, fecha y hora'}, 409)
    f = Funcion(
        pelicula_id=data['pelicula_id'],
        fecha=data['fecha'], hora=data['hora'],
        sala=sala, precio=data['precio'],
        formato=data.get('formato', '2D')
    )
    db.session.add(f)
    db.session.commit()
    return api_response({'mensaje': 'Función creada', 'id': f.id}, 201)

@app.route('/api/funciones/<int:fid>', methods=['DELETE'])
@admin_required
def eliminar_funcion(fid):
    f = Funcion.query.get_or_404(fid)
    db.session.delete(f)
    db.session.commit()
    return api_response({'mensaje': 'Función eliminada'})

# ============================================================
#  API ASIENTOS
# ============================================================
@app.route('/api/funciones/<int:fid>/asientos', methods=['GET'])
def get_asientos_funcion(fid):
    vendidos_ids = {r[0] for r in
        db.session.query(DetalleTiquete.asiento_id)
        .join(Tiquete)
        .filter(Tiquete.funcion_id == fid, Tiquete.estado.in_(['activo','usado']))
        .all()
    }
    asientos = Asiento.query.filter_by(estado='activo').order_by(Asiento.fila, Asiento.columna).all()
    return api_response([{
        'id': a.id, 'numero': a.numero, 'fila': a.fila,
        'columna': a.columna, 'tipo': a.tipo,
        'ocupado': a.id in vendidos_ids
    } for a in asientos])

# ============================================================
#  API COMPRA
# ============================================================
@app.route('/api/tiquetes', methods=['POST'])
def comprar_tiquete():
    data           = request.get_json()
    funcion_id     = data.get('funcion_id')
    asientos_ids   = data.get('asientos', [])
    nombre_cliente = data.get('nombre_cliente', session.get('nombre', 'Invitado'))

    if not funcion_id or not asientos_ids:
        return api_response({'error': 'Datos incompletos'}, 400)

    funcion = Funcion.query.get_or_404(funcion_id)

    ocupados = db.session.query(DetalleTiquete.asiento_id).join(Tiquete).filter(
        Tiquete.funcion_id == funcion_id,
        Tiquete.estado.in_(['activo','usado']),
        DetalleTiquete.asiento_id.in_(asientos_ids)
    ).all()
    if ocupados:
        return api_response({'error': f'Asientos ocupados: {[r[0] for r in ocupados]}'}, 409)

    asientos_obj = Asiento.query.filter(Asiento.id.in_(asientos_ids)).all()
    precio_base  = float(funcion.precio)
    total        = sum(precio_base * (1.3 if a.tipo == 'vip' else 1.0) for a in asientos_obj)

    codigo  = str(uuid.uuid4()).replace('-','').upper()[:12]
    tiquete = Tiquete(
        codigo=codigo, funcion_id=funcion_id,
        usuario_id=session.get('usuario_id'),
        nombre_cliente=nombre_cliente,
        total=round(total, 2)
    )
    db.session.add(tiquete)
    db.session.flush()

    for a in asientos_obj:
        precio_unit = precio_base * (1.3 if a.tipo == 'vip' else 1.0)
        db.session.add(DetalleTiquete(
            tiquete_id=tiquete.id,
            asiento_id=a.id,
            precio_unitario=round(precio_unit, 2)
        ))
    db.session.commit()

    return api_response({
        'mensaje': '¡Compra exitosa!',
        'codigo': codigo,
        'total': round(total, 2),
        'qr': generar_qr(codigo),
        'pelicula': funcion.pelicula.titulo,
        'fecha': str(funcion.fecha),
        'hora': str(funcion.hora),
        'sala': funcion.sala,
        'asientos': len(asientos_ids)
    }, 201)

# ============================================================
#  API CANCELAR TIQUETE
# ============================================================
@app.route('/api/tiquetes/<codigo>/cancelar', methods=['POST'])
@login_required
def cancelar_tiquete(codigo):
    t = Tiquete.query.filter_by(codigo=codigo, usuario_id=session['usuario_id']).first_or_404()
    if t.estado != 'activo':
        return api_response({'error': 'Solo se pueden cancelar tiquetes activos'}, 400)
    funcion_dt = datetime.combine(t.funcion.fecha, t.funcion.hora)
    if funcion_dt - datetime.utcnow() < timedelta(hours=2):
        return api_response({'error': 'No se puede cancelar con menos de 2 horas de anticipación'}, 400)
    t.estado = 'cancelado'
    db.session.commit()
    return api_response({'mensaje': 'Tiquete cancelado'})

# ============================================================
#  API HISTORIAL
# ============================================================
@app.route('/api/mis-tiquetes', methods=['GET'])
@login_required
def mis_tiquetes():
    tiquetes = Tiquete.query.filter_by(usuario_id=session['usuario_id'])\
        .order_by(Tiquete.fecha_compra.desc()).all()
    return api_response([{
        'codigo':       t.codigo,
        'pelicula':     t.funcion.pelicula.titulo,
        'imagen':       t.funcion.pelicula.imagen_url,
        'fecha':        str(t.funcion.fecha),
        'hora':         str(t.funcion.hora),
        'sala':         t.funcion.sala,
        'formato':      t.funcion.formato,
        'asientos':     [f"{d.asiento.fila}{d.asiento.columna}" for d in t.detalles],
        'total':        float(t.total),
        'estado':       t.estado,
        'fecha_compra': t.fecha_compra.strftime('%d/%m/%Y %H:%M'),
        'qr':           generar_qr(t.codigo),
        'cancelable':   t.estado == 'activo' and datetime.combine(t.funcion.fecha, t.funcion.hora) - datetime.utcnow() > timedelta(hours=2)
    } for t in tiquetes])

# ============================================================
#  API VALIDAR TIQUETE
# ============================================================
@app.route('/api/tiquetes/validar', methods=['POST'])
def validar_tiquete():
    data   = request.get_json()
    codigo = data.get('codigo','').strip().upper()
    if not codigo:
        return api_response({'estado':'invalido','mensaje':'Código vacío'}, 400)
    t = Tiquete.query.filter_by(codigo=codigo).first()
    if not t:
        return api_response({'estado':'invalido','mensaje':'Código no encontrado'}, 404)
    if t.estado == 'usado':
        return api_response({'estado':'usado','mensaje':'Este tiquete ya fue usado', 'fecha': str(t.funcion.fecha)})
    if t.estado == 'cancelado':
        return api_response({'estado':'invalido','mensaje':'Tiquete cancelado'})
    t.estado = 'usado'
    db.session.commit()
    return api_response({
        'estado': 'valido',
        'mensaje': '✅ Acceso permitido',
        'pelicula': t.funcion.pelicula.titulo,
        'funcion': str(t.funcion.fecha) + ' ' + str(t.funcion.hora),
        'sala': t.funcion.sala,
        'asientos': len(t.detalles)
    })

# ============================================================
#  API DASHBOARD ADMIN
# ============================================================
@app.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def dashboard():
    from sqlalchemy import func
    hoy = date.today()
    total_ventas = db.session.query(func.sum(Tiquete.total))\
        .filter(Tiquete.estado != 'cancelado').scalar() or 0
    tiquetes_hoy = Tiquete.query.filter(
        db.func.date(Tiquete.fecha_compra) == hoy).count()
    peliculas_activas = Pelicula.query.filter_by(estado='activa').count()
    funciones_hoy     = Funcion.query.filter_by(fecha=hoy, estado='disponible').count()
    ocupacion = db.session.query(
        Funcion.id, Pelicula.titulo, Funcion.fecha, Funcion.hora, Funcion.sala,
        func.count(DetalleTiquete.id).label('vendidos')
    ).join(Tiquete, Tiquete.funcion_id == Funcion.id)\
     .join(DetalleTiquete, DetalleTiquete.tiquete_id == Tiquete.id)\
     .join(Pelicula, Pelicula.id == Funcion.pelicula_id)\
     .filter(Tiquete.estado != 'cancelado', Funcion.fecha >= hoy)\
     .group_by(Funcion.id)\
     .order_by(Funcion.fecha, Funcion.hora)\
     .all()
    ventas_genero = db.session.query(
        Pelicula.genero,
        func.count(DetalleTiquete.id).label('cantidad')
    ).join(Funcion, Funcion.pelicula_id == Pelicula.id)\
     .join(Tiquete, Tiquete.funcion_id == Funcion.id)\
     .join(DetalleTiquete, DetalleTiquete.tiquete_id == Tiquete.id)\
     .filter(Tiquete.estado != 'cancelado')\
     .group_by(Pelicula.genero).all()

    return api_response({
        'total_ventas': float(total_ventas),
        'tiquetes_hoy': tiquetes_hoy,
        'peliculas_activas': peliculas_activas,
        'funciones_hoy': funciones_hoy,
        'ocupacion_por_funcion': [
            {'funcion_id': r[0], 'pelicula': r[1], 'fecha': str(r[2]),
             'hora': str(r[3]), 'sala': r[4], 'vendidos': r[5], 'disponibles': 150 - r[5]}
            for r in ocupacion
        ],
        'ventas_por_genero': [{'genero': r[0] or 'Sin género', 'cantidad': r[1]} for r in ventas_genero]
    })

@app.route('/api/admin/usuarios', methods=['GET'])
@admin_required
def listar_usuarios():
    usuarios = Usuario.query.filter_by(rol='cliente').order_by(Usuario.fecha_creacion.desc()).all()
    return api_response([{
        'id': u.id, 'nombre': u.nombre, 'email': u.email,
        'telefono': u.telefono or '—',
        'fecha': u.fecha_creacion.strftime('%d/%m/%Y'),
        'tiquetes': len(u.tiquetes)
    } for u in usuarios])

@app.route('/api/admin/usuarios/<int:uid>', methods=['DELETE'])
@admin_required
def eliminar_usuario_admin(uid):
    u = Usuario.query.get_or_404(uid)
    if u.rol == 'admin':
        return api_response({'error': 'No se pueden eliminar cuentas administradoras'}, 403)
    if session.get('usuario_id') == u.id:
        return api_response({'error': 'No puedes eliminar tu propia cuenta'}, 400)
    db.session.delete(u)
    db.session.commit()
    return api_response({'mensaje': 'Cuenta eliminada'})

# ============================================================
#  FUNCIONES ALEATORIAS (admin)
# ============================================================
def _generar_funciones_para(pelicula_id, n=4):
    from datetime import time as dtime
    salas    = ['Sala Principal', 'Sala 2', 'Sala 3', 'Sala VIP']
    precios  = [12000, 15000, 18000, 22000]
    formatos = ['2D', '3D', 'IMAX']
    hoy = date.today()
    for _ in range(n):
        fecha = hoy + timedelta(days=random.randint(0, 7))
        hora  = dtime(random.randint(12, 22), random.choice([0, 15, 30, 45]))
        db.session.add(Funcion(
            pelicula_id=pelicula_id, fecha=fecha, hora=hora,
            sala=random.choice(salas),
            precio=random.choice(precios),
            formato=random.choice(formatos)
        ))

@app.route('/api/admin/funciones-aleatorias', methods=['POST'])
@admin_required
def funciones_aleatorias():
    for peli in Pelicula.query.filter_by(estado='activa').all():
        for f in list(peli.funciones):
            db.session.delete(f)
        db.session.flush()
        _generar_funciones_para(peli.id)
    db.session.commit()
    return api_response({'mensaje': 'Funciones regeneradas'})

# ============================================================
#  INICIALIZACIÓN – corre con gunicorn Y con python app.py
# ============================================================
with app.app_context():
    db.create_all()
    asegurar_columnas_compatibles()
    normalizar_catalogo()
    if not Usuario.query.filter_by(email='admin@cine.com').first():
        db.session.add(Usuario(
            nombre='Administrador', email='admin@cine.com',
            contrasena=hash_password('admin123'), rol='admin'
        ))
        print("Admin creado: admin@cine.com / admin123")
    if Pelicula.query.count() == 0:
        seeds = [
            ('Spider-Man: No Way Home', 'Peter Parker abre el multiverso.', 148, 'Acción', '+13',
             'https://image.tmdb.org/t/p/w500/1g0dhYtq4irTY1GPXvft6k4YLjm.jpg'),
            ('Avengers: Endgame', 'Los Vengadores restauran el universo.', 181, 'Acción', '+13',
             'https://image.tmdb.org/t/p/w500/or06FN3Dka5tukK1e9sl16pB3iy.jpg'),
            ('The Dark Knight', 'Batman enfrenta al Joker en Gotham.', 152, 'Acción', '+16',
             'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg'),
            ('Dune: Parte Dos', 'Paul Atreides lidera a los Fremen.', 166, 'Ciencia Ficción', '+13',
             'https://image.tmdb.org/t/p/w500/8b8R8l88Qje9dn9OE8PY05Nxl1X.jpg'),
            ('Oppenheimer', 'El padre de la bomba atómica.', 180, 'Drama', '+13',
             'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg'),
            ('Deadpool & Wolverine', 'Dos antihéroes en el multiverso.', 127, 'Acción', '+18',
             'https://image.tmdb.org/t/p/w500/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg'),
            ('Inside Out 2', 'Las emociones de Riley adolescente.', 100, 'Animación', 'ATP',
             'https://image.tmdb.org/t/p/w500/vpnVM9B6NMmQpWeZvzLvDESb2QY.jpg'),
            ('Toy Story 4', 'Woody ayuda a Forky a encontrar su lugar.', 100, 'Animación', 'ATP',
             'https://image.tmdb.org/t/p/w500/w9kR8qbmQ01HwnvK4alvnQ2ca0L.jpg'),
            ('John Wick 3', 'John Wick con precio por su cabeza.', 131, 'Acción', '+18',
             'https://image.tmdb.org/t/p/w500/ziEuG1essDuWuC5lpWUaw1uXY2O.jpg'),
            ('Alien: Romulus', 'Jóvenes enfrentan lo más aterrador.', 119, 'Terror', '+16',
             'https://image.tmdb.org/t/p/w500/b33nnKl1GSFbao4l3fZDDqsMx0F.jpg'),
        ]
        for titulo, desc, dur, genero, clasif, img in seeds:
            p = Pelicula(titulo=titulo, descripcion=desc, duracion=dur,
                         genero=genero, clasificacion=clasif, imagen_url=img)
            db.session.add(p)
            db.session.flush()
            _generar_funciones_para(p.id, n=random.randint(3, 5))
        print("Películas seed insertadas.")
    if Asiento.query.count() == 0:
        filas    = list('ABCDEFGHIJ')
        columnas = range(1, 16)
        num = 1
        for fila in filas:
            for col in columnas:
                tipo = 'vip' if fila in ('I', 'J') else 'normal'
                db.session.add(Asiento(numero=num, fila=fila, columna=col, tipo=tipo))
                num += 1
        print("150 asientos precargados (filas I-J son VIP).")
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5000)