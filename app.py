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
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Tablero de Control y Gestión - Auditoría Interna",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# BASE DE DATOS LOCAL Y GESTIÓN DE COLUMNAS (SQLITE)
# ---------------------------------------------------------
DB_PATH = "usuarios_app.db"

TODAS_LAS_PESTANIAS = [
    "Tablero", 
    "Programa Anual", 
    "Métricas", 
    "Histórico", 
    "Alertas y Edición", 
    "Oficios", 
    "Finalizadas", 
    "Informes"
]

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_password(password, hashed):
    return hmac.compare_digest(hash_password(password), hashed)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT,
            autorizado INTEGER DEFAULT 1,
            token_recuperacion TEXT
        )
    ''')
    conn.commit()

    # Agregar la columna perm_pestañas si no existe en la BD existente
    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN perm_pestañas TEXT DEFAULT 'TODOS'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # La columna ya existía

    # Crear admin solo si no existe
    pw_hash = hash_password("admin123")
    c.execute('''
        INSERT OR IGNORE INTO usuarios (usuario, email, password_hash, autorizado, perm_pestañas) 
        VALUES (?, ?, ?, 1, 'TODOS')
    ''', ("admin", "admin@empresa.com", pw_hash))
    conn.commit()
    conn.close()

init_db()

def obtener_usuarios_df():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT usuario, email, autorizado, perm_pestañas FROM usuarios", conn)
    conn.close()
    return df

def actualizar_permisos_usuario(usuario, lista_pestañas):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    perm_str = ",".join(lista_pestañas) if lista_pestañas else ""
    c.execute("UPDATE usuarios SET perm_pestañas = ? WHERE usuario = ?", (perm_str, usuario))
    conn.commit()
    conn.close()

def guardar_o_actualizar_usuario(usuario, email, password, permisos_list):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    pw_hash = hash_password(password)
    perm_str = ",".join(permisos_list) if permisos_list else "TODOS"
    
    c.execute('''
        INSERT INTO usuarios (usuario, email, password_hash, autorizado, perm_pestañas)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(usuario) DO UPDATE SET
            email=excluded.email,
            password_hash=excluded.password_hash,
            autorizado=1,
            perm_pestañas=excluded.perm_pestañas
    ''', (usuario, email, pw_hash, perm_str))
    conn.commit()
    conn.close()

def enviar_correo_token(email_destino, token):
    try:
        smtp_config = st.secrets.get("smtp", {})
        server_host = smtp_config.get("server", "smtp.gmail.com")
        port = int(smtp_config.get("port", 587))
        remitente = smtp_config.get("user", "")
        password_remitente = smtp_config.get("password", "")

        if not remitente or not password_remitente:
            st.warning(f"🔑 [Entorno de Pruebas] Código generado para {email_destino}: **{token}**")
            return True

        asunto = "Código de Recuperación de Contraseña - Tablero Auditoría"
        cuerpo = f"Hola,\n\nTu código de verificación para restablecer la contraseña es: {token}\n\nSi no solicitaste este cambio, ignora este mensaje."

        msg = MIMEText(cuerpo)
        msg['Subject'] = asunto
        msg['From'] = remitente
        msg['To'] = email_destino

        with smtplib.SMTP(server_host, port) as server:
            server.starttls()
            server.login(remitente, password_remitente)
            server.sendmail(remitente, [email_destino], msg.as_string())
        return True
    except Exception as e:
        st.error(f"Error al enviar correo: {e}")
        return False

# ---------------------------------------------------------
# SISTEMA DE LOGIN Y CONTROL DE ACCESO
# ---------------------------------------------------------
def validar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if "usuario_actual" not in st.session_state:
        st.session_state["usuario_actual"] = ""
    if "permisos_usuario" not in st.session_state:
        st.session_state["permisos_usuario"] = []

    if not st.session_state["autenticado"]:
        st.markdown("## 🔒 Acceso Restringido")
        st.caption("Ingresa tus credenciales para acceder al tablero de Auditoría Interna.")
        
        tab_login, tab_recovery = st.tabs(["🔑 Iniciar Sesión", "❓ Olvidé mi Contraseña"])
        
        with tab_login:
            c1, _ = st.columns([1.5, 2])
            with c1:
                usuario = st.text_input("Usuario", key="user_input_ai")
                password = st.text_input("Contraseña", type="password", key="pass_input_ai")
                
                if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("SELECT password_hash, autorizado, perm_pestañas FROM usuarios WHERE usuario = ?", (usuario.strip(),))
                    row = c.fetchone()
                    conn.close()

                    if row:
                        pw_hash, autorizado, perm_str = row
                        if autorizado == 0:
                            st.error("🚫 Tu usuario no está autorizado para acceder.")
                        elif verificar_password(password, pw_hash):
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = usuario.strip()
                            
                            perm_val = perm_str if perm_str else "TODOS"
                            if perm_val == "TODOS" or usuario.strip() == "admin":
                                st.session_state["permisos_usuario"] = TODAS_LAS_PESTANIAS
                            else:
                                st.session_state["permisos_usuario"] = [p.strip() for p in perm_val.split(",") if p.strip()]
                                
                            st.rerun()
                        else:
                            st.error("❌ Usuario o contraseña incorrectos.")
                    else:
                        st.error("❌ Usuario o contraseña incorrectos.")

        with tab_recovery:
            c2, _ = st.columns([1.5, 2])
            with c2:
                st.markdown("##### Restablecer Contraseña")
                paso = st.session_state.get("paso_recuperacion", 1)

                if paso == 1:
                    email_req = st.text_input("Ingresa tu correo electrónico registrado:")
                    if st.button("Enviar Código de Verificación", use_container_width=True):
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT usuario, autorizado FROM usuarios WHERE email = ?", (email_req.strip().lower(),))
                        row = c.fetchone()

                        if row:
                            user_found, aut = row
                            if aut == 0:
                                st.error("🚫 Este usuario no está autorizado.")
                            else:
                                token = "".join(random.choices(string.digits, k=6))
                                c.execute("UPDATE usuarios SET token_recuperacion = ? WHERE email = ?", (token, email_req.strip().lower()))
                                conn.commit()
                                
                                if enviar_correo_token(email_req.strip().lower(), token):
                                    st.session_state["email_recuperacion"] = email_req.strip().lower()
                                    st.session_state["paso_recuperacion"] = 2
                                    st.success("✅ Código generado. Revisa tu correo.")
                                    st.rerun()
                        else:
                            st.error("❌ El correo no se encuentra registrado en el sistema.")
                        conn.close()

                elif paso == 2:
                    st.info(f"Código enviado a: **{st.session_state.get('email_recuperacion')}**")
                    token_ingresado = st.text_input("Ingresa el código de 6 dígitos recibido:")
                    nueva_pw = st.text_input("Nueva Contraseña:", type="password")
                    nueva_pw_conf = st.text_input("Confirmar Nueva Contraseña:", type="password")

                    if st.button("Restablecer Contraseña", type="primary", use_container_width=True):
                        if nueva_pw != nueva_pw_conf:
                            st.error("⚠️ Las contraseñas no coinciden.")
                        elif len(nueva_pw) < 6:
                            st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
                        else:
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute("SELECT token_recuperacion FROM usuarios WHERE email = ?", (st.session_state.get("email_recuperacion"),))
                            row = c.fetchone()

                            if row and row[0] == token_ingresado.strip():
                                new_hash = hash_password(nueva_pw)
                                c.execute("UPDATE usuarios SET password_hash = ?, token_recuperacion = NULL WHERE email = ?", 
                                          (new_hash, st.session_state.get("email_recuperacion")))
                                conn.commit()
                                conn.close()

                                st.success("🎉 ¡Contraseña actualizada con éxito! Ya puedes iniciar sesión.")
                                st.session_state["paso_recuperacion"] = 1
                                st.session_state["email_recuperacion"] = None
                            else:
                                st.error("❌ El código de verificación es incorrecto.")
                                conn.close()

                    if st.button("Volver a empezar"):
                        st.session_state["paso_recuperacion"] = 1
                        st.rerun()
        return False
    return True

if not validar_login():
    st.stop()

# ---------------------------------------------------------
# ESTILOS CSS
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppDeployButton {display:none !important;}
        [data-testid="stHeader"] {display:none !important;}
        [data-testid="stToolbar"] {display:none !important;}
        [data-testid="stDecoration"] {display:none !important;}
        [data-testid="stStatusWidget"] {display:none !important;}
        
        [data-testid="stSidebarCollapsedControl"],
        button[data-testid="stBaseButton-headerNoPadding"],
        button[aria-label="Close sidebar"],
        button[aria-label="Open sidebar"],
        button[aria-label="Collapse sidebar"],
        button[aria-label="Expand sidebar"] {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }

        [data-testid="stSidebar"] {
            min-width: 320px !important;
            max-width: 320px !important;
            display: block !important;
            visibility: visible !important;
            transform: none !important;
        }

        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }

        .titulo-tablero {
            font-size: 1.35rem !important;
            font-weight: 700 !important;
            color: var(--text-color);
            margin: 0 0 15px 0 !important;
            padding: 0 !important;
            line-height: 1.3 !important;
            display: block !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="titulo-tablero">📊 Tablero de Control y Gestión - Auditoría Interna</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# CARGA DE EXCEL PORTABLE
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

EXCEL_PATH = buscar_excel_inteligente()

def cargar_datos():
    if not os.path.exists(EXCEL_PATH):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        xls = pd.ExcelFile(EXCEL_PATH)
        sheet_b = "Base de datos" if "Base de datos" in xls.sheet_names else xls.sheet_names[0]
        df_base = pd.read_excel(xls, sheet_name=sheet_b)
        df_base.columns = [str(c).strip() for c in df_base.columns]
        return df_base, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_raw, _, _, _ = cargar_datos()

# ---------------------------------------------------------
# BARRA LATERAL (GESTIÓN DE PERMISOS + RESPALDO)
# ---------------------------------------------------------
st.sidebar.title("🔍 Filtros del Tablero")
st.sidebar.markdown(f"👤 **Usuario activo:** `{st.session_state.get('usuario_actual')}`")

if st.session_state.get("usuario_actual") == "admin":
    with st.sidebar.expander("👤 Gestión de Usuarios y Permisos (Admin)"):
        st.caption("1. Crear / Autorizar Usuario")
        new_u = st.text_input("Usuario", key="new_u_adm")
        new_e = st.text_input("Correo Electrónico", key="new_e_adm")
        new_p = st.text_input("Contraseña Inicial", type="password", key="new_p_adm")
        
        st.markdown("**Permisos de Acceso:**")
        u_permisos = []
        for pestania in TODAS_LAS_PESTANIAS:
            if st.checkbox(f"Ver {pestania}", value=True, key=f"chk_add_{pestania}"):
                u_permisos.append(pestania)

        if st.button("Guardar Usuario"):
            if new_u and new_e and new_p:
                guardar_o_actualizar_usuario(new_u.strip(), new_e.strip().lower(), new_p, u_permisos)
                st.success(f"Usuario {new_u} actualizado.")
            else:
                st.warning("Completa todos los campos.")
                
        st.markdown("---")
        st.caption("2. Modificar Permisos Existentes")
        df_users = obtener_usuarios_df()
        user_sel = st.selectbox("Seleccionar usuario:", df_users['usuario'].tolist(), key="sel_mod_user")
        
        if user_sel:
            row_u = df_users[df_users['usuario'] == user_sel].iloc[0]
            p_actuales = row_u['perm_pestañas'].split(",") if row_u['perm_pestañas'] != "TODOS" else TODAS_LAS_PESTANIAS
            
            nuevos_perms = []
            for p in TODAS_LAS_PESTANIAS:
                chk = st.checkbox(f"Acceso a {p}", value=(p in p_actuales), key=f"edit_perm_{user_sel}_{p}")
                if chk:
                    nuevos_perms.append(p)
                    
            if st.button(f"Actualizar Permisos de {user_sel}"):
                actualizar_permisos_usuario(user_sel, nuevos_perms)
                st.success("Permisos guardados.")
                st.rerun()

        st.markdown("---")
        st.caption("3. 📦 Respaldo de Usuarios")
        
        # Descarga CSV
        csv_bytes = df_users.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Descargar Respaldo (.CSV)",
            data=csv_bytes,
            file_name=f"respaldo_usuarios_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Descarga Excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df_users.to_excel(writer, index=False, sheet_name='Usuarios')
        st.download_button(
            label="📊 Descargar Respaldo (.XLSX)",
            data=buf.getvalue(),
            file_name=f"respaldo_usuarios_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["permisos_usuario"] = []
    st.rerun()

# ---------------------------------------------------------
# RENDERIZADO DE PESTAÑAS DINÁMICAS POR USUARIO
# ---------------------------------------------------------
pestañas_permitidas = [p for p in TODAS_LAS_PESTANIAS if p in st.session_state.get("permisos_usuario", [])]

if not pestañas_permitidas:
    st.warning("⚠️ No tienes permisos asignados para ver ninguna sección. Contacta al administrador.")
    st.stop()

tabs = st.tabs(pestañas_permitidas)

for nombre_tab, tab_obj in zip(pestañas_permitidas, tabs):
    with tab_obj:
        st.header(f"Sección: {nombre_tab}")
        st.info(f"Vista configurada correctamente para la pestaña **{nombre_tab}**.")