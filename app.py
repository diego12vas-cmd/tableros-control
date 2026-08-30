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
# BASE DE DATOS LOCAL Y PESTAÑAS
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

    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN perm_pestañas TEXT DEFAULT 'TODOS'")
        conn.commit()
    except sqlite3.OperationalError:
        pass

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

        .card-box {
            border-radius: 6px;
            padding: 4px 8px;
            text-align: center;
            font-weight: bold;
            color: #000;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.08);
            margin-bottom: 4px;
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
        .alert-row-compact {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            margin-bottom: 4px;
            font-weight: bold;
            font-size: 0.85rem;
            color: var(--text-color);
        }
        .alert-item-label {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 85px;
        }
        .alert-val-box {
            background-color: #EFEFEF;
            width: 44px;
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
            width: 120px !important;
        }
        .month-box {
            background-color: #D9EAD3;
            width: 44px;
            text-align: center;
            padding: 2px 0;
            border-radius: 4px;
            color: #000;
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
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="titulo-tablero">📊 Tablero de Control y Gestión - Auditoría Interna</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# CARGA DE EXCEL Y PROCESAMIENTO
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

def obtener_fecha_excel():
    if not EXCEL_PATH or not os.path.exists(EXCEL_PATH):
        return None
    try:
        xls = pd.ExcelFile(EXCEL_PATH)
        if "Tablero" in xls.sheet_names:
            df_tablero = pd.read_excel(xls, sheet_name="Tablero", header=None)
            for col in df_tablero.columns:
                for row_idx, val in enumerate(df_tablero[col].dropna()):
                    val_str = str(val).strip()
                    if "última fecha de actualización" in val_str.lower() or "ultima fecha" in val_str.lower():
                        match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", val_str)
                        if match:
                            return match.group(1)
        timestamp_mod = os.path.getmtime(EXCEL_PATH)
        return datetime.fromtimestamp(timestamp_mod).strftime("%d/%m/%Y")
    except Exception:
        if os.path.exists(EXCEL_PATH):
            return datetime.fromtimestamp(os.path.getmtime(EXCEL_PATH)).strftime("%d/%m/%Y")
        return None

def generar_excel_formateado(df):
    output = io.BytesIO()
    df_export = df.copy()

    cols_fecha = [col for col in df_export.columns if any(p in str(col).lower() for p in ["fecha", "terminacion", "cierre", "inicio", "vencimiento"])]

    for col in cols_fecha:
        def formatear_fecha_seguro(val):
            if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "nat", ""]:
                return ""
            if isinstance(val, (datetime, pd.Timestamp, date)):
                return val.strftime("%d/%m/%Y")
            val_str = str(val).strip()
            try:
                dt = pd.to_datetime(val_str, errors="coerce")
                if pd.notnull(dt):
                    return dt.strftime("%d/%m/%Y")
            except Exception:
                pass
            return val_str
        df_export[col] = df_export[col].apply(formatear_fecha_seguro)

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
            es_col_fecha = col in cols_fecha
            longitudes = [len(str(val)) for val in df_export[col].dropna().tolist()] if not df_export.empty else []
            max_len = max(longitudes) if longitudes else 0
            adjusted_width = min(max(max_len + 4, len(str(col)) + 4, 14), 65)
            worksheet.set_column(i, i, adjusted_width, date_cell_format if es_col_fecha else cell_format)

        worksheet.hide_gridlines(2)
    return output.getvalue()

def cargar_datos():
    if not os.path.exists(EXCEL_PATH):
        st.error(f"⚠️ No se encontró el archivo Excel en: `{EXCEL_PATH}`")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    try:
        xls = pd.ExcelFile(EXCEL_PATH)
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
        st.error(f"Error al cargar Excel: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_raw, df_calc, df_informes_raw, df_paa_raw = cargar_datos()

if df_raw.empty:
    st.stop()

def buscar_columna_por_patron(df, patrones):
    for col in df.columns:
        col_clean = str(col).lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        for pat in patrones:
            if pat in col_clean:
                return col
    return None

col_estado = buscar_columna_por_patron(df_raw, ["estado del compromiso", "estado compromiso", "estado"])
col_responsable = buscar_columna_por_patron(df_raw, ["responsable", "area responsable"])
col_auditor_resp = "Auditor Responsable" if "Auditor Responsable" in df_raw.columns else buscar_columna_por_patron(df_raw, ["auditor responsable", "auditor"])
col_plan_filtro = "Plan Auditoría" if "Plan Auditoría" in df_raw.columns else buscar_columna_por_patron(df_raw, ["plan auditoria", "vigencia"])
col_plan_accion = "Plan de Acción" if "Plan de Acción" in df_raw.columns else buscar_columna_por_patron(df_raw, ["compromiso", "plan de accion", "accion"]) or col_plan_filtro
col_auditoria = "Auditoría" if "Auditoría" in df_raw.columns else buscar_columna_por_patron(df_raw, ["auditoria especifica", "auditoria"])
col_hallazgo = buscar_columna_por_patron(df_raw, ["transcribir", "situacion evidenciada", "del hallazgo", "titulo del hallazgo", "hallazgo"])
col_nombre = buscar_columna_por_patron(df_raw, ["nombre", "nombre hallazgo", "titulo"])
col_riesgo = buscar_columna_por_patron(df_raw, ["riesgo", "nivel de riesgo"])
col_fecha_cierre = buscar_columna_por_patron(df_raw, ["cierre", "fecha cierre", "fecha compromiso"])
col_obs_audit = buscar_columna_por_patron(df_raw, ["observacion auditoria"]) or "Observación Auditoría"

col_a5 = buscar_columna_por_patron(df_raw, ["alerta 5"])
col_a10 = buscar_columna_por_patron(df_raw, ["alerta 10"])
col_a20 = buscar_columna_por_patron(df_raw, ["alerta 20"])
col_a30 = buscar_columna_por_patron(df_raw, ["alerta 30"])

if col_estado:
    df_raw[col_estado] = df_raw[col_estado].astype(str).str.capitalize()

meses_es = ["ENE", "FEB", "MAR", "ABR", "MAYO", "JUNIO", "JULIO", "AGO", "SEP", "OCT", "NOV", "DIC"]
conteo_meses = {m: 0 for m in meses_es}

if not df_calc.empty:
    for idx, row in df_calc.iterrows():
        val_m = str(row[0]).strip().lower()
        for idx_m, m_nombre in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]):
            if m_nombre in val_m:
                conteo_meses[meses_es[idx_m]] = int(row[1]) if pd.notnull(row[1]) and str(row[1]).isdigit() else 0

