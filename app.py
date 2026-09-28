import hashlib
import hmac
import sqlite3
import smtplib
from email.mime.text import MIMEText
import random
import string
from datetime import date, datetime, timedelta
import io
import os
import re
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Tablero de Control - La Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

def buscar_logo_local():
    dir_script = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    nombres_logo = ["logo_terminal.png", "logo_terminal.jpg", "logo.png", "logo.jpg"]
    for n in nombres_logo:
        ruta = os.path.join(dir_script, n)
        if os.path.exists(ruta):
            return ruta
    return None

LOGO_PATH = buscar_logo_local()

DB_PATH = "usuarios_app.db"
JSON_USERS_FILE = "usuarios.json"

SHEET_NOTIF_ID = "1jDD1qFgDMmf52wMue2VfdX3ls7EuZ4wV-ZrOZW3r0Os"

TODAS_LAS_PESTANIAS = [
    "Tablero", 
    "Programa Anual", 
    "Métricas", 
    "Indicadores de Gestión",
    "Histórico", 
    "Alertas y Edición", 
    "Oficios", 
    "Informes"
]

TODOS_LOS_ENTORNOS = [
    "Auditoría Interna",
    "Contraloría de Bogotá"
]

USUARIOS_AMARILLOS = [
    'admin', 
    'diego.vasquez@terminaldetransporte.gov.co', 
    'manuel.gutierrez', 
    'manuel.gutierrez@terminaldetransporte.gov.co',
    'omar.diaz',
    'omar.diaz@terminaldetransporte.gov.co'
]

USUARIO_EXCLUSIVO_CONTRALORIA = [
    'admin',
    'diego.vasquez@terminaldetransporte.gov.co'
]

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_password(password, hashed):
    return hmac.compare_digest(hash_password(password), str(hashed).strip())

