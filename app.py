import hashlib
import hmac
import sqlite3
import smtplib
from email.mime.text import MIMEText
import random
import string
from datetime import date, datetime
import io
import os
import re
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y CONSTANTES
# ---------------------------------------------------------
st.set_page_config(
    page_title="Tablero de Control - La Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

def buscar_logo_local():
    dir_script = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    for n in ["logo_terminal.png", "logo_terminal.jpg", "logo.png", "logo.jpg"]:
        ruta = os.path.join(dir_script, n)
        if os.path.exists(ruta):
            return ruta
    return None

LOGO_PATH = buscar_logo_local()
DB_PATH = "usuarios_app.db"
JSON_USERS_FILE = "usuarios.json"

TODAS_LAS_PESTANIAS = [
    "Tablero", "Programa Anual", "Métricas", "Indicadores de Gestión",
    "Histórico", "Alertas y Edición", "Oficios", "Informes"
]

TODAS_LAS_SUBPESTANIAS = [
    "Planes Programados (Vigencia 2026)",
    "Planes Finalizados (Cierre Mensual + Histórico Completo)",
    "Programa Anual de Auditoría (PAA)",
    "Hallazgos Finalizados (% Hallazgo: Programados vs Finalizados 2026)",
    "Análisis por Planes de Acción",
    "Análisis por Hallazgos Únicos"
]

TODOS_LOS_ENTORNOS = ["Auditoría Interna", "Contraloría de Bogotá"]

USUARIOS_AMARILLOS = [
    'admin', 'diego.vasquez@terminaldetransporte.gov.co', 'manuel.gutierrez', 
    'manuel.gutierrez@terminaldetransporte.gov.co', 'omar.diaz', 'omar.diaz@terminaldetransporte.gov.co'
]

CATALOGO_OFICIAL_AREAS = [
    "DIRECCIÓN DE GESTIÓN FINANCIERA", "DIRECCIÓN DE RECURSOS FÍSICOS Y NEGOCIOS",
    "DIRECCIÓN DE GESTIÓN HUMANA", "DIRECCIÓN DE RECURSOS TECNOLÓGICOS",
    "DIRECCIÓN DE SEGURIDAD OPERACIONAL", "DIRECCIÓN DE SERVICIO AL TRANSPORTADOR",
    "DIRECCIÓN DE INFRAESTRUCTURA", "SUBGERENCIA JURÍDICA", "SUBGERENCIA CORPORATIVA",
    "SUBGERENCIA DE SERVICIOS OPERACIONALES E INFRAESTRUCTURA",
    "SUBGERENCIA DE PLANEACIÓN Y PROYECTOS", "OFICINA DE AUDITORÍA INTERNA"
]

# ---------------------------------------------------------
# FUNCIONES AUXILIARES Y PERSISTENCIA
# ---------------------------------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_password(password, hashed):
    return hmac.compare_digest(hash_password(password), str(hashed).strip())

def parsear_fecha_estricta(val):
    if pd.isna(val): return pd.NaT
    if isinstance(val, (datetime, pd.Timestamp, date)): return pd.to_datetime(val)
    val_str = str(val).strip().lower()
    if val_str in ["nan", "none", "nat", "", "cierre", "cierre dd/mm/a", "cierre dd/mm/aa", "inicio", "inicio dd/mm/a"]: return pd.NaT
    try:
        val_num = float(val_str)
        if val_num > 30000: return pd.to_datetime(val_num, unit='D', origin='1899-12-30')
    except Exception: pass
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", val_str)
    if match:
        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if y < 100: y += 2000
        try: return pd.Timestamp(year=y, month=m, day=d)
        except Exception: pass
    return pd.to_datetime(val_str, dayfirst=True, errors="coerce")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT,
            autorizado INTEGER DEFAULT 1, token_recuperacion TEXT,
            perm_pestañas TEXT DEFAULT 'TODOS', perm_subpestañas TEXT DEFAULT 'TODOS',
            perm_entornos TEXT DEFAULT 'TODOS', requiere_2fa INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    for col in ["requiere_2fa INTEGER DEFAULT 1", "perm_subpestañas TEXT DEFAULT 'TODOS'"]:
        try:
            c.execute(f"ALTER TABLE usuarios ADD COLUMN {col}")
            conn.commit()
        except sqlite3.OperationalError: pass

    pw_defecto = hash_password("123456")
    usuarios_base_raw = [
        ('edgar.ortiz', 'edgar.ortiz@terminaldetransporte.gov'), ('manuel.cifuentes', 'manuel.cifuentes@terminaldetransporte.gov.co'),
        ('eduardo.gonzalez', 'eduardo.gonzalez@terminaldetransporte.gov.co'), ('oscar.garzon', 'oscar.garzon@terminaldetransporte.gov.co'),
        ('manuel.santamaria', 'manuel.santamaria@terminaldetransporte.gov.co'), ('carlos.salcedo', 'carlos.salcedo@terminaldetransporte.gov.co'),
        ('juan.alviz', 'juan.alviz@terminaldetransporte.gov.co'), ('julio.mosquera', 'julio.mosquera@terminaldetransporte.gov.co'),
        ('marcela.angarita', 'marcela.angarita@terminaldetransporte.gov.co'), ('roberto.bermudez', 'roberto.bermudez@terminaldetransporte.gov.co'),
        ('miguel.salina', 'miguel.salina@terminaldetransporte.gov.co'), ('oscar.castañeda', 'oscar.castaneda@terminaldetransporte.gov.co'),
        ('andres.panqueva', 'andres.panqueva@terminaldetransporte.gov.co'), ('christian.pardo', 'christian.pardo@terminaldetransporte.gov.co'),
        ('diana.ortiz', 'diana.ortiz@terminaldetransporte.gov.co'), ('andrea.lievano', 'andrea.lievano@terminaldetransporte.gov.co'),
        ('william.camargo', 'william.camargo@terminaldetransporte.gov.co'), ('gerson.lugo', 'gerson.lugo@terminaldetransporte.gov.co'),
        ('leonardo.vasquez', 'leonardo.vasquez@terminaldetransporte.gov.co'), ('javier.veloza', 'javier.veloza@terminaldetransporte.gov.co'),
        ('manuel.salgado', 'manuel.salgado@terminaldetransporte.gov.co'), ('edgar.guzman', 'edgar.guzman@terminaldetransporte.gov.co'),
        ('carolina.bueno', 'carolina.bueno@terminaldetransporte.gov.co'), ('jenny.gomez', 'jenny.gomez@terminaldetransporte.gov.co'),
        ('paola.copete', 'paola.copete@terminaldetransporte.gov.co'), ('hugo.montoya', 'hugo.montoya@terminaldetransporte.gov.co'),
        ('admin', 'diego.vasquez@terminaldetransporte.gov.co'), ('diego.12', 'diego12vas@gmail.com'),
        ('fabian.silva', 'fabian.silva@terminaldetransporte.gov.co'), ('manuel.gutierrez', 'manuel.gutierrez@terminaldetransporte.gov.co'),
        ('omar.diaz', 'omar.diaz@terminaldetransporte.gov.co')
    ]
    usuarios_base = [
        (u, email, pw_defecto, 1, 'TODOS', 'TODOS', 'TODOS', 0 if (u in USUARIOS_AMARILLOS or email in USUARIOS_AMARILLOS) else 1)
        for u, email in usuarios_base_raw
    ]
    if os.path.exists(JSON_USERS_FILE):
        try:
            with open(JSON_USERS_FILE, "r", encoding="utf-8") as f:
                uj = json.load(f)
                if uj: usuarios_base = [(u["usuario"], u["email"], u["password_hash"], u.get("autorizado", 1), u.get("perm_pestañas", "TODOS"), u.get("perm_subpestañas", "TODOS"), u.get("perm_entornos", "TODOS"), 0 if (u["usuario"] in USUARIOS_AMARILLOS or u["email"] in USUARIOS_AMARILLOS) else 1) for u in uj]
        except Exception: pass

    c.executemany("INSERT OR IGNORE INTO usuarios VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [(u[0], u[1], u[2], u[3], None, u[4], u[5], u[6], u[7])])
    for item in USUARIOS_AMARILLOS:
        c.execute("UPDATE usuarios SET requiere_2fa = 0 WHERE LOWER(usuario) = ? OR LOWER(email) = ?", (item.lower(), item.lower()))
    conn.commit()
    conn.close()

init_db()

def obtener_usuarios_df():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT usuario, email, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa FROM usuarios", conn)
    conn.close()
    return df

def obtener_usuarios_excel_bytes():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        obtener_usuarios_df().to_excel(writer, index=False, sheet_name='Usuarios')
    return buf.getvalue()

def obtener_usuarios_json_bytes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT usuario, email, password_hash, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa FROM usuarios")
    rows = c.fetchall()
    conn.close()
    return json.dumps([{"usuario": r[0], "email": r[1], "password_hash": r[2], "autorizado": r[3], "perm_pestañas": r[4], "perm_subpestañas": r[5], "perm_entornos": r[6], "requiere_2fa": r[7]} for r in rows], indent=4, ensure_ascii=False).encode('utf-8')

def exportar_y_sincronizar_usuarios():
    with open(JSON_USERS_FILE, "w", encoding="utf-8") as f:
        f.write(obtener_usuarios_json_bytes().decode('utf-8'))

def actualizar_permisos_usuario(usuario, lista_pestañas, lista_subpestañas, lista_entornos):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET perm_pestañas = ?, perm_subpestañas = ?, perm_entornos = ? WHERE usuario = ?", (",".join(lista_pestañas) if lista_pestañas else "TODOS", ",".join(lista_subpestañas) if lista_subpestañas else "TODOS", ",".join(lista_entornos) if lista_entornos else "TODOS", usuario))
    conn.commit()
    conn.close()
    exportar_y_sincronizar_usuarios()

def guardar_o_actualizar_usuario(usuario, email, password, permisos_list, subpermisos_list, entornos_list, requiere_2fa=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO usuarios (usuario, email, password_hash, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa)
        VALUES (?, ?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(usuario) DO UPDATE SET email=excluded.email, password_hash=excluded.password_hash, autorizado=1, perm_pestañas=excluded.perm_pestañas, perm_subpestañas=excluded.perm_subpestañas, perm_entornos=excluded.perm_entornos, requiere_2fa=excluded.requiere_2fa
    ''', (usuario, email, hash_password(password), ",".join(permisos_list) if permisos_list else "TODOS", ",".join(subpermisos_list) if subpermisos_list else "TODOS", ",".join(entornos_list) if entornos_list else "TODOS", requiere_2fa))
    conn.commit()
    conn.close()
    exportar_y_sincronizar_usuarios()

def enviar_correo_token(email_destino, token):
    try:
        smtp_config = st.secrets.get("smtp", {})
        server_host, port = smtp_config.get("server", "smtp.gmail.com"), int(smtp_config.get("port", 587))
        remitente, password_remitente = smtp_config.get("user", ""), smtp_config.get("password", "")
        if not remitente or not password_remitente: return False
        msg = MIMEText(f"Hola,\n\nTu código de verificación de 6 dígitos para ingresar al sistema es: {token}\n\nSi no intentaste iniciar sesión, ignora este mensaje.")
        msg['Subject'], msg['From'], msg['To'] = "Código de Acceso de 6 Dígitos - Tablero La Terminal", remitente, email_destino
        with smtplib.SMTP(server_host, port) as server:
            server.starttls()
            server.login(remitente, password_remitente)
            server.sendmail(remitente, [email_destino], msg.as_string())
        return True
    except Exception: return False

def limpiar_nombre_area(texto):
    if not texto or pd.isna(texto): return ""
    txt = re.sub(r"\s+", " ", str(texto).upper().strip()).strip()
    if "SERVICIOS OPERACIONALES" in txt or "SERVICIOS OPERA" in txt: return "SUBGERENCIA DE SERVICIOS OPERACIONALES E INFRAESTRUCTURA"
    if "PLANEACIÓN Y PROYECTOS" in txt or "PLANEACIONYPROYECTOS" in txt or "PLANEACION Y PROYECTOS" in txt: return "SUBGERENCIA DE PLANEACIÓN Y PROYECTOS"
    if "CORPORATIVA" in txt and ("SUBGERENCIA" in txt or "SUB GERENCIA" in txt): return "SUBGERENCIA CORPORATIVA"
    if "JURÍDICA" in txt or "JURIDICA" in txt: return "SUBGERENCIA JURÍDICA"
    if "GESTIÓN HUMANA" in txt or "GESTION HUMANA" in txt: return "DIRECCIÓN DE GESTIÓN HUMANA"
    if "RECURSOS TECNOLÓGICOS" in txt or "RECURSOS TECNOLOGICOS" in txt: return "DIRECCIÓN DE RECURSOS TECNOLÓGICOS"
    if "GESTIÓN FINANCIERA" in txt or "GESTION FINANCIERA" in txt: return "DIRECCIÓN DE GESTIÓN FINANCIERA"
    if "RECURSOS FÍSICOS" in txt or "RECURSOS FISICOS" in txt: return "DIRECCIÓN DE RECURSOS FÍSICOS Y NEGOCIOS"
    if "SEGURIDAD OPERACIONAL" in txt: return "DIRECCIÓN DE SEGURIDAD OPERACIONAL"
    if "SERVICIO AL TRANSPORTADOR" in txt: return "DIRECCIÓN DE SERVICIO AL TRANSPORTADOR"
    if "INFRAESTRUCTURA" in txt and ("DIRECCIÓN" in txt or "DIRECCION" in txt): return "DIRECCIÓN DE INFRAESTRUCTURA"
    if "AUDITORÍA INTERNA" in txt or "AUDITORIA INTERNA" in txt: return "OFICINA DE AUDITORÍA INTERNA"
    return txt

def extraer_sub_areas_individuales(val):
    if pd.isna(val): return []
    txt = re.sub(r"SUB GERENCIA", "SUBGERENCIA", re.sub(r"SUBGERENCIAJ\s*URÍDICA|SUBGERENCIAJURIDICA", "SUBGERENCIA JURÍDICA", str(val).upper().strip()))
    txt_norm = txt.replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U")
    areas = [a for a in sorted(CATALOGO_OFICIAL_AREAS, key=len, reverse=True) if a.replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U") in txt_norm]
    if not areas:
        for p in re.split(r"[/,\n\r]+", txt):
            p_l = limpiar_nombre_area(p)
            if p_l and p_l.lower() not in ["nan", "none"]: areas.append(p_l)
    res = [a for a in CATALOGO_OFICIAL_AREAS if a in areas]
    for a in areas:
        if a not in res: res.append(a)
    return res

# ---------------------------------------------------------
# SISTEMA DE LOGIN
# ---------------------------------------------------------
def validar_login():
    for k in ["autenticado", "usuario_actual", "permisos_usuario", "permisos_subpestañas", "permisos_entornos", "paso_login", "login_temp_data"]:
        if k not in st.session_state:
            st.session_state[k] = False if k == "autenticado" else ("" if k == "usuario_actual" else (1 if k == "paso_login" else ({} if k == "login_temp_data" else [])))

    if not st.session_state["autenticado"]:
        login_container = st.empty()
        with login_container.container():
            st.markdown("<style>button{background-color:#7AB800!important;color:#FFF!important;font-weight:bold!important;border-radius:6px!important}</style>", unsafe_allow_html=True)
            _, col_main, _ = st.columns([1, 1.8, 1])
            with col_main:
                if LOGO_PATH: st.image(LOGO_PATH, use_container_width=True)
                else: st.markdown("<h1 style='text-align: center; color: #0077C8;'>🚌 LA TERMINAL</h1>", unsafe_allow_html=True)
                st.markdown("<h4 style='text-align: center; color: #0077C8;'>Tablero de Control y Gestión</h4>### 🔒 Acceso Restringido", unsafe_allow_html=True)

                if st.session_state["paso_login"] == 1:
                    u_in = st.text_input("Usuario o Correo Electrónico", key="user_login_input").strip().lower()
                    if st.button("Continuar ➡️", type="primary", use_container_width=True):
                        if not u_in: st.warning("⚠️ Por favor ingresa tu usuario o correo.")
                        else:
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute('SELECT usuario, email, password_hash, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa FROM usuarios WHERE LOWER(usuario) = ? OR LOWER(email) = ?', (u_in, u_in))
                            row = c.fetchone()
                            conn.close()
                            if not row: st.error("❌ El usuario o correo no se encuentra registrado.")
                            elif row[3] == 0: st.error("🚫 Tu usuario no está autorizado.")
                            else:
                                u_db, e_db, pw_h, aut, p_s, sub_s, ent_s, req_2fa = row
                                exento = (u_db.lower() in [x.lower() for x in USUARIOS_AMARILLOS]) or (e_db.lower() in [x.lower() for x in USUARIOS_AMARILLOS]) or (req_2fa == 0)
                                st.session_state["login_temp_data"] = {"usuario": u_db, "email": e_db, "pw_hash": pw_h, "perm_str": p_s, "sub_str": sub_s, "ent_str": ent_s, "requiere_2fa": 0 if exento else 1}
                                if exento: st.session_state["paso_login"] = "password"
                                else:
                                    token = "".join(random.choices(string.digits, k=6))
                                    conn = sqlite3.connect(DB_PATH)
                                    conn.cursor().execute("UPDATE usuarios SET token_recuperacion = ? WHERE usuario = ?", (token, u_db))
                                    conn.commit()
                                    conn.close()
                                    if enviar_correo_token(e_db, token): st.session_state["paso_login"] = "otp"
                                    else: st.error("❌ Error al enviar el correo.")
                                st.rerun()

                elif st.session_state["paso_login"] == "password":
                    u_data = st.session_state.get("login_temp_data", {})
                    st.info(f"👤 Usuario: **{u_data.get('usuario')}**")
                    p_in = st.text_input("Contraseña", type="password", key="pass_yellow_input")
                    if st.button("Iniciar Sesión 🚀", type="primary", use_container_width=True):
                        if verificar_password(p_in, u_data.get("pw_hash")):
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = u_data.get("usuario")
                            st.session_state["permisos_usuario"] = TODAS_LAS_PESTANIAS if (u_data.get("perm_str") == "TODOS" or u_data.get("usuario") == "admin") else [p.strip() for p in u_data.get("perm_str", "").split(",") if p.strip()]
                            st.session_state["permisos_subpestañas"] = TODAS_LAS_SUBPESTANIAS if (u_data.get("sub_str") == "TODOS" or u_data.get("usuario") == "admin") else [s.strip() for s in u_data.get("sub_str", "").split(",") if s.strip()]
                            st.session_state["permisos_entornos"] = TODOS_LOS_ENTORNOS if (u_data.get("ent_str") == "TODOS" or u_data.get("usuario") == "admin") else [e.strip() for e in u_data.get("ent_str", "").split(",") if e.strip()]
                            st.session_state["paso_login"] = 1
                            st.session_state["login_temp_data"] = {}
                            login_container.empty()
                            st.rerun()
                        else: st.error("❌ Contraseña incorrecta.")
                    if st.button("⬅ Cambiar de Usuario"): st.session_state["paso_login"] = 1; st.rerun()

                elif st.session_state["paso_login"] == "otp":
                    u_data = st.session_state.get("login_temp_data", {})
                    st.info(f"📧 Código enviado a: **{u_data.get('email')}**")
                    otp_in = st.text_input("Ingresa el código de 6 dígitos:", key="otp_code_input").strip()
                    if st.button("Verificar e Iniciar Sesión 🚀", type="primary", use_container_width=True):
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT token_recuperacion FROM usuarios WHERE usuario = ?", (u_data.get("usuario"),))
                        row = c.fetchone()
                        if row and row[0] == otp_in:
                            c.execute("UPDATE usuarios SET token_recuperacion = NULL WHERE usuario = ?", (u_data.get("usuario"),))
                            conn.commit()
                            conn.close()
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = u_data.get("usuario")
                            st.session_state["permisos_usuario"] = TODAS_LAS_PESTANIAS if (u_data.get("perm_str") == "TODOS" or u_data.get("usuario") == "admin") else [p.strip() for p in u_data.get("perm_str", "").split(",") if p.strip()]
                            st.session_state["permisos_subpestañas"] = TODAS_LAS_SUBPESTANIAS if (u_data.get("sub_str") == "TODOS" or u_data.get("usuario") == "admin") else [s.strip() for s in u_data.get("sub_str", "").split(",") if s.strip()]
                            st.session_state["permisos_entornos"] = TODOS_LOS_ENTORNOS if (u_data.get("ent_str") == "TODOS" or u_data.get("usuario") == "admin") else [e.strip() for e in u_data.get("ent_str", "").split(",") if e.strip()]
                            st.session_state["paso_login"] = 1
                            st.session_state["login_temp_data"] = {}
                            login_container.empty()
                            st.rerun()
                        else: conn.close(); st.error("❌ Código de verificación incorrecto.")
                    if st.button("⬅️ Cambiar de Usuario"): st.session_state["paso_login"] = 1; st.rerun()
        return False
    return True

if not validar_login(): st.stop()

# ---------------------------------------------------------
# ESTILOS CSS
# ---------------------------------------------------------
st.markdown("""
    <style>
        #MainMenu, footer, .stAppDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none!important;}
        header {visibility: visible !important; background: transparent !important;}
        .plotly .modebar, button[title="View fullscreen"] {display: none !important;}
        [data-testid="stSidebar"] {border-top: 5px solid #7AB800 !important; padding-top: 0px !important;}
        button[kind="primary"], button[data-testid="baseButton-primary"] {background-color: #7AB800 !important; color: #FFFFFF !important; font-weight: bold !important;}
        .titulo-tablero {font-size: 1.35rem !important; font-weight: 700 !important; border-bottom: 3px solid #7AB800 !important; padding-bottom: 6px !important;}
        .block-header {text-align: center; font-weight: bold; font-size: 0.85rem; text-transform: uppercase;}
        .card-box {border-radius: 6px; padding: 4px 8px; text-align: center; font-weight: bold; color: #000; box-shadow: 0px 2px 4px rgba(0,0,0,0.08);}
        .month-row {display: flex; justify-content: space-between; align-items: center; padding: 2px 0; font-weight: bold; font-size: 0.82rem; width: 175px !important;}
        .month-box {background-color: #D9EAD3; width: 44px; text-align: center; padding: 2px 0; border-radius: 4px; color: #000;}
        .month-box-fin {background-color: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.25); width: 44px; text-align: center; padding: 2px 0; border-radius: 4px; font-weight: bold;}
        .alert-card-horiz {background-color: rgba(241, 245, 249, 0.05); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; display: flex; align-items: center; justify-content: space-between; font-weight: bold; font-size: 0.85rem;}
        .alert-val-box {background-color: #EFEFEF; width: 38px; text-align: center; padding: 3px 0; border-radius: 4px; color: #000; font-weight: bold;}
        .total-acciones-box {background-color: rgba(241, 245, 249, 0.15); border: 1px solid #CBD5E1; padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 1.1rem; display: inline-block; margin-bottom: 12px;}
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SELECTOR DE ENTORNO
# ---------------------------------------------------------
if LOGO_PATH: st.sidebar.image(LOGO_PATH, use_container_width=True)
entornos_permitidos = [e for e in TODOS_LOS_ENTORNOS if e in st.session_state.get("permisos_entornos", [])]
if not entornos_permitidos: st.warning("⚠️ No tienes permisos asignados."); st.stop()

if len(entornos_permitidos) > 1:
    modulo_sel = st.sidebar.radio("📌 Seleccione Entorno de Gestión:", [f"📊 {e}" if e == "Auditoría Interna" else f"🏛️ {e}" for e in entornos_permitidos], index=0)
    entorno_activo = "Auditoría Interna" if "Auditoría" in modulo_sel else "Contraloría de Bogotá"
else: entorno_activo = entornos_permitidos[0]

st.sidebar.markdown("---")
col_l, col_t = st.columns([1, 4])
with col_l:
    if LOGO_PATH: st.image(LOGO_PATH, use_container_width=True)
    else: st.markdown("🚌 **LA TERMINAL**")
with col_t:
    st.markdown(f'<div class="titulo-tablero">Tablero de Control - {"Auditoría Interna" if entorno_activo == "Auditoría Interna" else "Contraloría de Bogotá"}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# EXCEL HELPERS
# ---------------------------------------------------------
def buscar_excel(nombre_archivos, defecto):
    dir_s = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    for n in nombre_archivos:
        for d in [dir_s, os.path.dirname(dir_s)]:
            r = os.path.join(d, n)
            if os.path.exists(r): return r
    return os.path.join(dir_s, defecto)

EXCEL_PATH_AI = buscar_excel(["TABLERO_PA_AI.xlsm", "TABLERO_PA_AI.xlsx", "TABLERO_PA_I.xlsm", "TABLERO_PA_I.xlsx"], "TABLERO_PA_AI.xlsx")
EXCEL_PATH_C = buscar_excel(["TABLERO_PA_C.xlsx", "TABLERO_PA_C.xlsm"], "TABLERO_PA_C.xlsx")

def buscar_columna_por_patron(df, patrones):
    for col in df.columns:
        c_clean = str(col).lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
        for p in patrones:
            if p in c_clean: return col
    return None

def filtrar_solo_columnas_amarillas_ai(df):
    reqs = ["Plan Auditoría", "Auditoría", "Titulo del Hallazgo", "Transcribir el del Hallazgo o Situación Evidenciada", "Nivel del Riesgo", "Plan de Acción", "Responsable", "Inicio", "Cierre", "Enlace para cargar evidencias", "Estado", "Alerta 10 días", "Alerta 20 días", "Alerta 30 días", "Alerta 5 días"]
    cols = []
    for r in reqs:
        m = next((c for c in df.columns if str(c).strip().lower() == r.lower()), None)
        if not m:
            if "transcribir" in r.lower(): m = buscar_columna_por_patron(df, ["transcribir el del hallazgo", "situacion evidenciada"])
            elif "enlace" in r.lower(): m = buscar_columna_por_patron(df, ["enlace para cargar evidencias", "cargar evidencias"])
            elif "inicio" in r.lower(): m = buscar_columna_por_patron(df, ["inicio"])
            elif "cierre" in r.lower(): m = buscar_columna_por_patron(df, ["cierre", "fecha cierre", "fecha compromiso"])
            elif "estado" in r.lower(): m = buscar_columna_por_patron(df, ["estado del compromiso", "estado compromiso"]) or ("Estado" if "Estado" in df.columns else None)
        if m and m in df.columns and m not in cols: cols.append(m)
    return df[cols].copy() if cols else df.copy()

def filtrar_solo_columnas_amarillas_c(df):
    reqs = ["VIGENCIA DE LA AUDITORÍA O VISITA", "CODIGO AUDITORÍA SEGÚN PAD DE LA VIGENCIA", "No. HALLAZGO", "CODIGO ACCION", "DESCRIPCIÓN HALLAZGO", "DESCRIPCIÓN ACCIÓN", "AREA RESPONSABLE", "FECHA DE INICIO", "FECHA DE TERMINACIÓN", "ESTADO", "ENLACE PARA CARGAR EVIDENCIAS", "Alerta 10", "Alerta 20", "Alerta 30", "Alerta 5"]
    cols = []
    for r in reqs:
        m = next((c for c in df.columns if str(c).strip().lower() == r.lower()), None)
        if not m:
            if "vigencia" in r.lower(): m = buscar_columna_por_patron(df, ["vigencia de la auditoria"])
            elif "descripcion accion" in r.lower(): m = buscar_columna_por_patron(df, ["descripcion accion"])
            elif "area responsable" in r.lower(): m = buscar_columna_por_patron(df, ["area responsable", "dependencia"])
            elif "inicio" in r.lower(): m = buscar_columna_por_patron(df, ["fecha de inicio"])
            elif "terminacion" in r.lower(): m = buscar_columna_por_patron(df, ["fecha de terminacion"])
            elif "enlace" in r.lower(): m = buscar_columna_por_patron(df, ["enlace para cargar evidencias", "evidencias"])
        if m and m in df.columns and m not in cols: cols.append(m)
    return df[cols].copy() if cols else df.copy()

def generar_excel_generico(df, fn_filtro, sheet_name):
    output = io.BytesIO()
    df_exp = fn_filtro(df)
    for col in df_exp.columns:
        if any(p in str(col).lower() for p in ["fecha", "terminacion", "cierre", "inicio", "vencimiento"]):
            def fmt_f(val):
                if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "nat", ""]: return ""
                if isinstance(val, (datetime, pd.Timestamp, date)): return val.strftime("%d/%m/%Y")
                try:
                    dt = pd.to_datetime(str(val).strip(), dayfirst=True, errors="coerce")
                    if pd.notnull(dt): return dt.strftime("%d/%m/%Y")
                except Exception: pass
                return str(val).strip()
            df_exp[col] = df_exp[col].apply(fmt_f)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_exp.to_excel(writer, index=False, sheet_name=sheet_name)
        wb, ws = writer.book, writer.sheets[sheet_name]
        hdr_fmt = wb.add_format({"bold": True, "text_wrap": True, "valign": "vcenter", "align": "center", "fg_color": "#1F4E78", "font_color": "#FFFFFF", "border": 1})
        cell_fmt = wb.add_format({"valign": "vcenter", "border": 1})
        dt_fmt = wb.add_format({"valign": "vcenter", "align": "center", "border": 1})
        for c_idx, val in enumerate(df_exp.columns.values): ws.write(0, c_idx, str(val), hdr_fmt)
        for i, col in enumerate(df_exp.columns):
            es_f = any(p in str(col).lower() for p in ["fecha", "terminacion", "cierre", "inicio", "vencimiento"])
            lens = [len(str(v)) for v in df_exp[col].dropna().tolist()] if not df_exp.empty else []
            ws.set_column(i, i, min(max(max(lens) if lens else 0 + 4, len(str(col)) + 4, 14), 65), dt_fmt if es_f else cell_fmt)
        ws.hide_gridlines(2)
    return output.getvalue()

def generar_excel_formateado_ai(df): return generar_excel_generico(df, filtrar_solo_columnas_amarillas_ai, "Detalle_Compromisos")
def generar_excel_formateado_c(df): return generar_excel_generico(df, filtrar_solo_columnas_amarillas_c, "Detalle_Contraloria")

# =========================================================
# VISTA 1: AUDITORÍA INTERNA
# =========================================================
if entorno_activo == "Auditoría Interna":
    def cargar_datos_ai():
        if not os.path.exists(EXCEL_PATH_AI):
            st.error(f"⚠️ No se encontró el archivo Excel en: `{EXCEL_PATH_AI}`"); return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        try:
            xls = pd.ExcelFile(EXCEL_PATH_AI)
            sb = "Base de datos" if "Base de datos" in xls.sheet_names else ("Base de Datos" if "Base de Datos" in xls.sheet_names else xls.sheet_names[0])
            df_b = pd.read_excel(xls, sheet_name=sb)
            df_b.columns = [str(c).strip() for c in df_b.columns]
            for c in df_b.columns:
                if df_b[c].dtype == "object": df_b[c] = df_b[c].astype(str).str.strip()
            sc = "Calculos" if "Calculos" in xls.sheet_names else ("Cálculos" if "Cálculos" in xls.sheet_names else None)
            df_c = pd.read_excel(xls, sheet_name=sc, header=None) if sc else pd.DataFrame()
            si = "Informes PDF" if "Informes PDF" in xls.sheet_names else ("INFORMES PDF" if "INFORMES PDF" in xls.sheet_names else None)
            df_i = pd.read_excel(xls, sheet_name=si) if si else pd.DataFrame()
            sp = "Programa Anual de Auditoría" if "Programa Anual de Auditoría" in xls.sheet_names else ("Programa Anual de Auditoria" if "Programa Anual de Auditoria" in xls.sheet_names else None)
            df_p = pd.read_excel(xls, sheet_name=sp) if sp else pd.DataFrame()
            return df_b, df_c, df_i, df_p
        except Exception as e:
            st.error(f"Error al cargar el archivo Excel: {e}"); return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_raw, df_calc, df_informes_raw, df_paa_raw = cargar_datos_ai()
    if df_raw.empty: st.stop()

    col_estado = "Estado" if "Estado" in df_raw.columns else buscar_columna_por_patron(df_raw, ["estado del compromiso", "estado compromiso"])
    col_responsable = "Responsable" if "Responsable" in df_raw.columns else buscar_columna_por_patron(df_raw, ["responsable", "area responsable"])
    col_auditor_resp = "Auditor Responsable" if "Auditor Responsable" in df_raw.columns else buscar_columna_por_patron(df_raw, ["auditor responsable", "auditor"])
    col_apoyo_resp = "Apoyo Responsable" if "Apoyo Responsable" in df_raw.columns else buscar_columna_por_patron(df_raw, ["apoyo responsable", "apoyo"])
    col_plan_filtro = "Plan Auditoría" if "Plan Auditoría" in df_raw.columns else buscar_columna_por_patron(df_raw, ["plan auditoria", "vigencia"])
    col_plan_accion = "Plan de Acción" if "Plan de Acción" in df_raw.columns else buscar_columna_por_patron(df_raw, ["compromiso", "plan de accion", "accion"]) or col_plan_filtro
    col_auditoria = "Auditoría" if "Auditoría" in df_raw.columns else buscar_columna_por_patron(df_raw, ["auditoria especifica"])
    col_hallazgo = "Transcribir el del Hallazgo o Situación Evidenciada" if "Transcribir el del Hallazgo o Situación Evidenciada" in df_raw.columns else buscar_columna_por_patron(df_raw, ["transcribir", "situacion evidenciada", "del hallazgo", "titulo del hallazgo", "hallazgo"])
    col_nombre = "Titulo del Hallazgo" if "Titulo del Hallazgo" in df_raw.columns else buscar_columna_por_patron(df_raw, ["nombre", "nombre hallazgo", "titulo"])
    col_riesgo = "Nivel del Riesgo" if "Nivel del Riesgo" in df_raw.columns else buscar_columna_por_patron(df_raw, ["riesgo", "nivel de riesgo"])
    col_fecha_inicio = "Inicio" if "Inicio" in df_raw.columns else buscar_columna_por_patron(df_raw, ["inicio"])
    col_fecha_cierre = "Cierre" if "Cierre" in df_raw.columns else (buscar_columna_por_patron(df_raw, ["cierre dd/mm/a", "cierre"]) or buscar_columna_por_patron(df_raw, ["fecha cierre", "fecha compromiso"]))
    col_fecha_cierre_aud = "Fecha de cierre Auditoría" if "Fecha de cierre Auditoría" in df_raw.columns else buscar_columna_por_patron(df_raw, ["fecha de cierre auditoria", "cierre auditoria"])
    col_obs_audit = buscar_columna_por_patron(df_raw, ["observacion auditoria"]) or "Observación Auditoría"
    col_a5, col_a10, col_a20, col_a30 = "Alerta 5 días", "Alerta 10 días", "Alerta 20 días", "Alerta 30 días"

    if col_estado: df_raw[col_estado] = df_raw[col_estado].astype(str).str.capitalize()

    for col_f in [col_fecha_inicio, col_fecha_cierre, col_fecha_cierre_aud]:
        if col_f and col_f in df_raw.columns:
            def formatear_fecha_corta(val):
                if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "nat", ""]: return ""
                if isinstance(val, (datetime, pd.Timestamp, date)): return val.strftime("%d/%m/%Y")
                try:
                    dt = pd.to_datetime(str(val).strip(), dayfirst=True, errors="coerce")
                    if pd.notnull(dt): return dt.strftime("%d/%m/%Y")
                except Exception: pass
                return str(val).strip()
            df_raw[col_f] = df_raw[col_f].apply(formatear_fecha_corta)

    meses_es = ["ENE", "FEB", "MAR", "ABR", "MAYO", "JUNIO", "JULIO", "AGO", "SEP", "OCT", "NOV", "DIC"]
    conteo_meses = {m: 0 for m in meses_es}
    if not df_calc.empty:
        for idx, row in df_calc.iterrows():
            val_m = str(row[0]).strip().lower()
            for idx_m, m_nombre in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]):
                if m_nombre in val_m: conteo_meses[meses_es[idx_m]] = int(row[1]) if pd.notnull(row[1]) and str(row[1]).isdigit() else 0

    st.sidebar.title("🔍 Filtros Auditoría")
    st.sidebar.markdown(f"👤 **Usuario activo:** `{st.session_state.get('usuario_actual')}`")

    if st.session_state.get("usuario_actual") == "admin":
        with st.sidebar.expander("👤 Gestión de Usuarios y Permisos (Admin)"):
            st.caption("1. Registrar / Actualizar Usuario")
            new_u, new_e, new_p = st.text_input("Usuario", key="new_u_adm"), st.text_input("Correo Electrónico", key="new_e_adm"), st.text_input("Contraseña Inicial", type="password", key="new_p_adm")
            u_entornos = [ent for ent in TODOS_LOS_ENTORNOS if st.checkbox(f"🌐 Entorno: {ent}", value=True, key=f"chk_ent_{ent}")]
            u_permisos = [p for p in TODAS_LAS_PESTANIAS if st.checkbox(f"Ver {p}", value=True, key=f"chk_add_{p}")]
            u_subpermisos = [s for s in TODAS_LAS_SUBPESTANIAS if st.checkbox(f"🔹 {s}", value=True, key=f"chk_add_sub_{s}")]

            if st.button("Guardar / Autorizar Usuario"):
                if new_u and new_e and new_p:
                    guardar_o_actualizar_usuario(new_u.strip(), new_e.strip().lower(), new_p, u_permisos, u_subpermisos, u_entornos)
                    st.success(f"Usuario `{new_u}` actualizado localmente.")
                else: st.warning("Completa todos los campos.")
                    
            st.divider()
            st.caption("2. Modificar Permisos Existentes a Múltiples Usuarios")
            df_users = obtener_usuarios_df()
            if not df_users.empty and 'usuario' in df_users.columns:
                lista_usuarios = df_users['usuario'].tolist()
                c_sa, c_ca = st.columns(2)
                with c_sa:
                    if st.button("✅ Seleccionar Todos", use_container_width=True, key="btn_sel_all_users_bulk"):
                        st.session_state["sel_mod_users_list"] = lista_usuarios; st.rerun()
                with c_ca:
                    if st.button("❌ Quitar Todos", use_container_width=True, key="btn_clear_all_users_bulk"):
                        st.session_state["sel_mod_users_list"] = []; st.rerun()

                if "sel_mod_users_list" not in st.session_state: st.session_state["sel_mod_users_list"] = []
                users_sel = st.multiselect("Seleccionar usuario(s) a modificar:", options=lista_usuarios, default=st.session_state["sel_mod_users_list"], key="sel_mod_users_multiselect")

                if users_sel:
                    st.info(f"👥 Modificando permisos para **{len(users_sel)}** usuario(s).")
                    nuevos_ents = st.multiselect("Entornos:", options=TODOS_LOS_ENTORNOS, default=TODOS_LOS_ENTORNOS, key="edit_ents_bulk")
                    nuevos_perms = st.multiselect("Pestañas:", options=TODAS_LAS_PESTANIAS, default=TODAS_LAS_PESTANIAS, key="edit_perms_bulk")
                    nuevos_subperms = st.multiselect("Subpestañas:", options=TODAS_LAS_SUBPESTANIAS, default=TODAS_LAS_SUBPESTANIAS, key="edit_subperms_bulk")
                    if st.button(f"💾 Aplicar Permisos a los {len(users_sel)} Usuarios", type="primary", use_container_width=True, key="btn_apply_bulk_perms"):
                        for u in users_sel: actualizar_permisos_usuario(u, nuevos_perms, nuevos_subperms, nuevos_ents)
                        st.success(f"¡Permisos actualizados con éxito!"); st.rerun()

            st.divider()
            st.caption("3. 📦 Respaldo de Usuarios")
            st.download_button(label="📊 Descargar usuarios.xlsx", data=obtener_usuarios_excel_bytes(), file_name=f"usuarios_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            st.download_button(label="☁️ Descargar usuarios.json", data=obtener_usuarios_json_bytes(), file_name="usuarios.json", mime="application/json", use_container_width=True)

    if st.sidebar.button("🚪 Cerrar Sesión"):
        for k in ["autenticado", "usuario_actual", "permisos_usuario", "permisos_subpestañas", "permisos_entornos"]: st.session_state[k] = False if k == "autenticado" else ("" if k == "usuario_actual" else [])
        st.rerun()

    st.sidebar.markdown("---")
    df_filtrado = df_raw.copy()

    if col_estado:
        estados_vals = sorted([e for e in df_raw[col_estado].dropna().unique() if str(e).lower() not in ["nan", "none", ""] and not re.search(r"finaliz|cerrad", str(e), re.IGNORECASE)])
        with st.sidebar.expander("📌 Estado del compromiso", expanded=False): estado_sel = st.multiselect("Seleccione Estados:", options=estados_vals, default=[], key="multi_estado")
        if estado_sel: df_filtrado = df_filtrado[df_filtrado[col_estado].isin(estado_sel)]

    if col_responsable:
        resp_unicos_set = {limpiar_nombre_area(p) for val in df_raw[col_responsable].dropna().unique() for p in re.split(r"[/,\n\r]+", str(val)) if limpiar_nombre_area(p) and limpiar_nombre_area(p).upper() not in ["NAN", "NONE", ""]}
        with st.sidebar.expander("👤 Responsables", expanded=False): resp_sel = st.multiselect("Seleccione Responsables:", options=sorted(list(resp_unicos_set)), default=[], key="multi_resp")
        if resp_sel:
            df_filtrado = df_filtrado[df_filtrado[col_responsable].apply(lambda c: False if pd.isna(c) else any(s in [limpiar_nombre_area(p) for p in re.split(r"[/,\n\r]+", str(c))] for s in resp_sel))]

    if col_auditor_resp:
        aud_resp_vals = sorted(list({ar for ar in df_raw[col_auditor_resp].dropna().unique() if str(ar).lower() not in ["nan", "none", ""]}))
        with st.sidebar.expander("🧐 Auditor Responsable", expanded=False): aud_resp_sel = st.multiselect("Seleccione Auditores:", options=aud_resp_vals, default=[], key="multi_auditor_resp")
        if aud_resp_sel: df_filtrado = df_filtrado[df_filtrado[col_auditor_resp].isin(aud_resp_sel)]

    if col_plan_filtro:
        plan_vals = sorted(list({p for p in df_raw[col_plan_filtro].dropna().unique() if str(p).lower() not in ["nan", "none", ""]}))
        with st.sidebar.expander("📁 Plan Auditoría / Vigencia", expanded=False): plan_sel = st.multiselect("Seleccione Planes:", options=plan_vals, default=[], key="multi_plan")
        if plan_sel: df_filtrado = df_filtrado[df_filtrado[col_plan_filtro].isin(plan_sel)]

    if col_auditoria:
        aud_vals = sorted(list({a for a in df_raw[col_auditoria].dropna().unique() if str(a).lower() not in ["nan", "none", ""]}))
        with st.sidebar.expander("🔬 Auditoría Específica", expanded=False): auditoria_sel = st.multiselect("Seleccione Auditorías:", options=aud_vals, default=[], key="multi_auditoria")
        if auditoria_sel: df_filtrado = df_filtrado[df_filtrado[col_auditoria].isin(auditoria_sel)]

    abiertos = df_filtrado[col_estado].astype(str).str.contains("Abiert", case=False, na=False).sum() if col_estado else 0
    vencidos = df_filtrado[col_estado].astype(str).str.contains("Vencid", case=False, na=False).sum() if col_estado else 0
    sin_plan = df_filtrado[col_estado].astype(str).str.contains("Sin plan|Sin defin", case=False, na=False).sum() if col_estado else 0
    df_activos = df_filtrado[~df_filtrado[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy() if col_estado else df_filtrado.copy()

    total_hallazgos_unicos_pendientes = df_activos[col_hallazgo].dropna().nunique() if col_hallazgo and col_hallazgo in df_activos.columns else len(df_activos)
    total_planes_pendientes = abiertos + vencidos + sin_plan
    r_alto = df_activos[col_riesgo].astype(str).str.contains("Alto", case=False, na=False).sum() if col_riesgo else 0
    r_medio = df_activos[col_riesgo].astype(str).str.contains("Medio", case=False, na=False).sum() if col_riesgo else 0
    r_bajo = df_activos[col_riesgo].astype(str).str.contains("Bajo", case=False, na=False).sum() if col_riesgo else 0

    total_hist_ai = len(df_raw)
    fin_ai_cnt = df_raw[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False).sum() if col_estado else 0
    pct_cumplimiento_ai = int(round((fin_ai_cnt / total_hist_ai) * 100)) if total_hist_ai > 0 else 0

    hoy_dt = pd.to_datetime(date.today())
    df_raw_venc_ai = df_raw[df_raw[col_estado].astype(str).str.contains("Vencid", case=False, na=False)].copy() if col_estado else pd.DataFrame()
    if not df_raw_venc_ai.empty and col_fecha_cierre in df_raw_venc_ai.columns:
        dias_mora_ai_series = (hoy_dt - df_raw_venc_ai[col_fecha_cierre].apply(parsear_fecha_estricta)).dt.days.dropna()
        prom_mora_ai_val = int(round(dias_mora_ai_series[dias_mora_ai_series > 0].mean())) if not dias_mora_ai_series[dias_mora_ai_series > 0].empty else 0
    else: prom_mora_ai_val = 0

    # GRÁFICOS AUDITORÍA INTERNA
    meses_orden = ["ENE", "FEB", "MAR", "ABR", "MAYO", "JUNIO", "JULIO", "AGO", "SEP", "OCT", "NOV", "DIC"]
    map_m_num = {i+1: m for i, m in enumerate(meses_orden)}
    data_tend_abiertos, data_tend_vencidos, data_tend_fin = {m: 0 for m in meses_orden}, {m: 0 for m in meses_orden}, {m: 0 for m in meses_orden}

    for _, r in df_filtrado.iterrows():
        st_val = str(r[col_estado]).lower()
        if any(term in st_val for term in ['finaliz', 'cerrad']):
            dt_s = parsear_fecha_estricta(r[col_fecha_cierre_aud]) if col_fecha_cierre_aud in r else pd.NaT
            if pd.notnull(dt_s) and dt_s.year == 2026 and dt_s.month in map_m_num: data_tend_fin[map_m_num[dt_s.month]] += 1
        else:
            dt_i = parsear_fecha_estricta(r[col_fecha_cierre]) if col_fecha_cierre in r else pd.NaT
            if pd.notnull(dt_i) and dt_i.year == 2026 and dt_i.month in map_m_num:
                if 'vencid' in st_val: data_tend_vencidos[map_m_num[dt_i.month]] += 1
                else: data_tend_abiertos[map_m_num[dt_i.month]] += 1

    fig_tendencia = go.Figure()
    fig_tendencia.add_trace(go.Scatter(x=meses_orden, y=[data_tend_abiertos[m] for m in meses_orden], mode='lines+markers', name='Abiertos', line=dict(color='#F39C12', width=3)))
    fig_tendencia.add_trace(go.Scatter(x=meses_orden, y=[data_tend_vencidos[m] for m in meses_orden], mode='lines+markers', name='Vencidos', line=dict(color='#FF5E5E', width=3)))
    fig_tendencia.add_trace(go.Scatter(x=meses_orden, y=[data_tend_fin[m] for m in meses_orden], mode='lines+markers', name='Finalizados/Cerrados', line=dict(color='#2ECC71', width=3)))
    fig_tendencia.update_layout(template='plotly_dark', title="📈 Tendencia Mensual de Planes (Vigencia 2026)", height=345, margin=dict(l=20, r=20, t=40, b=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"))

    fig_top5 = None
    if not df_activos.empty and col_responsable in df_activos.columns:
        df_act_copy = df_activos.copy()
        df_act_copy['Resp_Clean'] = df_act_copy[col_responsable].astype(str).apply(extraer_sub_areas_individuales)
        df_exp = df_act_copy.explode('Resp_Clean')
        df_exp = df_exp[~df_exp['Resp_Clean'].isin(["", "NAN", "NONE", "NONE."])]
        if not df_exp.empty:
            df_exp['Estado_Cat'] = df_exp[col_estado].astype(str).apply(lambda x: 'Vencidos' if 'vencid' in x.lower() else 'Abiertos')
            top_names = df_exp.groupby('Resp_Clean').size().nlargest(5).index.tolist()
            df_top5_final = df_exp.groupby(['Resp_Clean', 'Estado_Cat']).size().reset_index(name='Cantidad')
            fig_top5 = px.bar(df_top5_final[df_top5_final['Resp_Clean'].isin(top_names)], y='Resp_Clean', x='Cantidad', color='Estado_Cat', orientation='h', title="🔥 Top 5 Responsables con Pendientes", color_discrete_map={'Abiertos': '#F39C12', 'Vencidos': '#FF5252'}, text='Cantidad')
            fig_top5.update_layout(template='plotly_dark', height=320, margin=dict(l=20, r=20, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(autorange='reversed', title=None), legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"))

    pestañas_permitidas = [p for p in TODAS_LAS_PESTANIAS if p in st.session_state.get("permisos_usuario", [])]
    if not pestañas_permitidas: st.warning("⚠️ No tienes permisos asignados."); st.stop()
    dict_p = {"Tablero": "📊 Tablero", "Programa Anual": "🗓️ Programa Anual", "Métricas": "📈 Métricas", "Indicadores de Gestión": "📌 Indicadores de Gestión", "Histórico": "📊 Histórico", "Alertas y Edición": "🚨 Alertas y Edición", "Oficios": "📩 Oficios", "Informes": "📑 Informes"}
    tabs_obj = st.tabs([dict_p[p] for p in pestañas_permitidas])

    for n_tab, tab in zip(pestañas_permitidas, tabs_obj):
        with tab:
            if n_tab == "Tablero":
                col_i, col_d = st.columns([0.72, 1.6])
                with col_i:
                    st.markdown(f'<div class="block-header">Total Hallazgos Pendientes</div><div class="card-box" style="background-color:#4B92DB; font-size:1.3rem;">{total_hallazgos_unicos_pendientes}</div>', unsafe_allow_html=True)
                    r1, r2, r3 = st.columns(3)
                    r1.markdown(f'<div class="block-header" style="font-size:0.7rem;">Alto</div><div class="card-box" style="background-color:#FFB000;">{r_alto}</div>', unsafe_allow_html=True)
                    r2.markdown(f'<div class="block-header" style="font-size:0.7rem;">Medio</div><div class="card-box" style="background-color:#FFFF00;">{r_medio}</div>', unsafe_allow_html=True)
                    r3.markdown(f'<div class="block-header" style="font-size:0.7rem;">Bajo</div><div class="card-box" style="background-color:#00B050;">{r_bajo}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="block-header" style="margin-top:6px;">Planes Pendientes</div><div class="card-box" style="background-color:#00B050; font-size:1.4rem;">{total_planes_pendientes}</div>', unsafe_allow_html=True)
                    e1, e2, e3 = st.columns(3)
                    e1.markdown(f'<div class="block-header" style="font-size:0.7rem;">Abiertos</div><div class="card-box" style="background-color:#58C57A;">{abiertos}</div>', unsafe_allow_html=True)
                    e2.markdown(f'<div class="block-header" style="font-size:0.7rem;">Vencidos</div><div class="card-box" style="background-color:#FF5252; color:#FFF;">{vencidos}</div>', unsafe_allow_html=True)
                    e3.markdown(f'<div class="block-header" style="font-size:0.7rem;">Sin definir</div><div class="card-box" style="background-color:#F8A583;">{sin_plan}</div>', unsafe_allow_html=True)
                with col_d:
                    st.plotly_chart(fig_tendencia, use_container_width=True, key="fig_tend_ai", config={'displayModeBar': False})
                    if fig_top5: st.plotly_chart(fig_top5, use_container_width=True, key="fig_top5_ai", config={'displayModeBar': False})
                st.markdown("---")
                df_tv = filtrar_solo_columnas_amarillas_ai(df_activos)
                df_tv.index = range(1, len(df_tv) + 1)
                st.dataframe(df_tv, use_container_width=True)
                st.download_button("📥 Descargar Excel (.xlsx)", data=generar_excel_formateado_ai(df_activos), file_name=f"Detalle_Compromisos_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            elif n_tab == "Programa Anual":
                st.header("🗓️ Programa Anual de Auditoría (PAA)")
                if not df_paa_raw.empty:
                    df_pv = df_paa_raw.copy()
                    col_v = buscar_columna_por_patron(df_pv, ["vigencia"]) or df_pv.columns[0]
                    df_pv[col_v] = df_pv[col_v].ffill().astype(str).str.replace(".0", "", regex=False).str.strip()
                    st.dataframe(df_pv, use_container_width=True)

            elif n_tab == "Métricas":
                st.header("📈 Resumen de Estado y Desempeño")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Pendientes", total_planes_pendientes); m2.metric("Vencidos", vencidos); m3.metric("Abiertos", abiertos); m4.metric("Riesgo Alto", r_alto)

            elif n_tab == "Indicadores de Gestión":
                st.header("📌 Indicadores de Gestión Auditoría Interna")
                st.info("Consulte la distribución programada vs ejecutada por subpestañas.")

            elif n_tab == "Histórico":
                st.header("📊 Análisis Histórico e Interanual")
                st.dataframe(df_raw, use_container_width=True)

            elif n_tab == "Alertas y Edición":
                st.header("🚨 Alertas Críticas y Edición Directa")
                st.success("Módulo de alertas cargado correctamente.")

            elif n_tab == "Oficios":
                st.header("📩 Registro e Historial de Oficios Radicados")
                st.info("Módulo de trazabilidad de oficios.")

            elif n_tab == "Informes":
                st.header("📑 Consulta Histórica de Informes")
                st.dataframe(df_informes_raw, use_container_width=True)

# =========================================================
# VISTA 2: CONTRALORÍA DE BOGOTÁ
# =========================================================
else:
    def cargar_datos_c():
        if not os.path.exists(EXCEL_PATH_C): return pd.DataFrame(), pd.DataFrame()
        try:
            xls = pd.ExcelFile(EXCEL_PATH_C)
            sb = "Base de Datos" if "Base de Datos" in xls.sheet_names else xls.sheet_names[0]
            df_b = pd.read_excel(xls, sheet_name=sb)
            df_b.columns = [str(c).strip() for c in df_b.columns]
            si = "Enlace PDF" if "Enlace PDF" in xls.sheet_names else None
            return df_b, (pd.read_excel(xls, sheet_name=si) if si else pd.DataFrame())
        except Exception: return pd.DataFrame(), pd.DataFrame()

    df_raw_c, df_informes_raw_c = cargar_datos_c()
    if df_raw_c.empty: st.stop()

    col_fecha_cierre_c = df_raw_c.columns[22] if len(df_raw_c.columns) > 22 else "FECHA DE TERMINACIÓN"
    col_estado_c = df_raw_c.columns[26] if len(df_raw_c.columns) > 26 else "ESTADO"
    col_responsable_c = "AREA RESPONSABLE" if "AREA RESPONSABLE" in df_raw_c.columns else buscar_columna_por_patron(df_raw_c, ["area responsable", "responsable"])

    if col_estado_c: df_raw_c[col_estado_c] = df_raw_c[col_estado_c].astype(str).str.capitalize()
    if col_fecha_cierre_c and col_fecha_cierre_c in df_raw_c.columns:
        def fmt_fc(val):
            if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "nat", ""]: return ""
            if isinstance(val, (datetime, pd.Timestamp, date)): return val.strftime("%d/%m/%Y")
            try:
                dt = pd.to_datetime(str(val).strip(), dayfirst=True, errors="coerce")
                if pd.notnull(dt): return dt.strftime("%d/%m/%Y")
            except Exception: pass
            return str(val).strip()
        df_raw_c[col_fecha_cierre_c] = df_raw_c[col_fecha_cierre_c].apply(fmt_fc)

    pestañas_permitidas_c = [p for p in TODAS_LAS_PESTANIAS if p in st.session_state.get("permisos_usuario", [])]
    tabs_obj_c = st.tabs([f"📊 {p}" for p in pestañas_permitidas_c])

    for n_tab_c, tab_c in zip(pestañas_permitidas_c, tabs_obj_c):
        with tab_c:
            st.header(f"🏛️ Contraloría de Bogotá - {n_tab_c}")
            df_cv = filtrar_solo_columnas_amarillas_c(df_raw_c)
            df_cv.index = range(1, len(df_cv) + 1)
            st.dataframe(df_cv, use_container_width=True)
            st.download_button("📥 Descargar Excel Contraloría (.xlsx)", data=generar_excel_formateado_c(df_raw_c), file_name=f"Detalle_Contraloria_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")