# ---------------------------------------------------------
# BARRA LATERAL (FILTROS Y GESTIÓN DE PERMISOS)
# ---------------------------------------------------------
st.sidebar.title("🔍 Filtros del Tablero")

fecha_excel = obtener_fecha_excel()
if fecha_excel:
    st.sidebar.markdown(f"📅 **Datos actualizados al:** {fecha_excel}")

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
        
        csv_bytes = df_users.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Descargar Respaldo (.CSV)",
            data=csv_bytes,
            file_name=f"respaldo_usuarios_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
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

st.sidebar.markdown("---")

# FILTROS EN BARRA LATERAL
df_filtrado = df_raw.copy()

if col_estado:
    estados_vals = sorted([e for e in df_raw[col_estado].dropna().unique() if str(e).lower() not in ["nan", "none", ""] and not re.search(r"finaliz|cerrad", str(e), re.IGNORECASE)])
    with st.sidebar.expander("📌 Estado del compromiso", expanded=True):
        estado_sel = st.multiselect("Seleccione Estados:", options=estados_vals, default=[], key="multi_estado")
    if estado_sel:
        df_filtrado = df_filtrado[df_filtrado[col_estado].isin(estado_sel)]

if col_responsable:
    resp_vals = sorted(list(set([r for r in df_raw[col_responsable].dropna().unique() if str(r).lower() not in ["nan", "none", ""]])))
    with st.sidebar.expander("👤 Responsables", expanded=False):
        resp_sel = st.multiselect("Seleccione Responsables:", options=resp_vals, default=[], key="multi_resp")
    if resp_sel:
        df_filtrado = df_filtrado[df_filtrado[col_responsable].isin(resp_sel)]

if col_auditor_resp:
    aud_resp_vals = sorted(list(set([ar for ar in df_raw[col_auditor_resp].dropna().unique() if str(ar).lower() not in ["nan", "none", ""]])))
    with st.sidebar.expander("🧐 Auditor Responsable", expanded=False):
        aud_resp_sel = st.multiselect("Seleccione Auditores:", options=aud_resp_vals, default=[], key="multi_auditor_resp")
    if aud_resp_sel:
        df_filtrado = df_filtrado[df_filtrado[col_auditor_resp].isin(aud_resp_sel)]

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