def parsear_fecha_estricta(val):
    if pd.isna(val): return pd.NaT
    if isinstance(val, (datetime, pd.Timestamp, date)): return pd.to_datetime(val)
    val_str = str(val).strip().lower()
    if val_str in ["nan", "none", "nat", "", "cierre", "cierre dd/mm/a", "cierre dd/mm/aa", "inicio", "inicio dd/mm/a"]:
        return pd.NaT
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
            usuario TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT,
            autorizado INTEGER DEFAULT 1,
            token_recuperacion TEXT,
            perm_pestañas TEXT DEFAULT 'TODOS',
            perm_entornos TEXT DEFAULT 'TODOS',
            requiere_2fa INTEGER DEFAULT 1
        )
    ''')
    conn.commit()

    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN requiere_2fa INTEGER DEFAULT 1")
        conn.commit()
    except sqlite3.OperationalError: pass

    pw_defecto = hash_password("123456")
    usuarios_base_raw = [
        ('edgar.ortiz', 'edgar.ortiz@terminaldetransporte.gov'),
        ('manuel.cifuentes', 'manuel.cifuentes@terminaldetransporte.gov.co'),
        ('eduardo.gonzalez', 'eduardo.gonzalez@terminaldetransporte.gov.co'),
        ('oscar.garzon', 'oscar.garzon@terminaldetransporte.gov.co'),
        ('manuel.santamaria', 'manuel.santamaria@terminaldetransporte.gov.co'),
        ('carlos.salcedo', 'carlos.salcedo@terminaldetransporte.gov.co'),
        ('juan.alviz', 'juan.alviz@terminaldetransporte.gov.co'),
        ('julio.mosquera', 'julio.mosquera@terminaldetransporte.gov.co'),
        ('marcela.angarita', 'marcela.angarita@terminaldetransporte.gov.co'),
        ('roberto.bermudez', 'roberto.bermudez@terminaldetransporte.gov.co'),
        ('miguel.salina', 'miguel.salina@terminaldetransporte.gov.co'),
        ('oscar.castañeda', 'oscar.castaneda@terminaldetransporte.gov.co'),
        ('andres.panqueva', 'andres.panqueva@terminaldetransporte.gov.co'),
        ('christian.pardo', 'christian.pardo@terminaldetransporte.gov.co'),
        ('diana.ortiz', 'diana.ortiz@terminaldetransporte.gov.co'),
        ('andrea.lievano', 'andrea.lievano@terminaldetransporte.gov.co'),
        ('william.camargo', 'william.camargo@terminaldetransporte.gov.co'),
        ('gerson.lugo', 'gerson.lugo@terminaldetransporte.gov.co'),
        ('leonardo.vasquez', 'leonardo.vasquez@terminaldetransporte.gov.co'),
        ('javier.veloza', 'javier.veloza@terminaldetransporte.gov.co'),
        ('manuel.salgado', 'manuel.salgado@terminaldetransporte.gov.co'),
        ('edgar.guzman', 'edgar.guzman@terminaldetransporte.gov.co'),
        ('carolina.bueno', 'carolina.bueno@terminaldetransporte.gov.co'),
        ('jenny.gomez', 'jenny.gomez@terminaldetransporte.gov.co'),
        ('paola.copete', 'paola.copete@terminaldetransporte.gov.co'),
        ('hugo.montoya', 'hugo.montoya@terminaldetransporte.gov.co'),
        ('admin', 'diego.vasquez@terminaldetransporte.gov.co'),
        ('diego.12', 'diego12vas@gmail.com'),
        ('fabian.silva', 'fabian.silva@terminaldetransporte.gov.co'),
        ('manuel.gutierrez', 'manuel.gutierrez@terminaldetransporte.gov.co'),
        ('omar.diaz', 'omar.diaz@terminaldetransporte.gov.co')
    ]

    usuarios_base = [
        (u, email, pw_defecto, 1, 'TODOS', 'TODOS', 0 if (u in USUARIOS_AMARILLOS or email in USUARIOS_AMARILLOS) else 1)
        for u, email in usuarios_base_raw
    ]

    if os.path.exists(JSON_USERS_FILE):
        try:
            with open(JSON_USERS_FILE, "r", encoding="utf-8") as f:
                usuarios_json = json.load(f)
                if usuarios_json:
                    usuarios_base = [
                        (
                            u["usuario"], u["email"], u["password_hash"], u.get("autorizado", 1), 
                            u.get("perm_pestañas", "TODOS"), u.get("perm_entornos", "TODOS"),
                            0 if (u["usuario"] in USUARIOS_AMARILLOS or u["email"] in USUARIOS_AMARILLOS) else 1
                        ) 
                        for u in usuarios_json
                    ]
        except Exception: pass

    c.executemany('''
        INSERT OR IGNORE INTO usuarios (usuario, email, password_hash, autorizado, perm_pestañas, perm_entornos, requiere_2fa)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', usuarios_base)

    for item in USUARIOS_AMARILLOS:
        c.execute("UPDATE usuarios SET requiere_2fa = 0 WHERE LOWER(usuario) = ? OR LOWER(email) = ?", (item.lower(), item.lower()))

    conn.commit()
    conn.close()

init_db()

@st.cache_data(ttl=5, show_spinner=False)
def obtener_notificaciones_drive_gsheet(sheet_id):
    if not sheet_id: return []
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        col_ent = next((c for c in df.columns if "entorno" in c), df.columns[0])
        col_arch = next((c for c in df.columns if "archivo" in c), df.columns[1])
        col_link = next((c for c in df.columns if "link" in c or "enlace" in c), df.columns[2])
        col_fec = next((c for c in df.columns if "fecha" in c), df.columns[3])
        
        notifs = []
        for idx, r in df.iterrows():
            arch_nom = str(r[col_arch]).strip()
            if arch_nom and arch_nom.lower() not in ["nan", "none", "proyecto sin título"]:
                notifs.append({
                    "id": idx,
                    "entorno": str(r[col_ent]).strip(),
                    "archivo": arch_nom,
                    "link_drive": str(r[col_link]).strip(),
                    "fecha": str(r[col_fec]).strip(),
                    "leido": False
                })
        return list(reversed(notifs))
    except Exception:
        return []

def obtener_notificaciones_usuario(usuario_actual):
    if usuario_actual.lower() not in [u.lower() for u in USUARIOS_AMARILLOS]:
        return []
    
    todas = obtener_notificaciones_drive_gsheet(SHEET_NOTIF_ID)
    es_dueno_contraloria = usuario_actual.lower() in [u.lower() for u in USUARIO_EXCLUSIVO_CONTRALORIA]
    
    if es_dueno_contraloria:
        return todas[:15]
    else:
        return [n for n in todas if "auditor" in n["entorno"].lower()][:15]

