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
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Tablero de Control - La Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# BÚSQUEDA DEL LOGO LOCAL
# ---------------------------------------------------------
def buscar_logo_local():
    dir_script = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    nombres_logo = ["logo_terminal.png", "logo_terminal.jpg", "logo.png", "logo.jpg"]
    for n in nombres_logo:
        ruta = os.path.join(dir_script, n)
        if os.path.exists(ruta):
            return ruta
    return None

LOGO_PATH = buscar_logo_local()

# ---------------------------------------------------------
# PERSISTENCIA LOCAL Y BASE DE DATOS
# ---------------------------------------------------------
DB_PATH = "usuarios_app.db"
JSON_USERS_FILE = "usuarios.json"

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

TODAS_LAS_SUBPESTANIAS = [
    "Planes Programados (Vigencia 2026)",
    "Planes Finalizados (Cierre Mensual + Histórico Completo)",
    "Programa Anual de Auditoría (PAA)",
    "Hallazgos Finalizados (% Hallazgo: Programados vs Finalizados 2026)",
    "Análisis por Planes de Acción",
    "Análisis por Hallazgos Únicos"
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

# CATÁLOGO OFICIAL DE ÁREAS RESPONSABLES DE LA TERMINAL
CATALOGO_OFICIAL_AREAS = [
    "DIRECCIÓN DE GESTIÓN FINANCIERA",
    "DIRECCIÓN DE RECURSOS FÍSICOS Y NEGOCIOS",
    "DIRECCIÓN DE GESTIÓN HUMANA",
    "DIRECCIÓN DE RECURSOS TECNOLÓGICOS",
    "DIRECCIÓN DE SEGURIDAD OPERACIONAL",
    "DIRECCIÓN DE SERVICIO AL TRANSPORTADOR",
    "DIRECCIÓN DE INFRAESTRUCTURA",
    "SUBGERENCIA JURÍDICA",
    "SUBGERENCIA CORPORATIVA",
    "SUBGERENCIA DE SERVICIOS OPERACIONALES E INFRAESTRUCTURA",
    "SUBGERENCIA DE PLANEACIÓN Y PROYECTOS",
    "OFICINA DE AUDITORÍA INTERNA"
]

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_password(password, hashed):
    return hmac.compare_digest(hash_password(password), str(hashed).strip())

def parsear_fecha_estricta(val):
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, (datetime, pd.Timestamp, date)):
        return pd.to_datetime(val)
        
    val_str = str(val).strip().lower()
    if val_str in ["nan", "none", "nat", "", "cierre", "cierre dd/mm/a", "cierre dd/mm/aa", "inicio", "inicio dd/mm/a"]:
        return pd.NaT

    try:
        val_num = float(val_str)
        if val_num > 30000:
            return pd.to_datetime(val_num, unit='D', origin='1899-12-30')
    except Exception:
        pass

    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", val_str)
    if match:
        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if y < 100:
            y += 2000
        try:
            return pd.Timestamp(year=y, month=m, day=d)
        except Exception:
            pass

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
            perm_subpestañas TEXT DEFAULT 'TODOS',
            perm_entornos TEXT DEFAULT 'TODOS',
            requiere_2fa INTEGER DEFAULT 1
        )
    ''')
    conn.commit()

    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN requiere_2fa INTEGER DEFAULT 1")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN perm_subpestañas TEXT DEFAULT 'TODOS'")
        conn.commit()
    except sqlite3.OperationalError:
        pass

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
        (u, email, pw_defecto, 1, 'TODOS', 'TODOS', 'TODOS', 0 if (u in USUARIOS_AMARILLOS or email in USUARIOS_AMARILLOS) else 1)
        for u, email in usuarios_base_raw
    ]

    if os.path.exists(JSON_USERS_FILE):
        try:
            with open(JSON_USERS_FILE, "r", encoding="utf-8") as f:
                usuarios_json = json.load(f)
                if usuarios_json:
                    usuarios_base = [
                        (
                            u["usuario"], 
                            u["email"], 
                            u["password_hash"], 
                            u.get("autorizado", 1), 
                            u.get("perm_pestañas", "TODOS"), 
                            u.get("perm_subpestañas", "TODOS"),
                            u.get("perm_entornos", "TODOS"),
                            0 if (u["usuario"] in USUARIOS_AMARILLOS or u["email"] in USUARIOS_AMARILLOS) else 1
                        ) 
                        for u in usuarios_json
                    ]
        except Exception:
            pass

    c.executemany('''
        INSERT OR IGNORE INTO usuarios (usuario, email, password_hash, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', usuarios_base)

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
    df = obtener_usuarios_df()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Usuarios')
    return buf.getvalue()

def obtener_usuarios_json_bytes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT usuario, email, password_hash, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa FROM usuarios")
    rows = c.fetchall()
    conn.close()

    lista_dict = [
        {
            "usuario": r[0],
            "email": r[1],
            "password_hash": r[2],
            "autorizado": r[3],
            "perm_pestañas": r[4],
            "perm_subpestañas": r[5],
            "perm_entornos": r[6],
            "requiere_2fa": r[7]
        }
        for r in rows
    ]

    return json.dumps(lista_dict, indent=4, ensure_ascii=False).encode('utf-8')

def exportar_y_sincronizar_usuarios():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT usuario, email, password_hash, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa FROM usuarios")
    rows = c.fetchall()
    conn.close()

    lista_dict = [
        {
            "usuario": r[0],
            "email": r[1],
            "password_hash": r[2],
            "autorizado": r[3],
            "perm_pestañas": r[4],
            "perm_subpestañas": r[5],
            "perm_entornos": r[6],
            "requiere_2fa": r[7]
        }
        for r in rows
    ]

    with open(JSON_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(lista_dict, f, indent=4, ensure_ascii=False)

def actualizar_permisos_usuario(usuario, lista_pestañas, lista_subpestañas, lista_entornos):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    perm_str = ",".join(lista_pestañas) if lista_pestañas else "TODOS"
    sub_str = ",".join(lista_subpestañas) if lista_subpestañas else "TODOS"
    ent_str = ",".join(lista_entornos) if lista_entornos else "TODOS"
    c.execute("UPDATE usuarios SET perm_pestañas = ?, perm_subpestañas = ?, perm_entornos = ? WHERE usuario = ?", (perm_str, sub_str, ent_str, usuario))
    conn.commit()
    conn.close()
    exportar_y_sincronizar_usuarios()

def guardar_o_actualizar_usuario(usuario, email, password, permisos_list, subpermisos_list, entornos_list, requiere_2fa=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    pw_hash = hash_password(password)
    perm_str = ",".join(permisos_list) if permisos_list else "TODOS"
    sub_str = ",".join(subpermisos_list) if subpermisos_list else "TODOS"
    ent_str = ",".join(entornos_list) if entornos_list else "TODOS"
    
    c.execute('''
        INSERT INTO usuarios (usuario, email, password_hash, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa)
        VALUES (?, ?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(usuario) DO UPDATE SET
            email=excluded.email,
            password_hash=excluded.password_hash,
            autorizado=1,
            perm_pestañas=excluded.perm_pestañas,
            perm_subpestañas=excluded.perm_subpestañas,
            perm_entornos=excluded.perm_entornos,
            requiere_2fa=excluded.requiere_2fa
    ''', (usuario, email, pw_hash, perm_str, sub_str, ent_str, requiere_2fa))
    conn.commit()
    conn.close()
    exportar_y_sincronizar_usuarios()

def enviar_correo_token(email_destino, token):
    try:
        smtp_config = st.secrets.get("smtp", {})
        server_host = smtp_config.get("server", "smtp.gmail.com")
        port = int(smtp_config.get("port", 587))
        remitente = smtp_config.get("user", "")
        password_remitente = smtp_config.get("password", "")

        if not remitente or not password_remitente:
            return False

        asunto = "Código de Acceso de 6 Dígitos - Tablero La Terminal"
        cuerpo = f"Hola,\n\nTu código de verificación de 6 dígitos para ingresar al sistema es: {token}\n\nSi no intentaste iniciar sesión, ignora este mensaje."

        msg = MIMEText(cuerpo)
        msg['Subject'] = asunto
        msg['From'] = remitente
        msg['To'] = email_destino

        with smtplib.SMTP(server_host, port) as server:
            server.starttls()
            server.login(remitente, password_remitente)
            server.sendmail(remitente, [email_destino], msg.as_string())
        return True
    except Exception:
        return False

def limpiar_nombre_area(texto):
    if not texto or pd.isna(texto):
        return ""
    txt = str(texto).upper().strip()
    txt = re.sub(r"\s+", " ", txt).strip()

    if "SERVICIOS OPERACIONALES" in txt or "SERVICIOS OPERA" in txt:
        return "SUBGERENCIA DE SERVICIOS OPERACIONALES E INFRAESTRUCTURA"
    if "PLANEACIÓN Y PROYECTOS" in txt or "PLANEACIONYPROYECTOS" in txt or "PLANEACION Y PROYECTOS" in txt:
        return "SUBGERENCIA DE PLANEACIÓN Y PROYECTOS"
    if "CORPORATIVA" in txt and ("SUBGERENCIA" in txt or "SUB GERENCIA" in txt):
        return "SUBGERENCIA CORPORATIVA"
    if "JURÍDICA" in txt or "JURIDICA" in txt:
        return "SUBGERENCIA JURÍDICA"
    if "GESTIÓN HUMANA" in txt or "GESTION HUMANA" in txt:
        return "DIRECCIÓN DE GESTIÓN HUMANA"
    if "RECURSOS TECNOLÓGICOS" in txt or "RECURSOS TECNOLOGICOS" in txt:
        return "DIRECCIÓN DE RECURSOS TECNOLÓGICOS"
    if "GESTIÓN FINANCIERA" in txt or "GESTION FINANCIERA" in txt:
        return "DIRECCIÓN DE GESTIÓN FINANCIERA"
    if "RECURSOS FÍSICOS" in txt or "RECURSOS FISICOS" in txt:
        return "DIRECCIÓN DE RECURSOS FÍSICOS Y NEGOCIOS"
    if "SEGURIDAD OPERACIONAL" in txt:
        return "DIRECCIÓN DE SEGURIDAD OPERACIONAL"
    if "SERVICIO AL TRANSPORTADOR" in txt:
        return "DIRECCIÓN DE SERVICIO AL TRANSPORTADOR"
    if "INFRAESTRUCTURA" in txt and ("DIRECCIÓN" in txt or "DIRECCION" in txt):
        return "DIRECCIÓN DE INFRAESTRUCTURA"
    if "AUDITORÍA INTERNA" in txt or "AUDITORIA INTERNA" in txt:
        return "OFICINA DE AUDITORÍA INTERNA"

    return txt

def extraer_sub_areas_individuales(val):
    if pd.isna(val):
        return []
    txt = str(val).upper().strip()
    
    txt = re.sub(r"SUBGERENCIAJ\s*URÍDICA|SUBGERENCIAJURIDICA", "SUBGERENCIA JURÍDICA", txt)
    txt = re.sub(r"SUB GERENCIA", "SUBGERENCIA", txt)
    
    txt_normalizado = txt.replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U")
    
    areas_encontradas = []
    for area in sorted(CATALOGO_OFICIAL_AREAS, key=len, reverse=True):
        area_norm = area.replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U")
        if area_norm in txt_normalizado:
            areas_encontradas.append(area)
            
    if not areas_encontradas:
        partes = re.split(r"[/,\n\r]+", txt)
        for p in partes:
            p_limp = limpiar_nombre_area(p)
            if p_limp and p_limp.lower() not in ["nan", "none"]:
                areas_encontradas.append(p_limp)
                
    res = []
    for a in CATALOGO_OFICIAL_AREAS:
        if a in areas_encontradas:
            res.append(a)
            
    for a in areas_encontradas:
        if a not in res:
            res.append(a)

    return res

# ---------------------------------------------------------
# SISTEMA DE LOGIN
# ---------------------------------------------------------
def validar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if "usuario_actual" not in st.session_state:
        st.session_state["usuario_actual"] = ""
    if "permisos_usuario" not in st.session_state:
        st.session_state["permisos_usuario"] = []
    if "permisos_subpestañas" not in st.session_state:
        st.session_state["permisos_subpestañas"] = []
    if "permisos_entornos" not in st.session_state:
        st.session_state["permisos_entornos"] = []
    if "paso_login" not in st.session_state:
        st.session_state["paso_login"] = 1
    if "login_temp_data" not in st.session_state:
        st.session_state["login_temp_data"] = {}

    if not st.session_state["autenticado"]:
        login_container = st.empty()
        
        with login_container.container():
            st.markdown(
                """
                <style>
                    button[data-testid="baseButton-primary"],
                    .stButton > button[kind="primary"],
                    .stButton > button {
                        background-color: #7AB800 !important;
                        background-image: none !important;
                        color: #FFFFFF !important;
                        border: none !important;
                        font-weight: bold !important;
                        border-radius: 6px !important;
                    }
                    button[data-testid="baseButton-primary"]:hover,
                    .stButton > button[kind="primary"]:hover,
                    .stButton > button:hover {
                        background-color: #689E00 !important;
                        color: #FFFFFF !important;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )

            _, col_main, _ = st.columns([1, 1.8, 1])
            
            with col_main:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                
                if LOGO_PATH:
                    st.image(LOGO_PATH, use_container_width=True)
                else:
                    st.markdown("<h1 style='text-align: center; color: #0077C8;'>🚌 LA TERMINAL</h1>", unsafe_allow_html=True)
                
                st.markdown("<h4 style='text-align: center; color: #0077C8; font-weight: bold; margin-top: 5px; margin-bottom: 20px;'>Tablero de Control y Gestión</h4>", unsafe_allow_html=True)
                
                st.markdown("### 🔒 Acceso Restringido")

                if st.session_state["paso_login"] == 1:
                    st.caption("Ingresa tu usuario o correo electrónico para continuar.")
                    
                    usuario_input = st.text_input("Usuario o Correo Electrónico", key="user_login_input").strip().lower()

                    if st.button("Continuar ➡️", type="primary", use_container_width=True):
                        if not usuario_input:
                            st.warning("⚠️ Por favor ingresa tu usuario o correo.")
                        else:
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute('''
                                SELECT usuario, email, password_hash, autorizado, perm_pestañas, perm_subpestañas, perm_entornos, requiere_2fa 
                                FROM usuarios 
                                WHERE LOWER(usuario) = ? OR LOWER(email) = ?
                            ''', (usuario_input, usuario_input))
                            row = c.fetchone()
                            conn.close()

                            if not row:
                                st.error("❌ El usuario o correo no se encuentra registrado.")
                            elif row[3] == 0:
                                st.error("🚫 Tu usuario no está autorizado para acceder. Contacta al administrador.")
                            else:
                                user_db, email_db, pw_hash, aut, perm_str, sub_str, ent_str, req_2fa = row
                                
                                es_exento = (user_db.lower() in [u.lower() for u in USUARIOS_AMARILLOS]) or (email_db.lower() in [e.lower() for e in USUARIOS_AMARILLOS]) or (req_2fa == 0)

                                st.session_state["login_temp_data"] = {
                                    "usuario": user_db,
                                    "email": email_db,
                                    "pw_hash": pw_hash,
                                    "perm_str": perm_str,
                                    "sub_str": sub_str,
                                    "ent_str": ent_str,
                                    "requiere_2fa": 0 if es_exento else 1
                                }

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

                                    enviado_ok = enviar_correo_token(email_db, token_6_digitos)
                                    if enviado_ok:
                                        st.session_state["paso_login"] = "otp"
                                        st.rerun()
                                    else:
                                        st.error("❌ Error al enviar el correo. Verifica las credenciales SMTP en Secrets.")

                elif st.session_state["paso_login"] == "password":
                    u_data = st.session_state.get("login_temp_data", {})
                    st.info(f"👤 Usuario: **{u_data.get('usuario')}**")
                    password_ingresada = st.text_input("Contraseña", type="password", key="pass_yellow_input")

                    if st.button("Iniciar Sesión 🚀", type="primary", use_container_width=True):
                        if verificar_password(password_ingresada, u_data.get("pw_hash")):
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = u_data.get("usuario")
                            
                            perm_val = u_data.get("perm_str", "TODOS")
                            if perm_val == "TODOS" or u_data.get("usuario") == "admin":
                                st.session_state["permisos_usuario"] = TODAS_LAS_PESTANIAS
                            else:
                                st.session_state["permisos_usuario"] = [p.strip() for p in perm_val.split(",") if p.strip()]

                            sub_val = u_data.get("sub_str", "TODOS")
                            if sub_val == "TODOS" or u_data.get("usuario") == "admin":
                                st.session_state["permisos_subpestañas"] = TODAS_LAS_SUBPESTANIAS
                            else:
                                st.session_state["permisos_subpestañas"] = [s.strip() for s in sub_val.split(",") if s.strip()]
                                
                            ent_val = u_data.get("ent_str", "TODOS")
                            if ent_val == "TODOS" or u_data.get("usuario") == "admin":
                                st.session_state["permisos_entornos"] = TODOS_LOS_ENTORNOS
                            else:
                                st.session_state["permisos_entornos"] = [e.strip() for e in ent_val.split(",") if e.strip()]

                            st.session_state["paso_login"] = 1
                            st.session_state["login_temp_data"] = {}
                            login_container.empty()
                            st.rerun()
                        else:
                            st.error("❌ Contraseña incorrecta.")

                    if st.button("⬅ Cambiar de Usuario"):
                        st.session_state["paso_login"] = 1
                        st.session_state["login_temp_data"] = {}
                        st.rerun()

                elif st.session_state["paso_login"] == "otp":
                    u_data = st.session_state.get("login_temp_data", {})
                    st.info(f"📧 Se ha enviado un código de verificación de 6 dígitos a: **{u_data.get('email')}**")

                    otp_ingresado = st.text_input("Ingresa el código de 6 dígitos recibido:", key="otp_code_input").strip()

                    if st.button("Verificar e Iniciar Sesión 🚀", type="primary", use_container_width=True):
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT token_recuperacion FROM usuarios WHERE usuario = ?", (u_data.get("usuario"),))
                        row = c.fetchone()

                        if row and row[0] == otp_ingresado:
                            c.execute("UPDATE usuarios SET token_recuperacion = NULL WHERE usuario = ?", (u_data.get("usuario"),))
                            conn.commit()
                            conn.close()

                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = u_data.get("usuario")
                            
                            perm_val = u_data.get("perm_str", "TODOS")
                            if perm_val == "TODOS" or u_data.get("usuario") == "admin":
                                st.session_state["permisos_usuario"] = TODAS_LAS_PESTANIAS
                            else:
                                st.session_state["permisos_usuario"] = [p.strip() for p in perm_val.split(",") if p.strip()]

                            sub_val = u_data.get("sub_str", "TODOS")
                            if sub_val == "TODOS" or u_data.get("usuario") == "admin":
                                st.session_state["permisos_subpestañas"] = TODAS_LAS_SUBPESTANIAS
                            else:
                                st.session_state["permisos_subpestañas"] = [s.strip() for s in sub_val.split(",") if s.strip()]
                                
                            ent_val = u_data.get("ent_str", "TODOS")
                            if ent_val == "TODOS" or u_data.get("usuario") == "admin":
                                st.session_state["permisos_entornos"] = TODOS_LOS_ENTORNOS
                            else:
                                st.session_state["permisos_entornos"] = [e.strip() for e in ent_val.split(",") if e.strip()]

                            st.session_state["paso_login"] = 1
                            st.session_state["login_temp_data"] = {}
                            login_container.empty()
                            st.rerun()
                        else:
                            conn.close()
                            st.error("❌ Código de verificación incorrecto.")

                    if st.button("⬅️ Cambiar de Usuario"):
                        st.session_state["paso_login"] = 1
                        st.session_state["login_temp_data"] = {}
                        st.rerun()

        return False
    return True

if not validar_login():
    st.stop()

# ---------------------------------------------------------
# ESTILOS CSS PRINCIPALES DEL TABLERO
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: visible !important;}
        footer {visibility: hidden;}
        .stAppDeployButton {display:none !important;}
        [data-testid="stDecoration"] {display:none !important;}
        [data-testid="stStatusWidget"] {display:none !important;}
        
        div[data-testid="stManageApp"] {display: none !important;}
        div[class*="stManageApp"] {display: none !important;}
        button[title*="Manage app"] {display: none !important;}
        iframe[title*="manage-app"] {display: none !important;}

        .plotly .modebar,
        button[title="View fullscreen"] {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }

        [data-testid="stSidebarCollapsedControl"] {
            display: block !important;
            visibility: visible !important;
            z-index: 1000000 !important;
        }

        [data-testid="stSidebar"] {
            border-top: 5px solid #7AB800 !important;
            padding-top: 0px !important;
        }

        [data-testid="stSidebarContent"] {
            padding-top: 0px !important;
        }

        [data-testid="stSidebar"] [data-testid="stImage"] {
            margin-top: -10px !important;
            padding-top: 0px !important;
        }

        /* PERMITIR QUE LOS DESPLEGABLES DEL SIDEBAR MUESTREN EL TEXTO COMPLETO SIN CORTARSE */
        [data-testid="stSidebar"] div[role="listbox"] {
            width: max-content !important;
            min-width: 100% !important;
            max-width: 480px !important;
            white-space: normal !important;
        }
        [data-testid="stSidebar"] div[role="option"] {
            white-space: normal !important;
            word-break: break-word !important;
        }

        /* PERMITIR SALTO DE LÍNEA EN LAS ETIQUETAS SELECCIONADAS DEL MULTISELECT */
        [data-testid="stSidebar"] div[data-baseweb="tag"] {
            max-width: 100% !important;
            height: auto !important;
            white-space: normal !important;
            word-break: break-word !important;
        }
        [data-testid="stSidebar"] div[data-baseweb="tag"] span {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        .block-container {
            padding-top: 0.8rem !important;
            padding-bottom: 1rem !important;
        }

        hr {
            margin-top: 0.2rem !important;
            margin-bottom: 0.4rem !important;
        }

        div[data-testid="stPlotlyChart"] {
            margin-bottom: -20px !important;
        }

        button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background-color: #7AB800 !important;
            background-image: none !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: bold !important;
        }
        button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            background-color: #689E00 !important;
            color: #FFFFFF !important;
        }

        .titulo-tablero {
            font-size: 1.35rem !important;
            font-weight: 700 !important;
            color: var(--text-color);
            margin: 0 0 10px 0 !important;
            padding-bottom: 6px !important;
            line-height: 1.3 !important;
            display: flex !important;
            align-items: center !important;
            gap: 15px !important;
            border-bottom: 3px solid #7AB800 !important;
        }

        .block-header {
            text-align: center;
            font-weight: bold;
            font-size: 0.85rem;
            color: var(--text-color);
            margin-bottom: 4px;
            margin-top: 2px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .card-box {
            border-radius: 6px;
            padding: 4px 8px;
            text-align: center;
            font-weight: bold;
            color: #000;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.08);
            margin-bottom: 4px;
        }

        [data-testid="stHorizontalBlock"] {
            align-items: flex-start !important;
        }

        div[data-testid="stDataFrame"] {
            margin-top: 8px !important;
            padding-top: 0px !important;
        }

        .titulo-seccion-finaliz {
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            color: var(--text-color);
            margin: 0 0 10px 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
            white-space: nowrap !important;
        }

        .month-container {
            margin-left: 0 !important;
            margin-top: 8px !important;
        }
        .month-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 2px 0;
            font-weight: bold;
            font-size: 0.82rem;
            color: var(--text-color);
            width: 175px !important;
        }
        .month-box {
            background-color: #D9EAD3;
            width: 44px;
            text-align: center;
            padding: 2px 0;
            border-radius: 4px;
            color: #000;
        }
        .month-box-fin {
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.25);
            width: 44px;
            text-align: center;
            padding: 2px 0;
            border-radius: 4px;
            color: var(--text-color);
            font-weight: bold;
        }
        .alert-card-horiz {
            background-color: rgba(241, 245, 249, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            padding: 6px 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-weight: bold;
            font-size: 0.85rem;
            color: var(--text-color);
            width: 100%;
            margin-bottom: 4px;
        }
        .alert-val-box {
            background-color: #EFEFEF;
            width: 38px;
            text-align: center;
            padding: 3px 0;
            border-radius: 4px;
            color: #000;
            font-weight: bold;
            font-size: 0.85rem;
        }
        .small-note {
            background-color: rgba(75, 146, 219, 0.15);
            border-left: 4px solid #2B6CB0;
            padding: 8px 14px;
            border-radius: 4px;
            font-size: 0.82rem;
            color: var(--text-color);
            margin-bottom: 12px;
            line-height: 1.4;
        }
        .total-acciones-box {
            background-color: rgba(241, 245, 249, 0.15);
            border: 1px solid #CBD5E1;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 1.1rem;
            color: var(--text-color);
            display: inline-block;
            margin-bottom: 12px;
        }
        div[data-testid="stDownloadButton"] button {
            background-color: #28A745 !important;
            color: #FFFFFF !important;
            border: 1px solid #218838 !important;
            font-weight: bold !important;
        }
        div[data-testid="stDownloadButton"] button:hover {
            background-color: #218838 !important;
            color: #FFFFFF !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# SELECTOR DINÁMICO DE ENTORNO SEGÚN PERMISOS DE USUARIO
# ---------------------------------------------------------
if LOGO_PATH:
    st.sidebar.image(LOGO_PATH, use_container_width=True)

entornos_permitidos = [e for e in TODOS_LOS_ENTORNOS if e in st.session_state.get("permisos_entornos", [])]

if not entornos_permitidos:
    st.warning("⚠️ No tienes permisos asignados para ver ningún Entorno de Gestión. Contacta al administrador.")
    st.stop()

if len(entornos_permitidos) > 1:
    modulo_seleccionado = st.sidebar.radio(
        "📌 Seleccione Entorno de Gestión:",
        [f"📊 {e}" if e == "Auditoría Interna" else f"🏛️ {e}" for e in entornos_permitidos],
        index=0,
        key="radio_modulo_global"
    )
    entorno_activo = "Auditoría Interna" if "Auditoría" in modulo_seleccionado else "Contraloría de Bogotá"
else:
    entorno_activo = entornos_permitidos[0]

st.sidebar.markdown("---")

col_head_logo, col_head_title = st.columns([1, 4])
with col_head_logo:
    if LOGO_PATH:
        st.image(LOGO_PATH, use_container_width=True)
    else:
        st.markdown("🚌 **LA TERMINAL**")

with col_head_title:
    if entorno_activo == "Auditoría Interna":
        st.markdown('<div class="titulo-tablero">Tablero de Control y Gestión - Auditoría Interna</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="titulo-tablero">Tablero de Control - Planes de Acción Contraloría de Bogotá</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# BÚSQUEDA Y CARGA DE EXCEL DE AUDITORÍA INTERNA
# ---------------------------------------------------------
def buscar_excel_inteligente():
    dir_script = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    dir_padre = os.path.dirname(dir_script)
    nombres_posibles = ["TABLERO_PA_AI.xlsm", "TABLERO_PA_AI.xlsx", "TABLERO_PA_I.xlsm", "TABLERO_PA_I.xlsx"]

    for nombre in nombres_posibles:
        ruta = os.path.join(dir_script, nombre)
        if os.path.exists(ruta):
            return ruta
    for nombre in nombres_posibles:
        ruta = os.path.join(dir_padre, nombre)
        if os.path.exists(ruta):
            return ruta

    return os.path.join(dir_script, "TABLERO_PA_AI.xlsx")

EXCEL_PATH_AI = buscar_excel_inteligente()

def buscar_excel_contraloria():
    dir_script = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    dir_padre = os.path.dirname(dir_script)
    nombres_posibles = ["TABLERO_PA_C.xlsx", "TABLERO_PA_C.xlsm"]

    for nombre in nombres_posibles:
        ruta = os.path.join(dir_script, nombre)
        if os.path.exists(ruta):
            return ruta
    for nombre in nombres_posibles:
        ruta = os.path.join(dir_padre, nombre)
        if os.path.exists(ruta):
            return ruta

    return os.path.join(dir_script, "TABLERO_PA_C.xlsx")

EXCEL_PATH_C = buscar_excel_contraloria()

def buscar_columna_por_patron(df, patrones):
    for col in df.columns:
        col_clean = str(col).lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        for pat in patrones:
            if pat in col_clean:
                return col
    return None

def filtrar_solo_columnas_amarillas_ai(df):
    columnas_permitidas_exactas = [
        "Plan Auditoría",
        "Auditoría",
        "Titulo del Hallazgo",
        "Transcribir el del Hallazgo o Situación Evidenciada",
        "Nivel del Riesgo",
        "Plan de Acción",
        "Responsable",
        "Inicio",
        "Cierre",
        "Enlace para cargar evidencias",
        "Estado",
        "Alerta 10 días",
        "Alerta 20 días",
        "Alerta 30 días",
        "Alerta 5 días"
    ]

    cols_finales = []
    for col_req in columnas_permitidas_exactas:
        col_m = None
        for c_df in df.columns:
            if str(c_df).strip().lower() == col_req.lower():
                col_m = c_df
                break
        if not col_m:
            if "transcribir" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["transcribir el del hallazgo", "situacion evidenciada"])
            elif "enlace" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["enlace para cargar evidencias", "cargar evidencias"])
            elif "inicio" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["inicio"])
            elif "cierre" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["cierre", "fecha cierre", "fecha compromiso"])
            elif "estado" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["estado del compromiso", "estado compromiso"]) or ("Estado" if "Estado" in df.columns else None)

        if col_m and col_m in df.columns and col_m not in cols_finales:
            cols_finales.append(col_m)

    return df[cols_finales].copy() if cols_finales else df.copy()

def filtrar_solo_columnas_amarillas_c(df):
    columnas_c_exactas = [
        "VIGENCIA DE LA AUDITORÍA O VISITA",
        "CODIGO AUDITORÍA SEGÚN PAD DE LA VIGENCIA",
        "No. HALLAZGO",
        "CODIGO ACCION",
        "DESCRIPCIÓN HALLAZGO",
        "DESCRIPCIÓN ACCIÓN",
        "AREA RESPONSABLE",
        "FECHA DE INICIO",
        "FECHA DE TERMINACIÓN",
        "ESTADO",
        "ENLACE PARA CARGAR EVIDENCIAS",
        "Alerta 10",
        "Alerta 20",
        "Alerta 30",
        "Alerta 5"
    ]

    cols_finales = []
    for col_req in columnas_c_exactas:
        col_m = None
        for c_df in df.columns:
            if str(c_df).strip().lower() == col_req.lower():
                col_m = c_df
                break
        if not col_m:
            if "vigencia" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["vigencia de la auditoria"])
            elif "descripcion accion" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["descripcion accion"])
            elif "area responsable" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["area responsable", "dependencia"])
            elif "inicio" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["fecha de inicio"])
            elif "terminacion" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["fecha de terminacion"])
            elif "enlace" in col_req.lower():
                col_m = buscar_columna_por_patron(df, ["enlace para cargar evidencias", "evidencias"])

        if col_m and col_m in df.columns and col_m not in cols_finales:
            cols_finales.append(col_m)

    return df[cols_finales].copy() if cols_finales else df.copy()

def generar_excel_formateado_ai(df):
    output = io.BytesIO()
    df_export = filtrar_solo_columnas_amarillas_ai(df)

    for col in df_export.columns:
        if any(p in str(col).lower() for p in ["fecha", "terminacion", "cierre", "inicio", "vencimiento"]):
            def formatear_fecha_limpia(val):
                if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "nat", ""]:
                    return ""
                if isinstance(val, (datetime, pd.Timestamp, date)):
                    return val.strftime("%d/%m/%Y")
                val_str = str(val).strip()
                try:
                    dt = pd.to_datetime(val_str, dayfirst=True, errors="coerce")
                    if pd.notnull(dt):
                        return dt.strftime("%d/%m/%Y")
                except Exception:
                    pass
                return val_str
            df_export[col] = df_export[col].apply(formatear_fecha_limpia)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Detalle_Compromisos")
        workbook = writer.book
        worksheet = writer.sheets["Detalle_Compromisos"]
        header_format = workbook.add_format({"bold": True, "text_wrap": True, "valign": "vcenter", "align": "center", "fg_color": "#1F4E78", "font_color": "#FFFFFF", "border": 1})
        cell_format = workbook.add_format({"valign": "vcenter", "border": 1})
        date_cell_format = workbook.add_format({"valign": "vcenter", "align": "center", "border": 1})

        for col_num, value in enumerate(df_export.columns.values):
            worksheet.write(0, col_num, str(value), header_format)

        for i, col in enumerate(df_export.columns):
            es_col_fecha = any(p in str(col).lower() for p in ["fecha", "terminacion", "cierre", "inicio", "vencimiento"])
            longitudes = [len(str(val)) for val in df_export[col].dropna().tolist()] if not df_export.empty else []
            max_len = max(longitudes) if longitudes else 0
            adjusted_width = min(max(max_len + 4, len(str(col)) + 4, 14), 65)
            worksheet.set_column(i, i, adjusted_width, date_cell_format if es_col_fecha else cell_format)

        worksheet.hide_gridlines(2)
    return output.getvalue()

def generar_excel_formateado_c(df):
    output = io.BytesIO()
    df_export = filtrar_solo_columnas_amarillas_c(df)

    for col in df_export.columns:
        if any(p in str(col).lower() for p in ["fecha", "terminacion", "cierre", "inicio", "vencimiento"]):
            def formatear_fecha_limpia(val):
                if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "nat", ""]:
                    return ""
                if isinstance(val, (datetime, pd.Timestamp, date)):
                    return val.strftime("%d/%m/%Y")
                val_str = str(val).strip()
                try:
                    dt = pd.to_datetime(val_str, dayfirst=True, errors="coerce")
                    if pd.notnull(dt):
                        return dt.strftime("%d/%m/%Y")
                except Exception:
                    pass
                return val_str
            df_export[col] = df_export[col].apply(formatear_fecha_limpia)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Detalle_Contraloria")
        workbook = writer.book
        worksheet = writer.sheets["Detalle_Contraloria"]
        header_format = workbook.add_format({"bold": True, "text_wrap": True, "valign": "vcenter", "align": "center", "fg_color": "#1F4E78", "font_color": "#FFFFFF", "border": 1})
        cell_format = workbook.add_format({"valign": "vcenter", "border": 1})
        date_cell_format = workbook.add_format({"valign": "vcenter", "align": "center", "border": 1})

        for col_num, value in enumerate(df_export.columns.values):
            worksheet.write(0, col_num, str(value), header_format)

        for i, col in enumerate(df_export.columns):
            es_col_fecha = any(p in str(col).lower() for p in ["fecha", "terminacion", "cierre", "inicio", "vencimiento"])
            longitudes = [len(str(val)) for val in df_export[col].dropna().tolist()] if not df_export.empty else []
            max_len = max(longitudes) if longitudes else 0
            adjusted_width = min(max(max_len + 4, len(str(col)) + 4, 14), 65)
            worksheet.set_column(i, i, adjusted_width, date_cell_format if es_col_fecha else cell_format)

        worksheet.hide_gridlines(2)
    return output.getvalue()

# =========================================================
# VISTA 1: AUDITORÍA INTERNA
# =========================================================
if entorno_activo == "Auditoría Interna":
    def cargar_datos_ai():
        if not os.path.exists(EXCEL_PATH_AI):
            st.error(f"⚠️ No se encontró el archivo Excel en: `{EXCEL_PATH_AI}`")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        try:
            xls = pd.ExcelFile(EXCEL_PATH_AI)
            sheet_b = "Base de datos" if "Base de datos" in xls.sheet_names else ("Base de Datos" if "Base de Datos" in xls.sheet_names else xls.sheet_names[0])
            df_base = pd.read_excel(xls, sheet_name=sheet_b)
            df_base.columns = [str(c).strip() for c in df_base.columns]

            for col in df_base.columns:
                if df_base[col].dtype == "object":
                    df_base[col] = df_base[col].astype(str).str.strip()

            sheet_c = "Calculos" if "Calculos" in xls.sheet_names else ("Cálculos" if "Cálculos" in xls.sheet_names else None)
            df_calc = pd.read_excel(xls, sheet_name=sheet_c, header=None) if sheet_c else pd.DataFrame()

            sheet_inf = "Informes PDF" if "Informes PDF" in xls.sheet_names else ("INFORMES PDF" if "INFORMES PDF" in xls.sheet_names else None)
            df_informes = pd.read_excel(xls, sheet_name=sheet_inf) if sheet_inf else pd.DataFrame()

            sheet_paa = "Programa Anual de Auditoría" if "Programa Anual de Auditoría" in xls.sheet_names else ("Programa Anual de Auditoria" if "Programa Anual de Auditoria" in xls.sheet_names else None)
            df_paa = pd.read_excel(xls, sheet_name=sheet_paa) if sheet_paa else pd.DataFrame()

            return df_base, df_calc, df_informes, df_paa
        except Exception as e:
            st.error(f"Error al cargar el archivo Excel: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_raw, df_calc, df_informes_raw, df_paa_raw = cargar_datos_ai()

    if df_raw.empty:
        st.stop()

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
    
    col_link_evidencia = "Enlace para cargar evidencias" if "Enlace para cargar evidencias" in df_raw.columns else buscar_columna_por_patron(df_raw, ["enlace para cargar evidencias", "cargar evidencias"])

    col_a5 = "Alerta 5 días" if "Alerta 5 días" in df_raw.columns else buscar_columna_por_patron(df_raw, ["alerta 5"])
    col_a10 = "Alerta 10 días" if "Alerta 10 días" in df_raw.columns else buscar_columna_por_patron(df_raw, ["alerta 10"])
    col_a20 = "Alerta 20 días" if "Alerta 20 días" in df_raw.columns else buscar_columna_por_patron(df_raw, ["alerta 20"])
    col_a30 = "Alerta 30 días" if "Alerta 30 días" in df_raw.columns else buscar_columna_por_patron(df_raw, ["alerta 30"])

    if col_estado:
        df_raw[col_estado] = df_raw[col_estado].astype(str).str.capitalize()

    for col_f in [col_fecha_inicio, col_fecha_cierre, col_fecha_cierre_aud]:
        if col_f and col_f in df_raw.columns:
            def formatear_fecha_corta(val):
                if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "nat", ""]:
                    return ""
                if isinstance(val, (datetime, pd.Timestamp, date)):
                    return val.strftime("%d/%m/%Y")
                val_str = str(val).strip()
                try:
                    dt = pd.to_datetime(val_str, dayfirst=True, errors="coerce")
                    if pd.notnull(dt):
                        return dt.strftime("%d/%m/%Y")
                except Exception:
                    pass
                return val_str
            df_raw[col_f] = df_raw[col_f].apply(formatear_fecha_corta)

    meses_es = ["ENE", "FEB", "MAR", "ABR", "MAYO", "JUNIO", "JULIO", "AGO", "SEP", "OCT", "NOV", "DIC"]
    conteo_meses = {m: 0 for m in meses_es}

    if not df_calc.empty:
        for idx, row in df_calc.iterrows():
            val_m = str(row[0]).strip().lower()
            for idx_m, m_nombre in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]):
                if m_nombre in val_m:
                    conteo_meses[meses_es[idx_m]] = int(row[1]) if pd.notnull(row[1]) and str(row[1]).isdigit() else 0

    st.sidebar.title("🔍 Filtros Auditoría")

    st.sidebar.markdown(f"👤 **Usuario activo:** `{st.session_state.get('usuario_actual')}`")

    if st.session_state.get("usuario_actual") == "admin":
        with st.sidebar.expander("👤 Gestión de Usuarios y Permisos (Admin)"):
            st.caption("1. Registrar / Actualizar Usuario")
            new_u = st.text_input("Usuario", key="new_u_adm")
            new_e = st.text_input("Correo Electrónico", key="new_e_adm")
            new_p = st.text_input("Contraseña Inicial", type="password", key="new_p_adm")
            
            st.markdown("**Permisos de Acceso a Entornos:**")
            u_entornos = []
            for ent in TODOS_LOS_ENTORNOS:
                if st.checkbox(f"🌐 Entorno: {ent}", value=True, key=f"chk_ent_{ent}"):
                    u_entornos.append(ent)

            st.markdown("**Permisos de Acceso a Pestañas:**")
            u_permisos = []
            for pestania in TODAS_LAS_PESTANIAS:
                if st.checkbox(f"Ver {pestania}", value=True, key=f"chk_add_{pestania}"):
                    u_permisos.append(pestania)

            st.markdown("**Permisos de Acceso a Subpestañas:**")
            u_subpermisos = []
            for subp in TODAS_LAS_SUBPESTANIAS:
                if st.checkbox(f"🔹 {subp}", value=True, key=f"chk_add_sub_{subp}"):
                    u_subpermisos.append(subp)

            if st.button("Guardar / Autorizar Usuario"):
                if new_u and new_e and new_p:
                    guardar_o_actualizar_usuario(new_u.strip(), new_e.strip().lower(), new_p, u_permisos, u_subpermisos, u_entornos)
                    st.success(f"Usuario `{new_u}` actualizado localmente.")
                else:
                    st.warning("Completa todos los campos.")
                    
            st.divider()
            st.caption("2. Modificar Permisos Existentes a Múltiples Usuarios")
            df_users = obtener_usuarios_df()
            if not df_users.empty and 'usuario' in df_users.columns:
                lista_usuarios = df_users['usuario'].tolist()

                col_sel_all, col_clear_all = st.columns(2)
                with col_sel_all:
                    if st.button("✅ Seleccionar Todos", use_container_width=True, key="btn_sel_all_users_bulk"):
                        st.session_state["sel_mod_users_list"] = lista_usuarios
                        st.rerun()
                with col_clear_all:
                    if st.button("❌ Quitar Todos", use_container_width=True, key="btn_clear_all_users_bulk"):
                        st.session_state["sel_mod_users_list"] = []
                        st.rerun()

                if "sel_mod_users_list" not in st.session_state:
                    st.session_state["sel_mod_users_list"] = []

                users_sel = st.multiselect(
                    "Seleccionar usuario(s) a modificar:",
                    options=lista_usuarios,
                    default=st.session_state["sel_mod_users_list"],
                    key="sel_mod_users_multiselect"
                )

                if users_sel:
                    st.info(f"👥 Modificando permisos para **{len(users_sel)}** usuario(s).")

                    st.markdown("**Modificar Entornos Permitidos:**")
                    nuevos_ents = st.multiselect(
                        "Entornos:",
                        options=TODOS_LOS_ENTORNOS,
                        default=TODOS_LOS_ENTORNOS,
                        key="edit_ents_bulk"
                    )

                    st.markdown("**Modificar Pestañas Permitidas:**")
                    nuevos_perms = st.multiselect(
                        "Pestañas:",
                        options=TODAS_LAS_PESTANIAS,
                        default=TODAS_LAS_PESTANIAS,
                        key="edit_perms_bulk"
                    )

                    st.markdown("**Modificar Subpestañas Permitidas:**")
                    nuevos_subperms = st.multiselect(
                        "Subpestañas:",
                        options=TODAS_LAS_SUBPESTANIAS,
                        default=TODAS_LAS_SUBPESTANIAS,
                        key="edit_subperms_bulk"
                    )

                    if st.button(f"💾 Aplicar Permisos a los {len(users_sel)} Usuarios", type="primary", use_container_width=True, key="btn_apply_bulk_perms"):
                        for user in users_sel:
                            actualizar_permisos_usuario(user, nuevos_perms, nuevos_subperms, nuevos_ents)
                        st.success(f"¡Permisos actualizados con éxito para los {len(users_sel)} usuarios!")
                        st.rerun()

            st.divider()
            st.caption("3. 📦 Respaldo de Usuarios")
            
            excel_bytes = obtener_usuarios_excel_bytes()
            st.download_button(
                label="📊 Descargar usuarios.xlsx",
                data=excel_bytes,
                file_name=f"usuarios_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            json_bytes = obtener_usuarios_json_bytes()
            st.download_button(
                label="☁️ Descargar usuarios.json",
                data=json_bytes,
                file_name="usuarios.json",
                mime="application/json",
                use_container_width=True
            )

    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.session_state["usuario_actual"] = ""
        st.session_state["permisos_usuario"] = []
        st.session_state["permisos_subpestañas"] = []
        st.session_state["permisos_entornos"] = []
        st.rerun()

    st.sidebar.markdown("---")

    df_filtrado = df_raw.copy()

    if col_estado:
        estados_vals = sorted([e for e in df_raw[col_estado].dropna().unique() if str(e).lower() not in ["nan", "none", ""] and not re.search(r"finaliz|cerrad", str(e), re.IGNORECASE)])
        with st.sidebar.expander("📌 Estado del compromiso", expanded=False):
            estado_sel = st.multiselect("Seleccione Estados:", options=estados_vals, default=[], key="multi_estado")
        if estado_sel:
            df_filtrado = df_filtrado[df_filtrado[col_estado].isin(estado_sel)]

    if col_responsable:
        resp_unicos_set = set()
        for val in df_raw[col_responsable].dropna().unique():
            partes = re.split(r"[/,\n\r]+", str(val))
            for p in partes:
                p_limpia = limpiar_nombre_area(p)
                if p_limpia and p_limpia.upper() not in ["NAN", "NONE", ""]:
                    resp_unicos_set.add(p_limpia)
        
        resp_vals = sorted(list(resp_unicos_set))
        
        with st.sidebar.expander("👤 Responsables", expanded=False):
            resp_sel = st.multiselect("Seleccione Responsables:", options=resp_vals, default=[], key="multi_resp")
        if resp_sel:
            def evaluar_resp_ai(cell_val):
                if pd.isna(cell_val):
                    return False
                partes_celda = [limpiar_nombre_area(p) for p in re.split(r"[/,\n\r]+", str(cell_val))]
                return any(sel in partes_celda for sel in resp_sel)
                
            mask_resp = df_filtrado[col_responsable].apply(evaluar_resp_ai)
            df_filtrado = df_filtrado[mask_resp]

    if col_auditor_resp:
        aud_resp_vals = sorted(list(set([ar for ar in df_raw[col_auditor_resp].dropna().unique() if str(ar).lower() not in ["nan", "none", ""]])))
        with st.sidebar.expander("🧐 Auditor Responsable", expanded=False):
            aud_resp_sel = st.multiselect("Seleccione Auditores:", options=aud_resp_vals, default=[], key="multi_auditor_resp")
        if aud_resp_sel:
            df_filtrado = df_filtrado[df_filtrado[col_auditor_resp].isin(aud_resp_sel)]

    if col_apoyo_resp and col_apoyo_resp in df_raw.columns:
        apoyo_raw_list = []
        for val in df_raw[col_apoyo_resp].dropna().unique():
            val_norm = str(val).replace("Maryury", "Maryuri").replace("Carloina", "Carolina")
            names = [n.strip() for n in val_norm.replace("\n", ",").split(",") if n.strip() and n.strip().lower() not in ["nan", "none"]]
            apoyo_raw_list.extend(names)
        apoyo_vals = sorted(list(set(apoyo_raw_list)))
        
        with st.sidebar.expander("👥 Apoyo Responsable", expanded=False):
            apoyo_sel = st.multiselect("Seleccione Apoyo Responsable:", options=apoyo_vals, default=[], key="multi_apoyo_resp")
        if apoyo_sel:
            mask_apoyo = df_filtrado[col_apoyo_resp].fillna("").astype(str).apply(
                lambda x: any(sel.lower() in str(x).replace("maryury", "maryuri").replace("carloina", "carolina").lower() for sel in apoyo_sel)
            )
            df_filtrado = df_filtrado[mask_apoyo]

    if col_plan_filtro:
        plan_vals = sorted(list(set([p for p in df_raw[col_plan_filtro].dropna().unique() if str(p).lower() not in ["nan", "none", ""]])))
        with st.sidebar.expander("📁 Plan Auditoría / Vigencia", expanded=False):
            plan_sel = st.multiselect("Seleccione Planes:", options=plan_vals, default=[], key="multi_plan")
        if plan_sel:
            df_filtrado = df_filtrado[df_filtrado[col_plan_filtro].isin(plan_sel)]

    if col_auditoria:
        aud_vals = sorted(list(set([a for a in df_raw[col_auditoria].dropna().unique() if str(a).lower() not in ["nan", "none", ""]])))
        with st.sidebar.expander("🔬 Auditoría Específica", expanded=False):
            auditoria_sel = st.multiselect("Seleccione Auditorías:", options=aud_vals, default=[], key="multi_auditoria")
        if auditoria_sel:
            df_filtrado = df_filtrado[df_filtrado[col_auditoria].isin(auditoria_sel)]

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
        fechas_ai_parsed = df_raw_venc_ai[col_fecha_cierre].apply(parsear_fecha_estricta)
        dias_mora_ai_series = (hoy_dt - fechas_ai_parsed).dt.days.dropna()
        dias_mora_ai_series = dias_mora_ai_series[dias_mora_ai_series > 0]
        prom_mora_ai_val = int(round(dias_mora_ai_series.mean())) if not dias_mora_ai_series.empty else 0
    else:
        prom_mora_ai_val = 0

    pct_abiertos = round((abiertos / total_planes_pendientes) * 100) if total_planes_pendientes > 0 else 0

    # ---------------------------------------------------------
    # CONSTRUCCIÓN DE GRÁFICOS AUDITORÍA INTERNA
    # ---------------------------------------------------------
    meses_orden = ["ENE", "FEB", "MAR", "ABR", "MAYO", "JUNIO", "JULIO", "AGO", "SEP", "OCT", "NOV", "DIC"]
    map_m_num = {1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"}

    data_tend_abiertos = {m: 0 for m in meses_orden}
    data_tend_vencidos = {m: 0 for m in meses_orden}
    data_tend_fin = {m: 0 for m in meses_orden}

    df_eval_tend = df_filtrado.copy()

    for _, r in df_eval_tend.iterrows():
        st_val = str(r[col_estado]).lower()
        
        if any(term in st_val for term in ['finaliz', 'cerrad']):
            dt_s = parsear_fecha_estricta(r[col_fecha_cierre_aud]) if col_fecha_cierre_aud in r else pd.NaT
            if pd.notnull(dt_s) and dt_s.year == 2026 and dt_s.month in map_m_num:
                m_lbl = map_m_num[dt_s.month]
                data_tend_fin[m_lbl] += 1
        else:
            dt_i = parsear_fecha_estricta(r[col_fecha_cierre]) if col_fecha_cierre in r else pd.NaT
            if pd.notnull(dt_i) and dt_i.year == 2026 and dt_i.month in map_m_num:
                m_lbl = map_m_num[dt_i.month]
                if 'vencid' in st_val:
                    data_tend_vencidos[m_lbl] += 1
                else:
                    data_tend_abiertos[m_lbl] += 1

    fig_tendencia = go.Figure()
    fig_tendencia.add_trace(go.Scatter(
        x=meses_orden, 
        y=[data_tend_abiertos[m] for m in meses_orden],
        mode='lines+markers',
        name='Abiertos',
        line=dict(color='#F39C12', width=3, shape='spline'),
        marker=dict(size=6)
    ))
    fig_tendencia.add_trace(go.Scatter(
        x=meses_orden, 
        y=[data_tend_vencidos[m] for m in meses_orden],
        mode='lines+markers',
        name='Vencidos',
        line=dict(color='#FF5E5E', width=3, shape='spline'),
        marker=dict(size=6)
    ))
    fig_tendencia.add_trace(go.Scatter(
        x=meses_orden, 
        y=[data_tend_fin[m] for m in meses_orden],
        mode='lines+markers',
        name='Finalizados/Cerrados',
        line=dict(color='#2ECC71', width=3, shape='spline'),
        marker=dict(size=6)
    ))

    fig_tendencia.update_layout(
        template='plotly_dark',
        title=dict(text="📈 Tendencia Mensual de Planes (Vigencia 2026)", font=dict(size=14, color="white")),
        height=345,
        margin=dict(l=20, r=20, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    )

    df_pend_ai = df_activos.copy()
    if not df_pend_ai.empty and col_responsable in df_pend_ai.columns:
        df_pend_ai['Resp_Clean'] = df_pend_ai[col_responsable].astype(str).apply(extraer_sub_areas_individuales)
        df_exploded_ai = df_pend_ai.explode('Resp_Clean')
        df_exploded_ai = df_exploded_ai[~df_exploded_ai['Resp_Clean'].isin(["", "NAN", "NONE", "NONE."])]

        if not df_exploded_ai.empty:
            df_exploded_ai['Estado_Cat'] = df_exploded_ai[col_estado].astype(str).apply(
                lambda x: 'Vencidos' if 'vencid' in x.lower() else 'Abiertos'
            )

            df_top5_grp = df_exploded_ai.groupby(['Resp_Clean', 'Estado_Cat']).size().reset_index(name='Cantidad')
            top_resp_names = df_exploded_ai.groupby('Resp_Clean').size().nlargest(5).index.tolist()
            df_top5_final = df_top5_grp[df_top5_grp['Resp_Clean'].isin(top_resp_names)].copy()

            fig_top5 = px.bar(
                df_top5_final,
                y='Resp_Clean',
                x='Cantidad',
                color='Estado_Cat',
                orientation='h',
                title="🔥 Top 5 Responsables con Pendientes por Estado",
                color_discrete_map={'Abiertos': '#F39C12', 'Vencidos': '#FF5252'},
                text='Cantidad'
            )
            fig_top5.update_traces(textposition='inside', insidetextanchor='middle')
            fig_top5.update_layout(
                template='plotly_dark',
                height=320,
                margin=dict(l=20, r=20, t=30, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(type='category', autorange='reversed', title=None),
                xaxis=dict(showgrid=False, visible=False),
                legend_title_text="Estado",
                legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center")
            )
        else:
            fig_top5 = None
    else:
        fig_top5 = None

    df_perf = df_filtrado.copy()
    df_perf["Estado_Normalizado"] = df_perf[col_estado].fillna("").astype(str).str.strip().apply(lambda x: "Abierta" if "abiert" in x.lower() else ("Vencida" if "vencid" in x.lower() else ("Sin plan de acción" if "sin" in x.lower() else x))) if col_estado in df_perf.columns else ""

    fig_area_horiz, total_acciones_area = None, 0
    if col_responsable in df_perf.columns:
        df_pend = df_perf[~df_perf["Estado_Normalizado"].str.contains("Finaliz|Cerrad", case=False, na=False)].copy()
        if not df_pend.empty:
            df_pend[col_responsable] = df_pend[col_responsable].astype(str).apply(extraer_sub_areas_individuales)
            df_pend_exploded = df_pend.explode(col_responsable)
            df_pend_exploded = df_pend_exploded[~df_pend_exploded[col_responsable].isin(["", "nan", "None", "None."])]

            total_acciones_area = len(df_pend_exploded)
            df_area_grouped = df_pend_exploded.groupby([col_responsable, "Estado_Normalizado"]).size().reset_index(name="Cantidad")
            df_totales_area = df_area_grouped.groupby(col_responsable)["Cantidad"].sum().reset_index(name="Total_Pendientes").sort_values(by="Total_Pendientes", ascending=False)
            df_area_grouped[col_responsable] = pd.Categorical(df_area_grouped[col_responsable], categories=df_totales_area[col_responsable], ordered=True)
            df_area_grouped["Texto_Etiqueta"] = df_area_grouped["Cantidad"].apply(lambda x: f"<b>{x}</b>" if x > 1 else "")

            fig_area_horiz = px.bar(df_area_grouped, y=col_responsable, x="Cantidad", color="Estado_Normalizado", text="Texto_Etiqueta", orientation="h", barmode="stack", color_discrete_map={"Abierta": "#58C57A", "Vencida": "#FF5252", "Sin plan de acción": "#F8A583"})
            fig_area_horiz.update_traces(textposition="inside", insidetextanchor="middle", textfont=dict(size=12, color="white", family="Arial Black"), cliponaxis=False)

            for _, row in df_totales_area.iterrows():
                fig_area_horiz.add_annotation(y=row[col_responsable], x=row["Total_Pendientes"], text=f" <b>{row['Total_Pendientes']}</b>", showarrow=False, xanchor="left", yanchor="middle", font=dict(size=13, color="var(--text-color)"))
            fig_area_horiz.update_layout(height=max(480, len(df_totales_area) * 44), coloraxis_showscale=False, yaxis=dict(type="category", autorange="reversed", title=None, automargin=True), xaxis=dict(showticklabels=False, title=None, visible=False, range=[0, (df_totales_area["Total_Pendientes"].max() if not df_totales_area.empty else 10) * 1.25]), legend_title_text="Estado", margin=dict(l=280, r=60, t=60, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    fig_aud_horiz, total_acciones_aud = None, 0
    if col_auditoria in df_perf.columns:
        df_aud_pend_raw = df_perf[~df_perf["Estado_Normalizado"].str.contains("Finaliz|Cerrad", case=False, na=False)]
        if not df_aud_pend_raw.empty:
            total_acciones_aud = len(df_aud_pend_raw)
            df_aud_grouped = df_aud_pend_raw.groupby([col_auditoria, "Estado_Normalizado"]).size().reset_index(name="Cantidad")
            df_totales_aud = df_aud_grouped.groupby(col_auditoria)["Cantidad"].sum().reset_index(name="Total_Pendientes").sort_values(by="Total_Pendientes", ascending=False)
            df_aud_grouped[col_auditoria] = pd.Categorical(df_aud_grouped[col_auditoria], categories=df_totales_aud[col_auditoria], ordered=True)
            df_aud_grouped["Texto_Etiqueta"] = df_aud_grouped["Cantidad"].apply(lambda x: f"<b>{x}</b>" if x > 1 else "")

            fig_aud_horiz = px.bar(df_aud_grouped, y=col_auditoria, x="Cantidad", color="Estado_Normalizado", text="Texto_Etiqueta", orientation="h", barmode="stack", color_discrete_map={"Abierta": "#58C57A", "Vencida": "#FF5252", "Sin plan de acción": "#F8A583"})
            fig_aud_horiz.update_traces(textposition="inside", insidetextanchor="middle", textfont=dict(size=12, color="white", family="Arial Black"), cliponaxis=False)

            for _, row in df_totales_aud.iterrows():
                fig_aud_horiz.add_annotation(y=row[col_auditoria], x=row["Total_Pendientes"], text=f" <b>{row['Total_Pendientes']}</b>", showarrow=False, xanchor="left", yanchor="middle", font=dict(size=13, color="var(--text-color)"))
            fig_aud_horiz.update_layout(height=max(450, len(df_totales_aud) * 44), coloraxis_showscale=False, yaxis=dict(type="category", autorange="reversed", title=None, automargin=True, tickfont=dict(color="var(--text-color)")), xaxis=dict(showticklabels=False, title=None, visible=False, range=[0, df_totales_aud["Total_Pendientes"].max() * 1.25 if not df_totales_aud.empty else 10]), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    dict_pestanias = {
        "Tablero": "📊 Tablero",
        "Programa Anual": "🗓️ Programa Anual",
        "Métricas": "📈 Métricas",
        "Indicadores de Gestión": "📌 Indicadores de Gestión",
        "Histórico": "📊 Histórico",
        "Alertas y Edición": "🚨 Alertas y Edición",
        "Oficios": "📩 Oficios",
        "Informes": "📑 Informes"
    }

    pestañas_permitidas = [p for p in TODAS_LAS_PESTANIAS if p in st.session_state.get("permisos_usuario", [])]

    if not pestañas_permitidas:
        st.warning("⚠️ No tienes permisos asignados para ver ninguna sección. Contacta al administrador.")
        st.stop()

    titulos_tabs = [dict_pestanias[p] for p in pestañas_permitidas]
    tabs_objetos = st.tabs(titulos_tabs)

    subp_usuario = st.session_state.get("permisos_subpestañas", [])

    for nombre_tab_real, tab_obj in zip(pestañas_permitidas, tabs_objetos):
        with tab_obj:
            if nombre_tab_real == "Tablero":
                col_izq, col_der = st.columns([0.72, 1.6])

                with col_izq:
                    st.markdown('<div class="block-header">Total Hallazgos Pendientes</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="card-box" style="background-color:#4B92DB; font-size:1.3rem; height:34px; line-height:26px;">{total_hallazgos_unicos_pendientes}</div>', unsafe_allow_html=True)

                    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
                    r1, r2, r3 = st.columns(3)
                    with r1:
                        st.markdown('<div class="block-header" style="font-size:0.72rem;">Riesgo Alto</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="card-box" style="background-color:#FFB000; font-size:1rem;">{r_alto}</div>', unsafe_allow_html=True)
                    with r2:
                        st.markdown('<div class="block-header" style="font-size:0.72rem;">Riesgo Medio</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="card-box" style="background-color:#FFFF00; font-size:1rem;">{r_medio}</div>', unsafe_allow_html=True)
                    with r3:
                        st.markdown('<div class="block-header" style="font-size:0.72rem;">Riesgo Bajo</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="card-box" style="background-color:#00B050; font-size:1rem;">{r_bajo}</div>', unsafe_allow_html=True)

                    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
                    st.markdown('<div class="block-header" style="font-size:0.78rem;">Planes de Acción Pendientes</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="card-box" style="background-color:#00B050; height:36px; line-height:26px; font-size:1.4rem; margin-bottom:8px;">{total_planes_pendientes}</div>', unsafe_allow_html=True)

                    st.markdown('<div class="block-header" style="font-size:0.78rem;">Detalle de Estados Pendientes</div>', unsafe_allow_html=True)
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        st.markdown('<div class="block-header" style="font-size:0.7rem; text-transform:none;">Abiertos</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="card-box" style="background-color:#58C57A; font-size:1.05rem; padding:4px;">{abiertos}</div>', unsafe_allow_html=True)
                    with e2:
                        st.markdown('<div class="block-header" style="font-size:0.7rem; text-transform:none;">Vencidos</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="card-box" style="background-color:#FF5252; color:#FFFFFF; font-size:1.05rem; padding:4px;">{vencidos}</div>', unsafe_allow_html=True)
                    with e3:
                        st.markdown('<div class="block-header" style="font-size:0.7rem; text-transform:none;">Sin definir</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="card-box" style="background-color:#F8A583; font-size:1.05rem; padding:4px;">{sin_plan}</div>', unsafe_allow_html=True)

                    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

                    col_m_strat1, col_m_strat2 = st.columns(2)
                    with col_m_strat1:
                        st.markdown('<div class="block-header" style="font-size:0.7rem; text-transform:none;">🎯 % Cumplimiento</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="card-box" style="background-color:#1F4E78; color:#FFFFFF; font-size:0.95rem; padding:4px;">{pct_cumplimiento_ai}%</div>', unsafe_allow_html=True)
                        st.caption(f"({fin_ai_cnt} cerrados de {total_hist_ai} totales)")
                    with col_m_strat2:
                        st.markdown('<div class="block-header" style="font-size:0.7rem; text-transform:none;">⏱️ Prom. Días Mora</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="card-box" style="background-color:#C0392B; color:#FFFFFF; font-size:0.95rem; padding:4px;">{prom_mora_ai_val} días</div>', unsafe_allow_html=True)
                        st.caption(f"({len(df_raw_venc_ai)} vencidos)")

                    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

                    st.markdown('<div class="block-header">Acciones próximas a vencer</div>', unsafe_allow_html=True)

                    def obtener_valor_alerta(col_name):
                        if col_name and col_name in df_filtrado.columns:
                            s = df_filtrado[col_name].dropna().astype(str).str.strip()
                            validos = s[~s.str.lower().isin(["nan", "none", "", "0", "0.0", "false"])]
                            cant = len(validos)
                            return str(cant) if cant > 0 else "—"
                        return "—"

                    val_5 = obtener_valor_alerta(col_a5)
                    val_10 = obtener_valor_alerta(col_a10)
                    val_20 = obtener_valor_alerta(col_a20)
                    val_30 = obtener_valor_alerta(col_a30)

                    st.markdown(f'<div class="alert-card-horiz"><span>5 días 🔴</span><div class="alert-val-box">{val_5}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="alert-card-horiz"><span>10 días 🟡</span><div class="alert-val-box">{val_10}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="alert-card-horiz"><span>20 días 🟢</span><div class="alert-val-box">{val_20}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="alert-card-horiz"><span>30 días 🔵</span><div class="alert-val-box">{val_30}</div></div>', unsafe_allow_html=True)

                with col_der:
                    st.plotly_chart(fig_tendencia, use_container_width=True, key="fig_tendencia_tablero", config={'displayModeBar': False})
                    
                    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                    
                    if fig_top5 is not None:
                        st.plotly_chart(fig_top5, use_container_width=True, key="fig_top5_tablero", config={'displayModeBar': False})
                    else:
                        st.info("ℹ️ No hay planes de acción pendientes registrados para generar el Top 5 Responsables.")

                st.markdown("---")

                col_sub, col_search_box, col_filtro_rapido = st.columns([1.8, 1.3, 1])
                with col_sub:
                    st.subheader("📋 Detalle General de Compromisos Pendientes")
                
                with col_search_box:
                    busqueda_texto = st.text_input("🔍 Buscar texto en la tabla:", placeholder="Escribe para filtrar...", key="search_tabla_general").strip().lower()

                with col_filtro_rapido:
                    opciones_rapidas = ["(Mostrar Todos)", "Riesgo: Alto", "Riesgo: Medio", "Riesgo: Bajo", "Estado: Abiertos", "Estado: Vencidos", "Estado: Sin definir"]
                    if col_a5: opciones_rapidas.append("Alerta: Próximos a 5 días")
                    if col_a10: opciones_rapidas.append("Alerta: Próximos a 10 días")
                    if col_a20: opciones_rapidas.append("Alerta: Próximos a 20 días")
                    if col_a30: opciones_rapidas.append("Alerta: Próximos a 30 días")

                    filtro_elegido = st.selectbox("⚡ Filtrar por categoría:", options=opciones_rapidas, index=0)

                df_tabla = df_activos.copy()
                if filtro_elegido != "(Mostrar Todos)":
                    if "Riesgo: Alto" in filtro_elegido and col_riesgo:
                        df_tabla = df_tabla[df_tabla[col_riesgo].astype(str).str.contains("Alto", case=False, na=False)]
                    elif "Riesgo: Medio" in filtro_elegido and col_riesgo:
                        df_tabla = df_tabla[df_tabla[col_riesgo].astype(str).str.contains("Medio", case=False, na=False)]
                    elif "Riesgo: Bajo" in filtro_elegido and col_riesgo:
                        df_tabla = df_tabla[df_tabla[col_riesgo].astype(str).str.contains("Bajo", case=False, na=False)]
                    elif "Estado: Abiertos" in filtro_elegido and col_estado:
                        df_tabla = df_tabla[df_tabla[col_estado].astype(str).str.contains("Abiert", case=False, na=False)]
                    elif "Estado: Vencidos" in filtro_elegido and col_estado:
                        df_tabla = df_tabla[df_tabla[col_estado].astype(str).str.contains("Vencid", case=False, na=False)]
                    elif "Estado: Sin definir" in filtro_elegido and col_estado:
                        df_tabla = df_tabla[df_tabla[col_estado].astype(str).str.contains("Sin", case=False, na=False)]
                    elif "Alerta: Próximos a 5 días" in filtro_elegido and col_a5:
                        s_val = df_tabla[col_a5].fillna("").astype(str).str.strip().str.lower()
                        df_tabla = df_tabla[~s_val.isin(["nan", "none", "", "0", "0.0", "false"])]
                    elif "Alerta: Próximos a 10 días" in filtro_elegido and col_a10:
                        s_val = df_tabla[col_a10].fillna("").astype(str).str.strip().str.lower()
                        df_tabla = df_tabla[~s_val.isin(["nan", "none", "", "0", "0.0", "false"])]
                    elif "Alerta: Próximos a 20 días" in filtro_elegido and col_a20:
                        s_val = df_tabla[col_a20].fillna("").astype(str).str.strip().str.lower()
                        df_tabla = df_tabla[~s_val.isin(["nan", "none", "", "0", "0.0", "false"])]
                    elif "Alerta: Próximos a 30 días" in filtro_elegido and col_a30:
                        s_val = df_tabla[col_a30].fillna("").astype(str).str.strip().str.lower()
                        df_tabla = df_tabla[~s_val.isin(["nan", "none", "", "0", "0.0", "false"])]

                df_tabla_vista = filtrar_solo_columnas_amarillas_ai(df_tabla)

                if busqueda_texto:
                    mask_texto = df_tabla_vista.apply(
                        lambda row: row.astype(str).str.lower().str.contains(busqueda_texto, case=False, na=False).any(),
                        axis=1
                    )
                    df_tabla_vista = df_tabla_vista[mask_texto]

                df_tabla_vista.index = range(1, len(df_tabla_vista) + 1)

                col_config_dict = {}
                col_ev_vista = "Enlace para cargar evidencias" if "Enlace para cargar evidencias" in df_tabla_vista.columns else buscar_columna_por_patron(df_tabla_vista, ["enlace para cargar evidencias", "cargar evidencias"])
                
                if col_ev_vista and col_ev_vista in df_tabla_vista.columns:
                    def normalizar_url(val):
                        val_str = str(val).strip()
                        if val_str and val_str.lower() not in ["nan", "none", ""] and not val_str.startswith("http"):
                            return f"https://{val_str}"
                        return val_str
                    df_tabla_vista[col_ev_vista] = df_tabla_vista[col_ev_vista].apply(normalizar_url)
                    col_config_dict[col_ev_vista] = st.column_config.LinkColumn(
                        col_ev_vista,
                        help="Haz clic para abrir o cargar la evidencia en Google Drive",
                        display_text="📂 Cargar Evidencia"
                    )

                st.dataframe(df_tabla_vista, use_container_width=True, column_config=col_config_dict, hide_index=False)

                st.download_button(
                    label="📥 Descargar Excel (.xlsx)",
                    data=generar_excel_formateado_ai(df_tabla),
                    file_name=f"Detalle_Compromisos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=False,
                )

            elif nombre_tab_real == "Programa Anual":
                st.header("🗓️ Programa Anual de Auditoría (PAA)")
                st.markdown("Relación de auditorías específicas y su estado de ejecución agrupadas por vigencia.")

                if not df_paa_raw.empty:
                    df_paa_vista = df_paa_raw.copy()
                    
                    col_vig_paa = buscar_columna_por_patron(df_paa_vista, ["vigencia"]) or df_paa_vista.columns[0]
                    col_tipo_paa = buscar_columna_por_patron(df_paa_vista, ["tipologia", "tipo"]) or df_paa_vista.columns[1]
                    col_nom_paa = buscar_columna_por_patron(df_paa_vista, ["nombre", "auditoria"]) or df_paa_vista.columns[2]
                    col_est_paa = buscar_columna_por_patron(df_paa_vista, ["estado"]) or df_paa_vista.columns[3]

                    df_paa_vista[col_vig_paa] = df_paa_vista[col_vig_paa].ffill().astype(str).str.replace(".0", "", regex=False).str.strip()
                    if col_tipo_paa: df_paa_vista[col_tipo_paa] = df_paa_vista[col_tipo_paa].ffill()

                    vigencias_paa_unicas = sorted([v for v in df_paa_vista[col_vig_paa].dropna().unique() if str(v).lower() not in ["nan", "none", ""]])

                    if vigencias_paa_unicas:
                        subtabs_paa = st.tabs([f"📅 Vigencia {v}" if str(v).isdigit() else str(v) for v in vigencias_paa_unicas])

                        for i, vig in enumerate(vigencias_paa_unicas):
                            with subtabs_paa[i]:
                                df_sub_paa = df_paa_vista[df_paa_vista[col_vig_paa] == vig].copy().reset_index(drop=True)
                                df_sub_paa.index = range(1, len(df_sub_paa) + 1)
                                
                                tot_p = len(df_sub_paa)
                                fin_p = df_sub_paa[col_est_paa].astype(str).str.contains("Finaliz", case=False, na=False).sum() if col_est_paa else 0
                                asig_p = tot_p - fin_p
                                pct_p = round((fin_p / tot_p) * 100) if tot_p > 0 else 0

                                m_p1, m_p2, m_p3, m_p4 = st.columns(4)
                                m_p1.metric("📋 Total Auditorías Programadas", tot_p)
                                m_p2.metric("✅ Auditorías Finalizadas", fin_p)
                                m_p3.metric("⏳ Asignadas / En Proceso", asig_p)
                                m_p4.metric("📊 Tasa de Ejecución", f"{pct_p}%")

                                st.markdown("---")

                                def resaltar_finalizadas(row):
                                    val_est = str(row[col_est_paa]).lower() if col_est_paa and pd.notnull(row[col_est_paa]) else ""
                                    if "finaliz" in val_est:
                                        return ["background-color: #D9EAD3; color: #000000; font-weight: normal;"] * len(row)
                                    return [""] * len(row)

                                st.dataframe(df_sub_paa.style.apply(resaltar_finalizadas, axis=1), use_container_width=True, hide_index=False)

                        st.markdown("---")
                        st.download_button(
                            label="📥 Descargar Programa Anual de Auditoría (.xlsx)",
                            data=generar_excel_formateado_ai(df_paa_vista),
                            file_name=f"Programa_Anual_Auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="btn_download_paa",
                            use_container_width=False,
                        )
                else:
                    st.info("ℹ️ No se encontró información en la hoja 'Programa Anual de Auditoría' del archivo Excel.")

            elif nombre_tab_real == "Métricas":
                st.header("📈 Resumen de Estado y Desempeño")
                st.markdown("Vista general del avance de compromisos por área y auditoría.")

                comp_vencidos_pendientes = df_activos[col_estado].astype(str).str.contains("Vencid", case=False, na=False).sum() if col_estado else 0
                comp_criticos_pendientes = df_activos[col_riesgo].astype(str).str.contains("Alto", case=False, na=False).sum() if col_riesgo else 0

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Planes de Acción Pendientes", total_planes_pendientes)
                m2.metric("🔴 Compromisos Vencidos", comp_vencidos_pendientes)
                m3.metric("🟢 Compromisos Abiertos", abiertos)
                m4.metric("🔥 Hallazgos Riesgo Alto", comp_criticos_pendientes)

                st.markdown("---")
                st.subheader("👥 Distribución de Compromisos Pendientes por Área")
                st.markdown('<div class="small-note"><b>ℹ️ Nota sobre Responsabilidad Compartida:</b> Los hallazgos con responsabilidad compartida se contabilizan en los compromisos de cada Área individualmente.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="total-acciones-box">📌 Total acciones: {total_acciones_area}</div>', unsafe_allow_html=True)

                if fig_area_horiz is not None:
                    st.plotly_chart(fig_area_horiz, use_container_width=True, key="fig_area_horiz_key", config={'displayModeBar': False})

                st.markdown("---")
                st.subheader("🔬 Distribución de Compromisos Pendientes por Auditoría")
                st.markdown(f'<div class="total-acciones-box">📌 Total acciones: {total_acciones_aud}</div>', unsafe_allow_html=True)

                if fig_aud_horiz is not None:
                    st.plotly_chart(fig_aud_horiz, use_container_width=True, key="fig_aud_horiz_key", config={'displayModeBar': False})

            elif nombre_tab_real == "Indicadores de Gestión":
                st.header("📌 Indicadores de Gestión Auditoría Interna")
                st.markdown("Selecciona una sub-pestaña para comparar la **programación mensual** contra la **ejecución de planes finalizados**.")

                sub_names_ind = [
                    "Planes Programados (Vigencia 2026)",
                    "Planes Finalizados (Cierre Mensual + Histórico Completo)",
                    "Programa Anual de Auditoría (PAA)",
                    "Hallazgos Finalizados (% Hallazgo: Programados vs Finalizados 2026)"
                ]

                sub_titles_ind = []
                for sn in sub_names_ind:
                    ok = (sn in subp_usuario) or ("TODOS" in [x.upper() for x in subp_usuario])
                    sub_titles_ind.append(f"📅 {sn}" if ok else f"🔒 {sn}")

                subtab_ind1, subtab_ind2, subtab_ind_paa, subtab_ind3 = st.tabs(sub_titles_ind)

                with subtab_ind1:
                    if not (sub_names_ind[0] in subp_usuario or "TODOS" in [x.upper() for x in subp_usuario]):
                        st.error("🔒 **Acceso Restringido:** No tienes permisos para consultar esta sub-pestaña.")
                    else:
                        st.subheader("📅 Programación de Cierre por Mes (Vigencia 2026)")
                        st.markdown("Relación de planes de acción programados para la **Vigencia 2026**.")

                        conteo_programados_2026 = {
                            "ENE": 0, "FEB": 0, "MAR": 0, "ABR": 0, "MAYO": 0, "JUNIO": 0,
                            "JULIO": 0, "AGO": 0, "SEP": 0, "OCT": 0, "NOV": 0, "DIC": 0
                        }
                        
                        col_fecha_prog = col_fecha_cierre if col_fecha_cierre in df_raw.columns else col_fecha_cierre_aud

                        if col_fecha_prog and col_fecha_prog in df_raw.columns:
                            fechas_prog_dt = pd.to_datetime(df_raw[col_fecha_prog], errors="coerce", dayfirst=True)
                            for f in fechas_prog_dt.dropna():
                                if f.year == 2026:
                                    map_m = {1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"}
                                    if f.month in map_m:
                                        conteo_programados_2026[map_m[f.month]] += 1

                        col_ind_1, col_ind_2 = st.columns([0.28, 1])

                        with col_ind_1:
                            st.markdown('<div class="titulo-seccion-finaliz">📅 Programados 2026</div>', unsafe_allow_html=True)
                            st.markdown('<div class="month-container">', unsafe_allow_html=True)
                            for m_lbl, cant_prog in conteo_programados_2026.items():
                                st.markdown(f'<div class="month-row"><span>{m_lbl}</span><div class="month-box" style="background-color:#C2E0C6;">{cant_prog}</div></div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

                        with col_ind_2:
                            st.markdown('<div class="titulo-seccion-finaliz" style="margin-left: 12px !important;">📋 Detalle de Planes Programados 2026</div>', unsafe_allow_html=True)
                            
                            df_prog_2026 = df_raw.copy()
                            if col_fecha_prog and col_fecha_prog in df_prog_2026.columns:
                                fechas_prog_dt_col = pd.to_datetime(df_prog_2026[col_fecha_prog], errors="coerce", dayfirst=True)
                                df_prog_2026 = df_prog_2026[fechas_prog_dt_col.dt.year == 2026].copy()

                            if not df_prog_2026.empty:
                                df_prog_2026_vista = filtrar_solo_columnas_amarillas_ai(df_prog_2026)
                                df_prog_2026_vista.index = range(1, len(df_prog_2026_vista) + 1)
                                st.dataframe(df_prog_2026_vista, use_container_width=True, hide_index=False)

                                st.download_button(
                                    label="📥 Descargar Programados 2026 (.xlsx)",
                                    data=generar_excel_formateado_ai(df_prog_2026),
                                    file_name=f"Planes_Programados_2026_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="btn_download_prog_2026_ai_ind",
                                    use_container_width=False,
                                )
                            else:
                                st.info("ℹ️ No hay planes de acción programados para la vigencia 2026 con los filtros aplicados.")

                with subtab_ind2:
                    if not (sub_names_ind[1] in subp_usuario or "TODOS" in [x.upper() for x in subp_usuario]):
                        st.error("🔒 **Acceso Restringido:** No tienes permisos para consultar esta sub-pestaña.")
                    else:
                        st.subheader("🎉 Avance de Cierre y Planes Finalizados")
                        col_m1, col_m2 = st.columns([0.28, 1])

                        with col_m1:
                            st.markdown('<div class="titulo-seccion-finaliz">📅 Cierre Mensual 2026</div>', unsafe_allow_html=True)
                            st.markdown('<div class="month-container">', unsafe_allow_html=True)
                            for m, cant in conteo_meses.items():
                                st.markdown(f'<div class="month-row"><span>{m}</span><div class="month-box">{cant}</div></div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

                        with col_m2:
                            st.markdown('<div class="titulo-seccion-finaliz" style="margin-left: 12px !important;">📋 Tabla Completa de Planes Finalizados</div>', unsafe_allow_html=True)
                            df_finalizadas_tabla = df_filtrado[df_filtrado[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy() if col_estado else pd.DataFrame()

                            if not df_finalizadas_tabla.empty:
                                df_finalizadas_vista = filtrar_solo_columnas_amarillas_ai(df_finalizadas_tabla)
                                df_finalizadas_vista.index = range(1, len(df_finalizadas_vista) + 1)
                                st.dataframe(df_finalizadas_vista, use_container_width=True, hide_index=False)

                                st.download_button(
                                    label="📥 Descargar Solo Finalizadas (.xlsx)",
                                    data=generar_excel_formateado_ai(df_finalizadas_tabla),
                                    file_name=f"Acciones_Finalizadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="btn_download_finalizadas_ind_subtab",
                                    use_container_width=False,
                                )
                            else:
                                st.info("ℹ️ No hay acciones con estado 'Finalizado' para los filtros aplicados.")

                with subtab_ind_paa:
                    if not (sub_names_ind[2] in subp_usuario or "TODOS" in [x.upper() for x in subp_usuario]):
                        st.error("🔒 **Acceso Restringido:** No tienes permisos para consultar esta sub-pestaña.")
                    else:
                        st.subheader("🗓️ Programa Anual de Auditoría - Programadas vs Finalizadas (Vigencia 2026)")
                        st.markdown("Comparativa mes a mes del número de auditorías del PAA **Programadas** (`Mes Programada`) frente a las **Finalizadas** (`Mes finalizada`) para la Vigencia 2026.")

                        conteo_paa_prog_2026 = {m: 0 for m in meses_es}
                        conteo_paa_fin_2026 = {m: 0 for m in meses_es}

                        map_meses_paa = {
                            "enero": "ENE", "febrero": "FEB", "marzo": "MAR", "abril": "ABR",
                            "mayo": "MAYO", "junio": "JUNIO", "julio": "JULIO", "agosto": "AGO",
                            "septiembre": "SEP", "octubre": "OCT", "noviembre": "NOV", "diciembre": "DIC"
                        }

                        if not df_paa_raw.empty:
                            df_paa_calc = df_paa_raw.copy()
                            col_vig_paa_calc = buscar_columna_por_patron(df_paa_calc, ["vigencia"]) or df_paa_calc.columns[0]
                            col_nom_paa_calc = buscar_columna_por_patron(df_paa_calc, ["nombre", "auditoria"]) or df_paa_calc.columns[1]
                            col_est_paa_calc = buscar_columna_por_patron(df_paa_calc, ["estado"]) or df_paa_calc.columns[2]
                            col_mes_prog_paa = buscar_columna_por_patron(df_paa_calc, ["mes programada", "programada"]) or df_paa_calc.columns[3]
                            col_mes_fin_paa = buscar_columna_por_patron(df_paa_calc, ["mes finalizada", "finalizada"]) or df_paa_calc.columns[4]

                            df_paa_calc[col_vig_paa_calc] = df_paa_calc[col_vig_paa_calc].ffill().astype(str).str.replace(".0", "", regex=False).str.strip()
                            df_paa_2026 = df_paa_calc[df_paa_calc[col_vig_paa_calc] == "2026"].copy()

                            for _, r_paa in df_paa_2026.iterrows():
                                m_prog_str = str(r_paa[col_mes_prog_paa]).strip().lower() if col_mes_prog_paa in r_paa and pd.notnull(r_paa[col_mes_prog_paa]) else ""
                                if m_prog_str in map_meses_paa:
                                    conteo_paa_prog_2026[map_meses_paa[m_prog_str]] += 1

                                m_fin_str = str(r_paa[col_mes_fin_paa]).strip().lower() if col_mes_fin_paa in r_paa and pd.notnull(r_paa[col_mes_fin_paa]) else ""
                                if m_fin_str in map_meses_paa:
                                    conteo_paa_fin_2026[map_meses_paa[m_fin_str]] += 1

                        col_paa_1, col_paa_2 = st.columns([0.45, 1])

                        with col_paa_1:
                            st.markdown('<div class="titulo-seccion-finaliz">🎯 Auditorías PAA 2026</div>', unsafe_allow_html=True)
                            st.markdown('<div style="font-size:0.75rem; color:#A0AEC0; margin-bottom:8px;">🟩 Programadas | 🔳 Finalizadas</div>', unsafe_allow_html=True)
                            st.markdown('<div class="month-container">', unsafe_allow_html=True)
                            for m_lbl in meses_es:
                                c_p = conteo_paa_prog_2026[m_lbl]
                                c_f = conteo_paa_fin_2026[m_lbl]

                                st.markdown(
                                    f'''
                                    <div class="month-row">
                                        <span>{m_lbl}</span>
                                        <div style="display:flex; gap:6px;">
                                            <div class="month-box" style="background-color:#C2E0C6;" title="Auditorías Programadas PAA 2026">{c_p}</div>
                                            <div class="month-box-fin" style="background-color:#B4C6E7; color:#000;" title="Auditorías Finalizadas PAA 2026">{c_f}</div>
                                        </div>
                                    </div>
                                    ''',
                                    unsafe_allow_html=True
                                )
                            st.markdown('</div>', unsafe_allow_html=True)

                        with col_paa_2:
                            st.markdown('<div class="titulo-seccion-finaliz">📋 Detalle del Programa Anual de Auditoría 2026</div>', unsafe_allow_html=True)
                            if not df_paa_raw.empty:
                                df_paa_2026_vista = df_paa_2026.copy().reset_index(drop=True)
                                df_paa_2026_vista.index = range(1, len(df_paa_2026_vista) + 1)
                                st.dataframe(df_paa_2026_vista[[col_nom_paa_calc, col_est_paa_calc, col_mes_prog_paa, col_mes_fin_paa]], use_container_width=True, hide_index=False)

                                st.download_button(
                                    label="📥 Descargar PAA 2026 (.xlsx)",
                                    data=generar_excel_formateado_ai(df_paa_2026_vista),
                                    file_name=f"PAA_2026_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="btn_download_paa_subtab_ind",
                                    use_container_width=False,
                                )
                            else:
                                st.info("ℹ️ No hay registros en el Programa Anual de Auditoría para 2026.")

                with subtab_ind3:
                    if not (sub_names_ind[3] in subp_usuario or "TODOS" in [x.upper() for x in subp_usuario]):
                        st.error("🔒 **Acceso Restringido:** No tienes permisos para consultar esta sub-pestaña.")
                    else:
                        st.subheader("Programados vs Finalizados (% Hallazgo 2026)")
                        st.markdown("Comparativa mes a mes entre la suma del **`% Hallazgo` (Columna AB)** programado según la **Fecha de Cierre (Columna I)** y lo finalizado según la **Fecha de Cierre Auditoría (Columna S)**.")

                        conteo_pct_prog_2026 = {m: 0.0 for m in meses_es}
                        conteo_pct_fin_2026 = {m: 0.0 for m in meses_es}

                        col_cierre_prog_idx = df_raw.columns[8] if len(df_raw.columns) > 8 else col_fecha_cierre
                        col_estado_idx_pct = df_raw.columns[11] if len(df_raw.columns) > 11 else col_estado
                        col_fecha_fin_idx_pct = df_raw.columns[18] if len(df_raw.columns) > 18 else col_fecha_cierre_aud
                        col_pct_idx = df_raw.columns[27] if len(df_raw.columns) > 27 else df_raw.columns[-1]

                        map_m_pct = {1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"}

                        def limpiar_float_absoluto(v):
                            s = str(v).strip().replace(",", ".")
                            try:
                                return float(s)
                            except Exception:
                                return 0.0

                        fechas_prog_parsed_pct = df_raw[col_cierre_prog_idx].apply(parsear_fecha_estricta)
                        df_raw_prog_pct = df_raw.copy()
                        df_raw_prog_pct["pct_val"] = df_raw_prog_pct[col_pct_idx].apply(limpiar_float_absoluto)
                        df_raw_prog_pct["f_dt"] = fechas_prog_parsed_pct

                        for _, r_p in df_raw_prog_pct.iterrows():
                            dt_val = r_p["f_dt"]
                            if pd.notnull(dt_val) and dt_val.year == 2026 and dt_val.month in map_m_pct:
                                conteo_pct_prog_2026[map_m_pct[dt_val.month]] += float(r_p["pct_val"])

                        mask_fin_estricto_pct = df_raw[col_estado_idx_pct].astype(str).str.strip().str.lower().isin(["finalizada", "cerrada"])
                        df_fin_pct_raw = df_raw[mask_fin_estricto_pct].copy()

                        if not df_fin_pct_raw.empty:
                            df_fin_pct_raw["fecha_fin_dt_pct"] = df_fin_pct_raw[col_fecha_fin_idx_pct].apply(parsear_fecha_estricta)
                            df_fin_pct_raw["pct_num_val"] = df_fin_pct_raw[col_pct_idx].apply(limpiar_float_absoluto)

                            for _, r_pct in df_fin_pct_raw.iterrows():
                                dt_val = r_pct["fecha_fin_dt_pct"]
                                if pd.notnull(dt_val) and dt_val.year == 2026 and dt_val.month in map_m_pct:
                                    conteo_pct_fin_2026[map_m_pct[dt_val.month]] += float(r_pct["pct_num_val"])

                        col_h1, col_h2 = st.columns([0.45, 1])

                        with col_h1:
                            st.markdown('<div class="titulo-seccion-finaliz">🎯 Programados vs Finalizados</div>', unsafe_allow_html=True)
                            st.markdown('<div style="font-size:0.75rem; color:#A0AEC0; margin-bottom:8px;">🟩 Programados | 🔳 Finalizados</div>', unsafe_allow_html=True)
                            st.markdown('<div class="month-container">', unsafe_allow_html=True)
                            for m_lbl in meses_es:
                                sum_p = conteo_pct_prog_2026[m_lbl]
                                sum_f = conteo_pct_fin_2026[m_lbl]

                                p_str = f"{sum_p:g}".replace(".", ",") if float(sum_p).is_integer() else f"{sum_p:.2f}".replace(".", ",")
                                f_str = f"{sum_f:g}".replace(".", ",") if float(sum_f).is_integer() else f"{sum_f:.2f}".replace(".", ",")

                                st.markdown(
                                    f'''
                                    <div class="month-row">
                                        <span>{m_lbl}</span>
                                        <div style="display:flex; gap:6px;">
                                            <div class="month-box" style="background-color:#C2E0C6;" title="Programados Vigencia 2026 (Suma % Hallazgo)">{p_str}</div>
                                            <div class="month-box-fin" style="background-color:#B4C6E7; color:#000;" title="Finalizados Real Vigencia 2026 (Suma % Hallazgo)">{f_str}</div>
                                        </div>
                                    </div>
                                    ''',
                                    unsafe_allow_html=True
                                )
                            st.markdown('</div>', unsafe_allow_html=True)

                        with col_h2:
                            st.markdown('<div class="titulo-seccion-finaliz">📋 Registros de Hallazgos Finalizados 2026</div>', unsafe_allow_html=True)
                            if not df_fin_pct_raw.empty:
                                df_fin_pct_vista = filtrar_solo_columnas_amarillas_ai(df_fin_pct_raw)
                                df_fin_pct_vista.index = range(1, len(df_fin_pct_vista) + 1)
                                st.dataframe(df_fin_pct_vista, use_container_width=True, hide_index=False)

                                st.download_button(
                                    label="📥 Descargar Detalle Hallazgos Finalizados (.xlsx)",
                                    data=generar_excel_formateado_ai(df_fin_pct_raw),
                                    file_name=f"Hallazgos_Finalizados_Suma_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="btn_download_hallazgos_pct_subtab",
                                    use_container_width=False,
                                )
                            else:
                                st.info("ℹ️ No hay hallazgos finalizados registrados para la vigencia 2026.")

            elif nombre_tab_real == "Histórico":
                st.header("📊 Análisis Histórico e Interanual - Auditoría Interna")
                
                sub_names_hist = [
                    "Análisis por Planes de Acción",
                    "Análisis por Hallazgos Únicos"
                ]

                sub_titles_hist = []
                for sh in sub_names_hist:
                    ok = (sh in subp_usuario) or ("TODOS" in [x.upper() for x in subp_usuario])
                    sub_titles_hist.append(f"📌 {sh}" if ok else f"🔒 {sh}")

                subtab_hist1, subtab_hist2 = st.tabs(sub_titles_hist)

                with subtab