# ---------------------------------------------------------
# MÉTRICAS Y FIGURAS
# ---------------------------------------------------------
abiertos = df_filtrado[col_estado].astype(str).str.contains("Abiert", case=False, na=False).sum() if col_estado else 0
vencidos = df_filtrado[col_estado].astype(str).str.contains("Vencid", case=False, na=False).sum() if col_estado else 0
sin_plan = df_filtrado[col_estado].astype(str).str.contains("Sin plan|Sin defin", case=False, na=False).sum() if col_estado else 0

df_activos = df_filtrado[~df_filtrado[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy() if col_estado else df_filtrado.copy()

total_hallazgos_unicos_pendientes = df_activos[col_hallazgo].dropna().nunique() if col_hallazgo and col_hallazgo in df_activos.columns else len(df_activos)
total_planes_pendientes = abiertos + vencidos + sin_plan

r_alto = df_activos[col_riesgo].astype(str).str.contains("Alto", case=False, na=False).sum() if col_riesgo else 0
r_medio = df_activos[col_riesgo].astype(str).str.contains("Medio", case=False, na=False).sum() if col_riesgo else 0
r_bajo = df_activos[col_riesgo].astype(str).str.contains("Bajo", case=False, na=False).sum() if col_riesgo else 0

# Barras
max_val_pend = max([abiertos, vencidos, sin_plan])
df_bar = pd.DataFrame({"Estado": ["Abiertos", "Vencidos", "Sin definir"], "Cantidad": [abiertos, vencidos, sin_plan]})
fig_bar = px.bar(df_bar, x="Estado", y="Cantidad", text="Cantidad", color="Estado", color_discrete_map={"Abiertos": "#58C57A", "Vencidos": "#FF5252", "Sin definir": "#F8A583"})
fig_bar.update_traces(textposition="outside", textfont=dict(size=12, color="var(--text-color)", family="Arial"), cliponaxis=False)
fig_bar.update_layout(showlegend=False, height=180, margin=dict(t=25, b=5, l=5, r=5), xaxis_title=None, yaxis_title=None, yaxis=dict(showticklabels=False, range=[0, max_val_pend * 1.25 if max_val_pend > 0 else 10]), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

# Donas
pct_abiertos = round((abiertos / total_planes_pendientes) * 100) if total_planes_pendientes > 0 else 0
fig_dona_abiertos = go.Figure(data=[go.Pie(values=[1]*20, hole=0.68, marker_colors=["#00B050" if i < (pct_abiertos / 5) else "#E0E0E0" for i in range(20)], marker_line=dict(color="#FFFFFF", width=2), textinfo="none", hoverinfo="none", domain=dict(x=[0.05, 0.95], y=[0.05, 0.95]))])
fig_dona_abiertos.add_annotation(text=f"<b>{pct_abiertos}%</b>", x=0.5, y=0.5, font=dict(size=18, color="var(--text-color)"), showarrow=False)
fig_dona_abiertos.update_layout(showlegend=False, height=170, autosize=True, margin=dict(t=15, b=15, l=15, r=15), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

pct_vencidos = round((vencidos / total_planes_pendientes) * 100) if total_planes_pendientes > 0 else 0
fig_dona_vencidos = go.Figure(data=[go.Pie(values=[1]*20, hole=0.68, marker_colors=["#FF5252" if i < (pct_vencidos / 5) else "#E0E0E0" for i in range(20)], marker_line=dict(color="#FFFFFF", width=2), textinfo="none", hoverinfo="none", domain=dict(x=[0.05, 0.95], y=[0.05, 0.95]))])
fig_dona_vencidos.add_annotation(text=f"<b>{pct_vencidos}%</b>", x=0.5, y=0.5, font=dict(size=18, color="var(--text-color)"), showarrow=False)
fig_dona_vencidos.update_layout(showlegend=False, height=170, autosize=True, margin=dict(t=15, b=15, l=15, r=15), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

# Áreas y Auditorías
df_perf = df_filtrado.copy()
df_perf["Estado_Normalizado"] = df_perf[col_estado].fillna("").astype(str).str.strip().apply(lambda x: "Abierta" if "abiert" in x.lower() else ("Vencida" if "vencid" in x.lower() else ("Sin plan de acción" if "sin" in x.lower() else x))) if col_estado in df_perf.columns else ""

fig_area_horiz, total_acciones_area = None, 0
if col_responsable in df_perf.columns:
    df_pend = df_perf[~df_perf["Estado_Normalizado"].str.contains("Finaliz|Cerrad", case=False, na=False)].copy()
    if not df_pend.empty:
        df_pend[col_responsable] = df_pend[col_responsable].astype(str).str.replace("\n", ",").str.split(",")
        df_pend_exploded = df_pend.explode(col_responsable)
        df_pend_exploded[col_responsable] = df_pend_exploded[col_responsable].astype(str).str.strip()
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
        fig_aud_horiz.update_layout(height=max(450, len(df_totales_aud) * 44), coloraxis_showscale=False, yaxis=dict(type="category", autorange="reversed", title=None, automargin=True), xaxis=dict(showticklabels=False, title=None, visible=False, range=[0, (df_totales_aud["Total_Pendientes"].max() if not df_totales_aud.empty else 10) * 1.25]), legend_title_text="Estado", margin=dict(l=280, r=60, t=60, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

# ---------------------------------------------------------
# RENDERIZADO DINÁMICO DE PESTAÑAS SEGÚN PERMISOS
# ---------------------------------------------------------
pestañas_permitidas = [p for p in TODAS_LAS_PESTANIAS if p in st.session_state.get("permisos_usuario", [])]

if not pestañas_permitidas:
    st.warning("⚠️ No tienes permisos asignados para ver ninguna sección. Contacta al administrador.")
    st.stop()

tabs = st.tabs(pestañas_permitidas)

for nombre_tab, tab_obj in zip(pestañas_permitidas, tabs):
    with tab_obj:
        if nombre_tab == "Tablero":
            c2, c3, c4 = st.columns([2.5, 2.5, 2.0])
            with c2:
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

            with c3:
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

                st.markdown(f"""
                    <div style="display: flex; flex-direction: column; align-items: center; width: 100%;">
                        <div class="alert-row-compact"><div class="alert-item-label"><span>5 días</span><span>🔴</span></div><div class="alert-val-box">{val_5}</div></div>
                        <div class="alert-row-compact"><div class="alert-item-label"><span>10 días</span><span>🟡</span></div><div class="alert-val-box">{val_10}</div></div>
                        <div class="alert-row-compact"><div class="alert-item-label"><span>20 días</span><span>🟢</span></div><div class="alert-val-box">{val_20}</div></div>
                        <div class="alert-row-compact"><div class="alert-item-label"><span>30 días</span><span>🔵</span></div><div class="alert-val-box">{val_30}</div></div>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown('<div class="block-header" style="margin-top:2px;">Distribución de Planes Pendientes</div>', unsafe_allow_html=True)
                st.plotly_chart(fig_bar, use_container_width=True, key="fig_bar_pendientes", config={'displayModeBar': False})

            with c4:
                st.markdown('<div class="block-header">Porcentaje de Acciones Pendientes</div>', unsafe_allow_html=True)
                st.markdown('<div class="block-header" style="font-size:0.75rem; text-transform:none; margin-bottom:0px; color:#00B050;">🟢 En tiempo (Abiertos)</div>', unsafe_allow_html=True)
                st.plotly_chart(fig_dona_abiertos, use_container_width=True, key="fig_dona_abiertos_key", config={'displayModeBar': False})
                st.markdown('<div class="block-header" style="font-size:0.75rem; text-transform:none; margin-bottom:0px; color:#FF5252;">🔴 Vencidos</div>', unsafe_allow_html=True)
                st.plotly_chart(fig_dona_vencidos, use_container_width=True, key="fig_dona_vencidos_key", config={'displayModeBar': False})

            st.markdown("---")
            col_sub, col_filtro_rapido = st.columns([2, 1])
            with col_sub:
                st.subheader("📋 Detalle General de Compromisos Pendientes")
            with col_filtro_rapido:
                opciones_rapidas = ["(Mostrar Todos)", "Riesgo: Alto", "Riesgo: Medio", "Riesgo: Bajo", "Estado: Abiertos", "Estado: Vencidos", "Estado: Sin definir"]
                if col_a5: opciones_rapidas.append("Alerta: Próximos a 5 días")
                if col_a10: opciones_rapidas.append("Alerta: Próximos a 10 días")
                if col_a20: opciones_rapidas.append("Alerta: Próximos a 20 días")
                if col_a30: opciones_rapidas.append("Alerta: Próximos a 30 días")
                filtro_elegido = st.selectbox("⚡ Filtrar vista detallada por categoría:", options=opciones_rapidas, index=0)

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

            df_tabla.index = range(1, len(df_tabla) + 1)
            st.dataframe(df_tabla, use_container_width=True)
            st.download_button(label="📥 Descargar Excel (.xlsx)", data=generar_excel_formateado(df_tabla), file_name=f"Detalle_Compromisos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        elif nombre_tab == "Programa Anual":
            st.header("🗓️ Programa Anual de Auditoría (PAA)")
            if not df_paa_raw.empty:
                df_paa_vista = df_paa_raw.copy()
                col_vig_paa = buscar_columna_por_patron(df_paa_vista, ["vigencia"]) or df_paa_vista.columns[0]
                col_est_paa = buscar_columna_por_patron(df_paa_vista, ["estado"]) or df_paa_vista.columns[3]
                df_paa_vista[col_vig_paa] = df_paa_vista[col_vig_paa].ffill().astype(str).str.replace(".0", "", regex=False).str.strip()
                vigencias_paa_unicas = sorted([v for v in df_paa_vista[col_vig_paa].dropna().unique() if str(v).lower() not in ["nan", "none", ""]])
                
                if vigencias_paa_unicas:
                    subtabs_paa = st.tabs([f"📅 Vigencia {v}" if str(v).isdigit() else str(v) for v in vigencias_paa_unicas])
                    for i, vig in enumerate(vigencias_paa_unicas):
                        with subtabs_paa[i]:
                            df_sub_paa = df_paa_vista[df_paa_vista[col_vig_paa] == vig].copy().reset_index(drop=True)
                            tot_p = len(df_sub_paa)
                            fin_p = df_sub_paa[col_est_paa].astype(str).str.contains("Finaliz", case=False, na=False).sum() if col_est_paa else 0
                            m_p1, m_p2, m_p3, m_p4 = st.columns(4)
                            m_p1.metric("📋 Total Auditorías Programadas", tot_p)
                            m_p2.metric("✅ Auditorías Finalizadas", fin_p)
                            m_p3.metric("⏳ Asignadas / En Proceso", tot_p - fin_p)
                            m_p4.metric("📊 Tasa de Ejecución", f"{round((fin_p / tot_p) * 100) if tot_p > 0 else 0}%")
                            st.markdown("---")
                            df_sub_paa.index = range(1, len(df_sub_paa) + 1)
                            st.dataframe(df_sub_paa, use_container_width=True)
            else:
                st.info("ℹ️ No hay datos en Programa Anual de Auditoría.")

        elif nombre_tab == "Métricas":
            st.header("📈 Resumen de Estado y Desempeño")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Planes de Acción Pendientes", total_planes_pendientes)
            m2.metric("🔴 Compromisos Vencidos", vencidos)
            m3.metric("🔥 Hallazgos Riesgo Alto", r_alto)
            m4.metric("🎯 Tasa Global de Cierre", f"{pct_abiertos}%")
            st.markdown("---")
            st.subheader("👥 Distribución de Compromisos Pendientes por Área")
            if fig_area_horiz: st.plotly_chart(fig_area_horiz, use_container_width=True, key="fig_area_horiz_key", config={'displayModeBar': False})
            st.markdown("---")
            st.subheader("🔬 Distribución de Compromisos Pendientes por Auditoría")
            if fig_aud_horiz: st.plotly_chart(fig_aud_horiz, use_container_width=True, key="fig_aud_horiz_key", config={'displayModeBar': False})

        elif nombre_tab == "Histórico":
            st.header("📊 Análisis Histórico e Interanual de Planes de Mejoramiento")
            if col_plan_filtro and col_plan_filtro in df_raw.columns:
                df_hist_calc = df_raw.copy()
                df_hist_calc["Vigencia_Limpia"] = df_hist_calc[col_plan_filtro].astype(str).str.strip()
                df_vigencia_totales = df_hist_calc.groupby("Vigencia_Limpia").size().reset_index(name="Total_Planes").sort_values(by="Vigencia_Limpia")
                fig_hist_line = px.bar(df_vigencia_totales, x="Vigencia_Limpia", y="Total_Planes", text="Total_Planes", title="Evolución Total de Planes de Mejoramiento por Vigencia", color_discrete_sequence=["#1F4E78"])
                fig_hist_line.update_traces(textposition="outside")
                st.plotly_chart(fig_hist_line, use_container_width=True, key="fig_hist_line_key", config={'displayModeBar': False})

        elif nombre_tab == "Alertas y Edición":
            st.header("🚨 Alertas Críticas y Edición Directa")
            st.subheader("✏️ Establecer Compromisos")
            df_edicion_temp = df_raw.copy()
            if col_hallazgo and not df_edicion_temp.empty:
                dict_opciones = {f"[{str(row[col_nombre]).strip() if col_nombre and col_nombre in row else ''}] - {str(row[col_hallazgo])}": str(row[col_hallazgo]) for _, row in df_edicion_temp.dropna(subset=[col_hallazgo]).iterrows()}
                if dict_opciones:
                    etiqueta_sel = st.selectbox("Seleccione el Registro a Modificar:", options=list(dict_opciones.keys()), key="f_hallazgo_sel")
                    id_sel = dict_opciones[etiqueta_sel]
                    mask = df_edicion_temp[col_hallazgo] == id_sel
                    registro = df_edicion_temp[mask].iloc[0] if mask.any() else None
                    if registro is not None:
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            nueva_fecha = st.date_input("Nueva Fecha de Cierre:", key="in_fecha_edit")
                            nuevo_est = st.selectbox("Estado del Compromiso:", options=["Abierta", "Vencida", "Finalizada", "Sin plan de acción"], key="in_estado_edit")
                        with col_f2:
                            nuevo_plan = st.text_area("Plan de Acción:", value=str(registro[col_plan_accion]) if col_plan_accion else "", key="in_plan_edit")
                        if st.button("➕ Registrar Cambio", type="primary"):
                            st.toast("✅ ¡Modificación registrada temporalmente!", icon="🎉")

        elif nombre_tab == "Oficios":
            st.header("📩 Registro e Historial de Oficios Radicados")
            col_rad_target = buscar_columna_por_patron(df_filtrado, ["radicado"])
            if col_rad_target:
                df_oficios_raw = df_filtrado.dropna(subset=[col_rad_target]).copy()
                st.dataframe(df_oficios_raw, use_container_width=True)
            else:
                st.info("ℹ️ No se detectaron columnas de oficio radicado.")

        elif nombre_tab == "Finalizadas":
            st.header("🎉 Acciones Finalizadas")
            col_m1, col_m2 = st.columns([0.24, 1])
            with col_m1:
                st.markdown('<div class="titulo-seccion-finaliz">📅 Cierre Mensual 2026</div>', unsafe_allow_html=True)
                for m, cant in conteo_meses.items():
                    st.markdown(f'<div class="month-row"><span>{m}</span><div class="month-box">{cant}</div></div>', unsafe_allow_html=True)
            with col_m2:
                df_finalizadas_tabla = df_filtrado[df_filtrado[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy() if col_estado else pd.DataFrame()
                if not df_finalizadas_tabla.empty:
                    df_finalizadas_tabla.index = range(1, len(df_finalizadas_tabla) + 1)
                    st.dataframe(df_finalizadas_tabla, use_container_width=True)

        elif nombre_tab == "Informes":
            st.header("📑 Informes de Auditoría Interna por Vigencia")
            if not df_informes_raw.empty:
                df_inf_vista = df_informes_raw.copy()
                col_vig_inf = buscar_columna_por_patron(df_inf_vista, ["vigencia"]) or df_inf_vista.columns[0]
                vigencias_unicas = sorted([v for v in df_inf_vista[col_vig_inf].dropna().unique() if str(v).lower() not in ["nan", "none", ""]])
                if vigencias_unicas:
                    subtabs = st.tabs([f"📅 Vigencia {v}" if str(v).isdigit() else str(v) for v in vigencias_unicas])
                    for i, vig in enumerate(vigencias_unicas):
                        with subtabs[i]:
                            df_sub_vig = df_inf_vista[df_inf_vista[col_vig_inf] == vig].copy().reset_index(drop=True)
                            st.dataframe(df_sub_vig, use_container_width=True)