def obtener_usuarios_df():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT usuario, email, autorizado, perm_pestañas, perm_entornos, requiere_2fa FROM usuarios", conn)
    conn.close()
    return df

def exportar_y_sincronizar_usuarios():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT usuario, email, password_hash, autorizado, perm_pestañas, perm_entornos, requiere_2fa FROM usuarios")
    rows = c.fetchall()
    conn.close()
    lista_dict = [{"usuario": r[0], "email": r[1], "password_hash": r[2], "autorizado": r[3], "perm_pestañas": r[4], "perm_entornos": r[5], "requiere_2fa": r[6]} for r in rows]
    with open(JSON_USERS_FILE, "w", encoding="utf-8") as f: json.dump(lista_dict, f, indent=4, ensure_ascii=False)

def enviar_correo_token(email_destino, token):
    try:
        smtp_config = st.secrets.get("smtp", {})
        server_host = smtp_config.get("server", "smtp.gmail.com")
        port = int(smtp_config.get("port", 587))
        remitente = smtp_config.get("user", "")
        password_remitente = smtp_config.get("password", "")
        if not remitente or not password_remitente: return False
        msg = MIMEText(f"Hola,\n\nTu código de verificación de 6 dígitos para ingresar al sistema es: {token}\n\nSi no intentaste iniciar sesión, ignora este mensaje.")
        msg['Subject'] = "Código de Acceso de 6 Dígitos - Tablero La Terminal"
        msg['From'] = remitente
        msg['To'] = email_destino
        with smtplib.SMTP(server_host, port) as server:
            server.starttls()
            server.login(remitente, password_remitente)
            server.sendmail(remitente, [email_destino], msg.as_string())
        return True
    except Exception: return False

def limpiar_nombre_area(texto):
    if not texto or pd.isna(texto): return ""
    txt = str(texto).upper().strip()
    reemplazos = [(r"DIRECCIÓNDE", "DIRECCIÓN DE "), (r"DIRECCIONDE", "DIRECCIÓN DE "), (r"DEGESTIÓN", "DE GESTIÓN "), (r"DEGESTION", "DE GESTIÓN "), (r"DERECURSOS", "DE RECURSOS "), (r"FÍSICOSY", "FÍSICOS Y "), (r"FISICOSY", "FÍSICOS Y "), (r"FÍSICOSNEGOCIOS", "FÍSICOS Y NEGOCIOS "), (r"FISICOSNEGOCIOS", "FÍSICOS Y NEGOCIOS "), (r"TECNOLÓGICOS", "TECNOLÓGICOS"), (r"TECNOLOGICOS", "TECNOLÓGICOS"), (r"SUBGERENCIAJURÍDICA", "SUBGERENCIA JURÍDICA"), (r"SUBGERENCIACORPORATIVA", "SUBGERENCIA CORPORATIVA"), (r"SUBGERENCIADESERVICIOS", "SUBGERENCIA DE SERVICIOS "), (r"OPERACIONALESEINFRAESTRUCTURA", "OPERACIONALES E INFRAESTRUCTURA"), (r"SUB GERENCIA", "SUBGERENCIA")]
    for pat, rep in reemplazos: txt = re.sub(pat, rep, txt)
    return re.sub(r"\s+", " ", txt).strip()

