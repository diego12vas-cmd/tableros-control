import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import io

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE BASE DE DATOS Y ROLES
# -----------------------------------------------------------------------------
DB_PATH = "usuarios_app.db"

# Lista de todas las pestañas disponibles en tu tablero
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
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Tabla de usuarios con columna perm_pestañas
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT,
            autorizado INTEGER DEFAULT 1,
            token_recuperacion TEXT,
            perm_pestañas TEXT DEFAULT 'TODOS'
        )
    ''')
    conn.commit()
    
    # Usuario admin por defecto
    pw_admin = hash_password("admin123")
    c.execute('''
        INSERT OR IGNORE INTO usuarios (usuario, email, password_hash, autorizado, perm_pestañas)
        VALUES ('admin', 'admin@empresa.com', ?, 1, 'TODOS')
    ''', (pw_admin,))
    
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES DE BASE DE DATOS
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# CONTROL DE SESIÓN Y AUTENTICACIÓN
# -----------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""
if "permisos_usuario" not in st.session_state:
    st.session_state.permisos_usuario = []

def autenticar_usuario(usuario, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    pw_hash = hash_password(password)
    c.execute("SELECT usuario, perm_pestañas FROM usuarios WHERE usuario = ? AND password_hash = ? AND autorizado = 1", (usuario, pw_hash))
    res = c.fetchone()
    conn.close()
    if res:
        st.session_state.logged_in = True
        st.session_state.usuario_actual = res[0]
        perm_str = res[1] or ""
        if perm_str == "TODOS" or res[0] == "admin":
            st.session_state.permisos_usuario = TODAS_LAS_PESTANIAS
        else:
            st.session_state.permisos_usuario = [p.strip() for p in perm_str.split(",") if p.strip()]
        return True
    return False

# -----------------------------------------------------------------------------
# PANTALLA DE LOGIN
# -----------------------------------------------------------------------------
if not st.session_state.logged_in:
    st.title("🔒 Acceso Restringido")
    st.caption("Ingresa tus credenciales para acceder al tablero de Auditoría Interna.")
    
    tab_login, tab_recovery = st.tabs(["🔑 Iniciar Sesión", "❓ Olvidé mi Contraseña"])
    
    with tab_login:
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            if autenticar_usuario(user_input, pass_input):
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
                
    with tab_recovery:
        email_rec = st.text_input("Correo Electrónico Registrado")
        if st.button("Enviar Código / Restablecer", use_container_width=True):
            st.info("Funcionalidad SMTP vinculada a Secrets.")
            
    st.stop()

# -----------------------------------------------------------------------------
# BARRA LATERAL (GESTIÓN DE ADMIN & FILTROS)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"**Usuario en sesión:** `{st.session_state.usuario_actual}`")
    
    # SECCIÓN ADMINISTRADOR (Solo visible para 'admin')
    if st.session_state.usuario_actual == "admin":
        with st.expander("👤 Gestión de Usuarios y Permisos (Admin)"):
            st.subheader("1. Registrar / Actualizar Usuario")
            u_nombre = st.text_input("Nombre de Usuario", key="admin_u_name")
            u_email = st.text_input("Correo Electrónico", key="admin_u_email")
            u_pass = st.text_input("Contraseña Inicial", type="password", key="admin_u_pass")
            
            st.markdown("**Permisos de Acceso a Pestañas:**")
            u_permisos = []
            for pestania in TODAS_LAS_PESTANIAS:
                if st.checkbox(f"Ver {pestania}", value=True, key=f"chk_add_{pestania}"):
                    u_permisos.append(pestania)
            
            if st.button("Guardar / Autorizar Usuario", type="primary"):
                if u_nombre and u_email and u_pass:
                    guardar_o_actualizar_usuario(u_nombre, u_email, u_pass, u_permisos)
                    st.success(f"Usuario `{u_nombre}` actualizado correctamente.")
                else:
                    st.warning("Completa todos los campos para registrar.")
            
            st.divider()
            
            st.subheader("2. Modificar Permisos Existentes")
            df_actual = obtener_usuarios_df()
            user_list = df_actual['usuario'].tolist()
            user_selected = st.selectbox("Seleccionar usuario para editar permisos:", user_list)
            
            if user_selected:
                row_user = df_actual[df_actual['usuario'] == user_selected].iloc[0]
                perm_actuales = row_user['perm_pestañas'].split(",") if row_user['perm_pestañas'] != "TODOS" else TODAS_LAS_PESTANIAS
                
                nuevos_permisos = []
                for p in TODAS_LAS_PESTANIAS:
                    is_active = p in perm_actuales
                    if st.checkbox(f"Acceso a {p}", value=is_active, key=f"edit_perm_{user_selected}_{p}"):
                        nuevos_permisos.append(p)
                
                if st.button(f"Actualizar Permisos de {user_selected}"):
                    actualizar_permisos_usuario(user_selected, nuevos_permisos)
                    st.success("Permisos actualizados con éxito.")
                    st.rerun()

            st.divider()

            st.subheader("3. 📦 Respaldo de Base de Datos de Usuarios")
            df_respaldo = obtener_usuarios_df()
            
            # Descarga CSV
            csv_data = df_respaldo.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📄 Descargar Respaldo (.CSV)",
                data=csv_data,
                file_name=f"respaldo_usuarios_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # Descarga Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_respaldo.to_excel(writer, index=False, sheet_name='Usuarios')
            excel_data = buffer.getvalue()
            
            st.download_button(
                label="📊 Descargar Respaldo (.XLSX)",
                data=excel_data,
                file_name=f"respaldo_usuarios_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.markdown("**Usuarios Registrados:**")
            st.dataframe(df_respaldo[['usuario', 'email', 'perm_pestañas']], use_container_width=True)

    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.usuario_actual = ""
        st.session_state.permisos_usuario = []
        st.rerun()

# -----------------------------------------------------------------------------
# VISUALIZACIÓN DINÁMICA DE PESTAÑAS SEGÚN PERMISOS
# -----------------------------------------------------------------------------
st.title("📊 Tablero de Control y Gestión - Auditoría Interna")

# Filtrar las pestañas visibles para este usuario
pestañas_visibles = [p for p in TODAS_LAS_PESTANIAS if p in st.session_state.permisos_usuario]

if not pestañas_visibles:
    st.warning("⚠️ No tienes permisos asignados para ver ninguna sección. Contacta al administrador.")
    st.stop()

# Crear tabs dinámicos
tabs_objetos = st.tabs(pestañas_visibles)

for nombre_tab, tab_obj in zip(pestañas_visibles, tabs_objetos):
    with tab_obj:
        st.header(f"Sección: {nombre_tab}")
        
        if nombre_tab == "Tablero":
            st.write("Aquí va el contenido general del Tablero (Kpis, Gráficos, etc.)")
        elif nombre_tab == "Programa Anual":
            st.write("Contenido del Programa Anual...")
        elif nombre_tab == "Alertas y Edición":
            st.write("Formularios de Edición y Alertas...")
        else:
            st.write(f"Vista habilitada para `{nombre_tab}`.")