def validar_login():
    if "autenticado" not in st.session_state: st.session_state["autenticado"] = False
    if "usuario_actual" not in st.session_state: st.session_state["usuario_actual"] = ""
    if "permisos_usuario" not in st.session_state: st.session_state["permisos_usuario"] = []
    if "permisos_entornos" not in st.session_state: st.session_state["permisos_entornos"] = []
    if "paso_login" not in st.session_state: st.session_state["paso_login"] = 1
    if "login_temp_data" not in st.session_state: st.session_state["login_temp_data"] = {}

    if not st.session_state["autenticado"]:
        login_container = st.empty()
        with login_container.container():
            st.markdown("""<style>button[data-testid="baseButton-primary"], .stButton > button[kind="primary"], .stButton > button { background-color: #7AB800 !important; color: #FFFFFF !important; font-weight: bold !important; border-radius: 6px !important; }</style>""", unsafe_allow_html=True)
            _, col_main, _ = st.columns([1, 1.8, 1])
            with col_main:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                if LOGO_PATH: st.image(LOGO_PATH, use_container_width=True)
                else: st.markdown("<h1 style='text-align: center; color: #0077C8;'>🚌 LA TERMINAL</h1>", unsafe_allow_html=True)
                st.markdown("<h4 style='text-align: center; color: #0077C8; font-weight: bold;'>Tablero de Control y Gestión</h4>", unsafe_allow_html=True)
                st.markdown("### 🔒 Acceso Restringido")

                if st.session_state["paso_login"] == 1:
                    usuario_input = st.text_input("Usuario o Correo Electrónico", key="user_login_input").strip().lower()
                    if st.button("Continuar ➡️", type="primary", use_container_width=True):
                        if not usuario_input: st.warning("⚠️ Por favor ingresa tu usuario o correo.")
                        else:
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute('SELECT usuario, email, password_hash, autorizado, perm_pestañas, perm_entornos, requiere_2fa FROM usuarios WHERE LOWER(usuario) = ? OR LOWER(email) = ?', (usuario_input, usuario_input))
                            row = c.fetchone()
                            conn.close()
                            if not row: st.error("❌ El usuario o correo no se encuentra registrado.")
                            elif row[3] == 0: st.error("🚫 Tu usuario no está autorizado.")
                            else:
                                user_db, email_db, pw_hash, aut, perm_str, ent_str, req_2fa = row
                                es_exento = (user_db.lower() in [u.lower() for u in USUARIOS_AMARILLOS]) or (email_db.lower() in [e.lower() for e in USUARIOS_AMARILLOS]) or (req_2fa == 0)
                                st.session_state["login_temp_data"] = {"usuario": user_db, "email": email_db, "pw_hash": pw_hash, "perm_str": perm_str, "ent_str": ent_str, "requiere_2fa": 0 if es_exento else 1}
                                if es_exento:
                                    st.session_state["paso_login"] = "password"
                                    st.rerun()
                                else:
                                    token_6_digitos = "".join(random.choices(string.digits, k=6))
                                    conn = sqlite3.connect(DB_PATH)
                                    c = conn.cursor()
                                    c.execute("UPDATE usuarios SET token_recuperacion = ? WHERE usuario = ?", (token_6_digitos, user_db))
                                    conn.commit()
                                    conn.close()
                                    if enviar_correo_token(email_db, token_6_digitos):
                                        st.session_state["paso_login"] = "otp"
                                        st.rerun()
                                    else: st.error("❌ Error al enviar el correo.")

                elif st.session_state["paso_login"] == "password":
                    u_data = st.session_state.get("login_temp_data", {})
                    st.info(f"👤 Usuario: **{u_data.get('usuario')}**")
                    password_ingresada = st.text_input("Contraseña", type="password", key="pass_yellow_input")
                    if st.button("Iniciar Sesión 🚀", type="primary", use_container_width=True):
                        if verificar_password(password_ingresada, u_data.get("pw_hash")):
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = u_data.get("usuario")
                            perm_val = u_data.get("perm_str", "TODOS")
                            st.session_state["permisos_usuario"] = TODAS_LAS_PESTANIAS if (perm_val == "TODOS" or u_data.get("usuario") == "admin") else [p.strip() for p in perm_val.split(",") if p.strip()]
                            ent_val = u_data.get("ent_str", "TODOS")
                            st.session_state["permisos_entornos"] = TODOS_LOS_ENTORNOS if (ent_val == "TODOS" or u_data.get("usuario") == "admin") else [e.strip() for e in ent_val.split(",") if e.strip()]
                            st.session_state["paso_login"] = 1
                            st.session_state["login_temp_data"] = {}
                            login_container.empty()
                            st.rerun()
                        else: st.error("❌ Contraseña incorrecta.")

        return False
    return True

if not validar_login(): st.stop()

st.markdown("""<style>#MainMenu {visibility: hidden;} header {visibility: visible !important;} footer {visibility: hidden;} .stAppDeployButton {display:none !important;} [data-testid="stDecoration"] {display:none !important;} [data-testid="stStatusWidget"] {display:none !important;} [data-testid="stSidebar"] {border-top: 5px solid #7AB800 !important;} .titulo-tablero { font-size: 1.35rem !important; font-weight: 700 !important; color: var(--text-color); border-bottom: 3px solid #7AB800 !important; }</style>""", unsafe_allow_html=True)

if LOGO_PATH: st.sidebar.image(LOGO_PATH, use_container_width=True)

entornos_permitidos = [e for e in TODOS_LOS_ENTORNOS if e in st.session_state.get("permisos_entornos", [])]
if not entornos_permitidos: st.warning("⚠️ No tienes permisos asignados."); st.stop()

if len(entornos_permitidos) > 1:
    modulo_seleccionado = st.sidebar.radio("📌 Seleccione Entorno de Gestión:", [f"📊 {e}" if e == "Auditoría Interna" else f"🏛️ {e}" for e in entornos_permitidos], index=0, key="radio_modulo_global")
    entorno_activo = "Auditoría Interna" if "Auditoría" in modulo_seleccionado else "Contraloría de Bogotá"
else: entorno_activo = entornos_permitidos[0]

user_actual_str = st.session_state.get("usuario_actual", "")
if user_actual_str.lower() in [u.lower() for u in USUARIOS_AMARILLOS]:
    notifs_lista = obtener_notificaciones_usuario(user_actual_str)
    sin_leer_cnt = len(notifs_lista)
    label_campana = f"🔔 Notificaciones ({sin_leer_cnt})" if sin_leer_cnt > 0 else "🔔 Notificaciones (0)"
    
    with st.sidebar.expander(label_campana, expanded=False):
        if notifs_lista:
            for notif in notifs_lista:
                st.markdown(
                    f'''
                    <div style="border-bottom: 1px solid rgba(255,255,255,0.1); padding: 6px 0; font-size: 0.78rem;">
                        <span style="font-weight: bold; color: #7AB800;">[{notif['entorno']}]</span><br>
                        📄 <b>{notif['archivo']}</b><br>
                        <a href="{notif['link_drive']}" target="_blank" style="color: #4B92DB;">📂 Abrir evidencia en Drive</a>
                        <span style="float: right; color: #718096; font-size: 0.7rem;">{notif['fecha']}</span>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
        else:
            st.caption("No hay notificaciones recientes de evidencias.")

st.sidebar.markdown("---")

def buscar_excel_inteligente():
    dir_script = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    dir_padre = os.path.dirname(dir_script)
    for nombre in ["TABLERO_PA_AI.xlsm", "TABLERO_PA_AI.xlsx", "TABLERO_PA_I.xlsm", "TABLERO_PA_I.xlsx"]:
        if os.path.exists(os.path.join(dir_script, nombre)): return os.path.join(dir_script, nombre)
        if os.path.exists(os.path.join(dir_padre, nombre)): return os.path.join(dir_padre, nombre)
    return os.path.join(dir_script, "TABLERO_PA_AI.xlsx")

EXCEL_PATH_AI = buscar_excel_inteligente()

def buscar_excel_contraloria():
    dir_script = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    dir_padre = os.path.dirname(dir_script)
    for nombre in ["TABLERO_PA_C.xlsx", "TABLERO_PA_C.xlsm"]:
        if os.path.exists(os.path.join(dir_script, nombre)): return os.path.join(dir_script, nombre)
        if os.path.exists(os.path.join(dir_padre, nombre)): return os.path.join(dir_padre, nombre)
    return os.path.join(dir_script, "TABLERO_PA_C.xlsx")

EXCEL_PATH_C = buscar_excel_contraloria()

def buscar_columna_por_patron(df, patrones):
    for col in df.columns:
        col_clean = str(col).lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        for pat in patrones:
            if pat in col_clean: return col
    return None

@st.cache_data(ttl=600, show_spinner=False)
def cargar_datos_ai_cached(path):
    if not os.path.exists(path): return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    xls = pd.ExcelFile(path)
    sheet_b = "Base de datos" if "Base de datos" in xls.sheet_names else ("Base de Datos" if "Base de Datos" in xls.sheet_names else xls.sheet_names[0])
    df_base = pd.read_excel(xls, sheet_name=sheet_b)
    df_base.columns = [str(c).strip() for c in df_base.columns]
    for col in df_base.columns:
        if df_base[col].dtype == "object": df_base[col] = df_base[col].astype(str).str.strip()
    sheet_c = "Calculos" if "Calculos" in xls.sheet_names else ("Cálculos" if "Cálculos" in xls.sheet_names else None)
    df_calc = pd.read_excel(xls, sheet_name=sheet_c, header=None) if sheet_c else pd.DataFrame()
    sheet_inf = "Informes PDF" if "Informes PDF" in xls.sheet_names else ("INFORMES PDF" if "INFORMES PDF" in xls.sheet_names else None)
    df_informes = pd.read_excel(xls, sheet_name=sheet_inf) if sheet_inf else pd.DataFrame()
    sheet_paa = "Programa Anual de Auditoría" if "Programa Anual de Auditoría" in xls.sheet_names else ("Programa Anual de Auditoria" if "Programa Anual de Auditoria" in xls.sheet_names else None)
    df_paa = pd.read_excel(xls, sheet_name=sheet_paa) if sheet_paa else pd.DataFrame()
    return df_base, df_calc, df_informes, df_paa

@st.cache_data(ttl=600, show_spinner=False)
def cargar_datos_c_cached(path):
    if not os.path.exists(path): return pd.DataFrame(), pd.DataFrame()
    xls = pd.ExcelFile(path)
    sheet_b = "Base de Datos" if "Base de Datos" in xls.sheet_names else ("Base de datos" if "Base de datos" in xls.sheet_names else xls.sheet_names[0])
    df_base = pd.read_excel(xls, sheet_name=sheet_b)
    df_base.columns = [str(c).strip() for c in df_base.columns]
    for col in df_base.columns:
        if df_base[col].dtype == "object": df_base[col] = df_base[col].astype(str).str.strip()
    sheet_inf = "Enlace PDF" if "Enlace PDF" in xls.sheet_names else ("Enlace pdf" if "Enlace pdf" in xls.sheet_names else None)
    df_informes = pd.read_excel(xls, sheet_name=sheet_inf) if sheet_inf else pd.DataFrame()
    return df_base, df_informes

pestañas_permitidas = [p for p in TODAS_LAS_PESTANIAS if p in st.session_state.get("permisos_usuario", [])]
if not pestañas_permitidas: st.warning("⚠️ No tienes permisos para ninguna pestaña."); st.stop()

pestañas_objetos = st.tabs(pestañas_permitidas)

if entorno_activo == "Auditoría Interna":
    df_raw, df_calc, df_informes_raw, df_paa_raw = cargar_datos_ai_cached(EXCEL_PATH_AI)
    if df_raw.empty:
        st.error(f"⚠️ No se encontró el archivo Excel en: `{EXCEL_PATH_AI}`")
        st.stop()

    col_estado = "Estado" if "Estado" in df_raw.columns else buscar_columna_por_patron(df_raw, ["estado del compromiso", "estado compromiso"])
    col_responsable = "Responsable" if "Responsable" in df_raw.columns else buscar_columna_por_patron(df_raw, ["responsable", "area responsable"])
    col_plan = "Plan Auditoría" if "Plan Auditoría" in df_raw.columns else buscar_columna_por_patron(df_raw, ["plan auditoria", "vigencia"])
    col_riesgo = "Nivel de Riesgo" if "Nivel de Riesgo" in df_raw.columns else buscar_columna_por_patron(df_raw, ["nivel de riesgo", "riesgo"])

    # RENDERIZADO DE PESTAÑAS EN AUDITORÍA INTERNA
    for i, nombre_pest in enumerate(pestañas_permitidas):
        with pestañas_objetos[i]:
            if nombre_pest == "Tablero":
                st.markdown("### 📊 Vista Principal del Tablero - Auditoría Interna")
                col_m1, col_m2, col_m3 = st.columns(3)
                tot_p = len(df_raw)
                abiertos_cnt = len(df_raw[df_raw[col_estado].astype(str).str.upper().str.contains("ABIERTO", na=False)]) if col_estado else 0
                vencidos_cnt = len(df_raw[df_raw[col_estado].astype(str).str.upper().str.contains("VENCIDO", na=False)]) if col_estado else 0
                
                col_m1.metric("TOTAL HALLAZGOS", tot_p)
                col_m2.metric("COMPROMISOS ABIERTOS", abiertos_cnt)
                col_m3.metric("COMPROMISOS VENCIDOS", vencidos_cnt)

                st.markdown("---")
                if col_responsable and col_estado:
                    fig = px.histogram(df_raw, x=col_responsable, color=col_estado, title="Top Responsables con Pendientes por Estado", barmode="stack")
                    st.plotly_chart(fig, use_container_width=True)

            elif nombre_pest == "Programa Anual":
                st.markdown("### 📅 Programa Anual de Auditoría")
                if not df_paa_raw.empty: st.dataframe(df_paa_raw, use_container_width=True)
                else: st.info("No hay información cargada en el Programa Anual.")

            elif nombre_pest == "Métricas":
                st.markdown("### 📈 Métricas de Gestión")
                st.dataframe(df_raw, use_container_width=True)

            elif nombre_pest == "Indicadores de Gestión":
                st.markdown("### 🎯 Indicadores de Gestión")
                st.caption("Resumen consolidado de porcentajes de cumplimiento y mora.")

            elif nombre_pest == "Histórico":
                st.markdown("### 📜 Histórico de Compromisos")
                st.dataframe(df_raw, use_container_width=True)

            elif nombre_pest == "Alertas y Edición":
                st.markdown("### ⚠️ Alertas y Edición de Compromisos")
                st.caption("Herramienta de actualización de estados.")

            elif nombre_pest == "Oficios":
                st.markdown("### ✉️ Oficios y Comunicaciones")

            elif nombre_pest == "Informes":
                st.markdown("### 📄 Informes PDF")
                if not df_informes_raw.empty: st.dataframe(df_informes_raw, use_container_width=True)

else:
    df_raw_c, df_informes_raw_c = cargar_datos_c_cached(EXCEL_PATH_C)
    if df_raw_c.empty:
        st.error(f"⚠️ No se encontró el archivo Excel de Contraloría en: `{EXCEL_PATH_C}`")
        st.stop()

    col_estado_c = "ESTADO AUDITOR" if "ESTADO AUDITOR" in df_raw_c.columns else buscar_columna_por_patron(df_raw_c, ["estado auditor", "estado"])
    col_resp_c = "AREA RESPONSABLE" if "AREA RESPONSABLE" in df_raw_c.columns else buscar_columna_por_patron(df_raw_c, ["area responsable", "responsable"])

    # RENDERIZADO DE PESTAÑAS EN CONTRALORÍA DE BOGOTÁ
    for i, nombre_pest in enumerate(pestañas_permitidas):
        with pestañas_objetos[i]:
            if nombre_pest == "Tablero":
                st.markdown("### 🏛️ Vista Principal del Tablero - Contraloría de Bogotá")
                col_m1, col_m2 = st.columns(2)
                tot_c = len(df_raw_c)
                cerradas_cnt = len(df_raw_c[df_raw_c[col_estado_c].astype(str).str.upper().str.contains("CERRAD", na=False)]) if col_estado_c else 0
                
                col_m1.metric("TOTAL HALLAZGOS CONTRALORÍA", tot_c)
                col_m2.metric("HALLAZGOS CERRADOS", cerradas_cnt)

                st.markdown("---")
                if col_resp_c:
                    fig_c = px.histogram(df_raw_c, x=col_resp_c, title="Hallazgos por Área Responsable en Contraloría")
                    st.plotly_chart(fig_c, use_container_width=True)

            elif nombre_pest == "Programa Anual":
                st.markdown("### 📅 Plan de Mejoramiento Contraloría")
                st.dataframe(df_raw_c, use_container_width=True)

            elif nombre_pest == "Métricas":
                st.markdown("### 📈 Métricas Contraloría")
                st.dataframe(df_raw_c, use_container_width=True)

            elif nombre_pest == "Indicadores de Gestión":
                st.markdown("### 🎯 Indicadores Contraloría")

            elif nombre_pest == "Histórico":
                st.markdown("### 📜 Histórico de Auditorías")
                st.dataframe(df_raw_c, use_container_width=True)

            elif nombre_pest == "Alertas y Edición":
                st.markdown("### ⚠️ Edición Contraloría")

            elif nombre_pest == "Oficios":
                st.markdown("### ✉️ Oficios Contraloría")

            elif nombre_pest == "Informes":
                st.markdown("### 📄 Informes y Anexos PDF")
                if not df_informes_raw_c.empty: st.dataframe(df_informes_raw_c, use_container_width=True)