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
    page_title="Tablero de Control - Planes de Acción Auditoría Interna",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------
# SISTEMA DE AUTENTICACIÓN SEGURA (STREAMLIT SECRETS)
# ---------------------------------------------------------
def validar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("## 🔒 Acceso Restringido")
        st.caption("Por favor, ingresa tus credenciales para acceder al tablero de Auditoría Interna.")
        
        c1, _ = st.columns([1.5, 2])
        with c1:
            usuario = st.text_input("Usuario", key="user_input_ai")
            password = st.text_input("Contraseña", type="password", key="pass_input_ai")
            
            if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                usuarios_validos = st.secrets.get("passwords", {})
                
                if usuario in usuarios_validos and str(usuarios_validos[usuario]) == password:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
        return False
    return True

# Bloquea el resto del tablero si no se ha iniciado sesión
if not validar_login():
    st.stop()

# ---------------------------------------------------------
# ESTILOS CSS COMPACTOS & RESPONSIVOS (OCULTA BOTÓN NEGRO)
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
        
        div[data-testid="stManageApp"] {display: none !important;}
        div[class*="stManageApp"] {display: none !important;}
        button[title*="Manage app"] {display: none !important;}
        iframe[title*="manage-app"] {display: none !important;}

        header[data-testid="stHeader"] {
            height: 2.5rem !important;
            background: transparent !important;
        }

        .block-container {
            padding-top: 2rem !important;
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

        [data-testid="stSidebar"] {
            min-width: 360px !important;
            max-width: 360px !important;
        }
        div[data-baseweb="popover"] {
            z-index: 99999999 !important;
            position: fixed !important;
        }
        div[role="listbox"] {
            z-index: 99999999 !important;
        }
        div[role="tooltip"],
        [data-baseweb="tooltip"],
        .stTooltipIcon span {
            display: block !important;
            z-index: 9999999 !important;
            max-width: 450px !important;
            white-space: normal !important;
            word-break: break-word !important;
        }
        div[role="tooltip"] div,
        [data-baseweb="tooltip"] div {
            z-index: 9999999 !important;
            background-color: #000000 !important;
            color: #ffffff !important;
            border-radius: 8px !important;
            padding: 8px 12px !important;
            font-size: 0.85rem !important;
            box-shadow: 0px 4px 12px rgba(0,0,0,0.3) !important;
        }
        div[data-baseweb="tag"] {
            max-width: 100% !important;
            height: auto !important;
            white-space: normal !important;
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
            margin-top: 12px !important;
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

        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-top: 1.5rem !important;
            }
            .titulo-tablero {
                font-size: 1.1rem !important;
                text-align: center;
            }
            .card-box {
                font-size: 0.95rem !important;
                padding: 6px 2px !important;
            }
            .block-header {
                font-size: 0.78rem !important;
            }
            div[data-testid="stDataFrame"] {
                width: 100% !important;
                overflow-x: auto !important;
            }
        }
    </style>
""",
    unsafe_allow_html=True,
)

# TÍTULO PRINCIPAL
st.markdown('<div class="titulo-tablero">📊 Tablero de Control - Planes de Acción Auditorías Internas</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# BÚSQUEDA ROBUSTA Y DINÁMICA DEL ARCHIVO EXCEL
# ---------------------------------------------------------
def buscar_excel_inteligente():
    dir_script = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    dir_padre = os.path.dirname(dir_script)

    rutas_candidatas = [
        r"C:\Users\diego\OneDrive\Escritorio\Tableros de Control\1. Auditorías Internas\TABLERO_PA_AI.xlsm",
        r"C:\Users\diego\OneDrive\Escritorio\Tableros de Control\1. Auditoría Interna\TABLERO_PA_I.xlsm",
        r"C:\Users\diego\OneDrive\Escritorio\Tableros de Control\1. Auditoria Interna\TABLERO_PA_I.xlsm",
        r"C:\Users\diego\OneDrive\Escritorio\Tableros de Control\1. Auditorías Internas\TABLERO_PA_AI.xlsx",
        r"C:\Users\diego\OneDrive\Escritorio\Tableros de Control\1. Auditoría Interna\TABLERO_PA_I.xlsx",
        os.path.join(dir_script, "TABLERO_PA_AI.xlsm"),
        os.path.join(dir_script, "TABLERO_PA_I.xlsm"),
        os.path.join(dir_script, "TABLERO_PA_AI.xlsx"),
        os.path.join(dir_script, "TABLERO_PA_I.xlsx"),
        os.path.join(dir_padre, "TABLERO_PA_AI.xlsm"),
        os.path.join(dir_padre, "TABLERO_PA_I.xlsm"),
    ]

    for ruta in rutas_candidatas:
        if os.path.exists(ruta):
            return ruta

    for folder in [dir_script, dir_padre]:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.endswith((".xlsm", ".xlsx")) and ("TABLERO" in file.upper() or "PA_" in file.upper()) and not file.startswith("~$"):
                    return os.path.join(folder, file)

    return rutas_candidatas[0]


EXCEL_PATH = buscar_excel_inteligente()


# ---------------------------------------------------------
# EXTRAER FECHA DE ACTUALIZACIÓN DIRECTA DE LA HOJA 'TABLERO'
# ---------------------------------------------------------
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
                        if row_idx + 1 < len(df_tablero):
                            val_next = str(df_tablero[col].iloc[row_idx + 1]).strip()
                            match_next = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", val_next)
                            if match_next:
                                return match_next.group(1)
        
        timestamp_mod = os.path.getmtime(EXCEL_PATH)
        return datetime.fromtimestamp(timestamp_mod).strftime("%d/%m/%Y")
    except Exception:
        if os.path.exists(EXCEL_PATH):
            timestamp_mod = os.path.getmtime(EXCEL_PATH)
            return datetime.fromtimestamp(timestamp_mod).strftime("%d/%m/%Y")
        return None


# ---------------------------------------------------------
# EXPORTACIÓN EXCEL SIN PERDIDA DE DATOS
# ---------------------------------------------------------
def generar_excel_formateado(df):
    output = io.BytesIO()
    df_export = df.copy()

    cols_fecha = []
    for col in df_export.columns:
        col_str = str(col).lower()
        if any(patron in col_str for patron in ["fecha", "terminacion", "cierre", "inicio", "vencimiento"]):
            cols_fecha.append(col)

    for col in cols_fecha:
        def formatear_fecha_seguro(val):
            if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "nat", ""]:
                return ""
            
            if isinstance(val, (datetime, pd.Timestamp, date)):
                return val.strftime("%d/%m/%Y")
            
            val_str = str(val).strip()
            try:
                dt = pd.to_datetime(val_str, format="%Y-%m-%d", errors="coerce")
                if pd.notnull(dt):
                    return dt.strftime("%d/%m/%Y")
                
                dt = pd.to_datetime(val_str, format="%d/%m/%Y", errors="coerce")
                if pd.notnull(dt):
                    return dt.strftime("%d/%m/%Y")
                
                dt = pd.to_datetime(val_str, dayfirst=True, errors="coerce")
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

        header_format = workbook.add_format({
            "bold": True,
            "text_wrap": True,
            "valign": "vcenter",
            "align": "center",
            "fg_color": "#1F4E78",
            "font_color": "#FFFFFF",
            "border": 1,
        })
        
        cell_format = workbook.add_format({"valign": "vcenter", "border": 1})
        date_cell_format = workbook.add_format({"valign": "vcenter", "align": "center", "border": 1})

        for col_num, value in enumerate(df_export.columns.values):
            worksheet.write(0, col_num, str(value), header_format)

        for i, col in enumerate(df_export.columns):
            es_col_fecha = col in cols_fecha
            
            if not df_export.empty:
                longitudes = [len(str(val)) for val in df_export[col].dropna().tolist()]
                max_len = max(longitudes) if longitudes else 0
            else:
                max_len = 0
            
            l_col = len(str(col))
            adjusted_width = min(max(max_len + 4, l_col + 4, 14), 65)
            
            if es_col_fecha:
                worksheet.set_column(i, i, adjusted_width, date_cell_format)
            else:
                worksheet.set_column(i, i, adjusted_width, cell_format)

        worksheet.hide_gridlines(2)

    return output.getvalue()


# ---------------------------------------------------------
# CARGA DE DATOS (BASE DE DATOS, INFORMES PDF Y PROGRAMA ANUAL)
# ---------------------------------------------------------
def cargar_datos():
    if not os.path.exists(EXCEL_PATH):
        st.error(f"⚠️ No se encontró el archivo Excel en la ruta:\n`{EXCEL_PATH}`")
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

        sheet_inf = "Informes PDF" if "Informes PDF" in xls.sheet_names else ("INFORMES PDF" if "INFORMES PDF" in xls.sheet_names else ("Informes pdf" if "Informes pdf" in xls.sheet_names else None))
        df_informes = pd.read_excel(xls, sheet_name=sheet_inf) if sheet_inf else pd.DataFrame()

        sheet_paa = "Programa Anual de Auditoría" if "Programa Anual de Auditoría" in xls.sheet_names else ("Programa Anual de Auditoria" if "Programa Anual de Auditoria" in xls.sheet_names else None)
        df_paa = pd.read_excel(xls, sheet_name=sheet_paa) if sheet_paa else pd.DataFrame()

        return df_base, df_calc, df_informes, df_paa
    except Exception as e:
        st.error(f"Error al cargar el archivo Excel: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


df_raw, df_calc, df_informes_raw, df_paa_raw = cargar_datos()

if df_raw.empty:
    st.stop()


# ---------------------------------------------------------
# DETECCIÓN DE COLUMNAS
# ---------------------------------------------------------
def buscar_columna_por_patron(df, patrones):
    for col in df.columns:
        col_clean = (
            str(col)
            .lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )
        for pat in patrones:
            if pat in col_clean:
                return col
    return None


col_estado = buscar_columna_por_patron(df_raw, ["estado del compromiso", "estado compromiso", "estado"])
col_responsable = buscar_columna_por_patron(df_raw, ["responsable", "area responsable"])
col_auditor_resp = "Auditor Responsable" if "Auditor Responsable" in df_raw.columns else buscar_columna_por_patron(df_raw, ["auditor responsable", "auditor"])
col_plan_filtro = "Plan Auditoría" if "Plan Auditoría" in df_raw.columns else buscar_columna_por_patron(df_raw, ["plan auditoria", "vigencia"])
col_plan_accion = "Plan de Acción" if "Plan de Acción" in df_raw.columns else buscar_columna_por_patron(df_raw, ["compromiso", "plan de accion", "accion"])

if not col_plan_accion:
    col_plan_accion = col_plan_filtro

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

# MESES PESTAÑA FINALIZADAS
meses_es = ["ENE", "FEB", "MAR", "ABR", "MAYO", "JUNIO", "JULIO", "AGO", "SEP", "OCT", "NOV", "DIC"]
conteo_meses = {m: 0 for m in meses_es}

if not df_calc.empty:
    for idx, row in df_calc.iterrows():
        val_m = str(row[0]).strip().lower()
        for idx_m, m_nombre in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]):
            if m_nombre in val_m:
                clave_m = meses_es[idx_m]
                conteo_meses[clave_m] = int(row[1]) if pd.notnull(row[1]) and str(row[1]).isdigit() else 0


# ---------------------------------------------------------
# FILTROS LATERALES, FECHA DE CORTE DEL EXCEL & CERRAR SESIÓN
# ---------------------------------------------------------
st.sidebar.title("🔍 Filtros del Tablero")

fecha_excel = obtener_fecha_excel()
if fecha_excel:
    st.sidebar.markdown(f"📅 **Datos actualizados al:** {fecha_excel}")

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

st.sidebar.markdown("---")

df_filtrado = df_raw.copy()

if col_estado:
    estados_vals = sorted([
        e for e in df_raw[col_estado].dropna().unique() 
        if str(e).lower() not in ["nan", "none", ""] and not re.search(r"finaliz|cerrad", str(e), re.IGNORECASE)
    ])
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
# MÉTRICAS Y GRÁFICOS
# ---------------------------------------------------------
abiertos = df_filtrado[col_estado].astype(str).str.contains("Abiert", case=False, na=False).sum() if col_estado else 0
vencidos = df_filtrado[col_estado].astype(str).str.contains("Vencid", case=False, na=False).sum() if col_estado else 0
sin_plan = df_filtrado[col_estado].astype(str).str.contains("Sin plan|Sin defin", case=False, na=False).sum() if col_estado else 0

df_activos = df_filtrado[~df_filtrado[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy() if col_estado else df_filtrado.copy()

if col_hallazgo and col_hallazgo in df_activos.columns:
    total_hallazgos_unicos_pendientes = df_activos[col_hallazgo].dropna().nunique()
else:
    total_hallazgos_unicos_pendientes = len(df_activos)

total_planes_pendientes = abiertos + vencidos + sin_plan

r_alto = df_activos[col_riesgo].astype(str).str.contains("Alto", case=False, na=False).sum() if col_riesgo else 0
r_medio = df_activos[col_riesgo].astype(str).str.contains("Medio", case=False, na=False).sum() if col_riesgo else 0
r_bajo = df_activos[col_riesgo].astype(str).str.contains("Bajo", case=False, na=False).sum() if col_riesgo else 0

# --- BARRAS ---
max_val_pend = max([abiertos, vencidos, sin_plan])
df_bar = pd.DataFrame({
    "Estado": ["Abiertos", "Vencidos", "Sin definir"], 
    "Cantidad": [abiertos, vencidos, sin_plan]
})

fig_bar = px.bar(df_bar, x="Estado", y="Cantidad", text="Cantidad", color="Estado", color_discrete_map={"Abiertos": "#58C57A", "Vencidos": "#FF5252", "Sin definir": "#F8A583"})
fig_bar.update_traces(textposition="outside", textfont=dict(size=12, color="var(--text-color)", family="Arial"), cliponaxis=False)
fig_bar.update_layout(
    showlegend=False,
    height=180,
    margin=dict(t=25, b=5, l=5, r=5),
    xaxis_title=None,
    yaxis_title=None,
    xaxis=dict(tickfont=dict(size=11, color="var(--text-color)", family="Arial")),
    yaxis=dict(showticklabels=False, range=[0, max_val_pend * 1.25 if max_val_pend > 0 else 10]),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

# --- DONAS ---
pct_abiertos = round((abiertos / total_planes_pendientes) * 100) if total_planes_pendientes > 0 else 0
colors_abiertos = ["#00B050" if i < (pct_abiertos / 5) else "#E0E0E0" for i in range(20)]

fig_dona_abiertos = go.Figure(data=[
    go.Pie(values=[1]*20, hole=0.68, marker_colors=colors_abiertos, marker_line=dict(color="#FFFFFF", width=2), textinfo="none", hoverinfo="none")
])
fig_dona_abiertos.add_annotation(text=f"<b>{pct_abiertos}%</b>", x=0.5, y=0.5, font=dict(size=28, color="var(--text-color)"), showarrow=False)
fig_dona_abiertos.update_layout(showlegend=False, height=145, margin=dict(t=2, b=2, l=2, r=2), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

pct_vencidos = round((vencidos / total_planes_pendientes) * 100) if total_planes_pendientes > 0 else 0
colors_vencidos = ["#FF5252" if i < (pct_vencidos / 5) else "#E0E0E0" for i in range(20)]

fig_dona_vencidos = go.Figure(data=[
    go.Pie(values=[1]*20, hole=0.68, marker_colors=colors_vencidos, marker_line=dict(color="#FFFFFF", width=2), textinfo="none", hoverinfo="none")
])
fig_dona_vencidos.add_annotation(text=f"<b>{pct_vencidos}%</b>", x=0.5, y=0.5, font=dict(size=28, color="var(--text-color)"), showarrow=False)
fig_dona_vencidos.update_layout(showlegend=False, height=145, margin=dict(t=2, b=2, l=2, r=2), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

# --- ÁREAS Y AUDITORÍAS ---
df_perf = df_filtrado.copy()
if col_estado in df_perf.columns:
    df_perf["Estado_Normalizado"] = df_perf[col_estado].fillna("").astype(str).str.strip()
    df_perf["Estado_Normalizado"] = df_perf["Estado_Normalizado"].apply(lambda x: "Abierta" if "abiert" in x.lower() else ("Vencida" if "vencid" in x.lower() else ("Sin plan de acción" if "sin" in x.lower() else x)))
else:
    df_perf["Estado_Normalizado"] = ""

s_est = df_perf["Estado_Normalizado"]

fig_area_horiz, total_acciones_area = None, 0
if col_responsable in df_perf.columns:
    df_pend = df_perf[~s_est.str.contains("Finaliz|Cerrad", case=False, na=False)].copy()
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

        calc_height_areas = max(480, len(df_totales_area) * 44)
        fig_area_horiz = px.bar(df_area_grouped, y=col_responsable, x="Cantidad", color="Estado_Normalizado", text="Texto_Etiqueta", orientation="h", barmode="stack", color_discrete_map={"Abierta": "#58C57A", "Vencida": "#FF5252", "Sin plan de acción": "#F8A583"})
        fig_area_horiz.update_traces(textposition="inside", insidetextanchor="middle", textfont=dict(size=12, color="white", family="Arial Black"), cliponaxis=False)

        for _, row in df_totales_area.iterrows():
            fig_area_horiz.add_annotation(y=row[col_responsable], x=row["Total_Pendientes"], text=f" <b>{row['Total_Pendientes']}</b>", showarrow=False, xanchor="left", yanchor="middle", font=dict(size=13, color="var(--text-color)"))
        max_pend_area = df_totales_area["Total_Pendientes"].max() if not df_totales_area.empty else 10
        fig_area_horiz.update_layout(
            height=calc_height_areas,
            coloraxis_showscale=False,
            yaxis=dict(type="category", autorange="reversed", title=None, automargin=True, tickfont=dict(color="var(--text-color)")),
            xaxis=dict(showticklabels=False, title=None, visible=False, showgrid=False, zeroline=False, range=[0, max_pend_area * 1.25]),
            legend_title_text="Estado",
            margin=dict(l=280, r=60, t=60, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

fig_aud_horiz, total_acciones_aud = None, 0
if col_auditoria in df_perf.columns:
    df_aud_pend_raw = df_perf[~s_est.str.contains("Finaliz|Cerrad", case=False, na=False)]
    if not df_aud_pend_raw.empty:
        total_acciones_aud = len(df_aud_pend_raw)
        df_aud_grouped = df_aud_pend_raw.groupby([col_auditoria, "Estado_Normalizado"]).size().reset_index(name="Cantidad")
        df_totales_aud = df_aud_grouped.groupby(col_auditoria)["Cantidad"].sum().reset_index(name="Total_Pendientes").sort_values(by="Total_Pendientes", ascending=False)
        df_aud_grouped[col_auditoria] = pd.Categorical(df_aud_grouped[col_auditoria], categories=df_totales_aud[col_auditoria], ordered=True)
        df_aud_grouped["Texto_Etiqueta"] = df_aud_grouped["Cantidad"].apply(lambda x: f"<b>{x}</b>" if x > 1 else "")

        calc_height_auds = max(450, len(df_totales_aud) * 44)
        fig_aud_horiz = px.bar(df_aud_grouped, y=col_auditoria, x="Cantidad", color="Estado_Normalizado", text="Texto_Etiqueta", orientation="h", barmode="stack", color_discrete_map={"Abierta": "#58C57A", "Vencida": "#FF5252", "Sin plan de acción": "#F8A583"})
        fig_aud_horiz.update_traces(textposition="inside", insidetextanchor="middle", textfont=dict(size=12, color="white", family="Arial Black"), cliponaxis=False)

        for _, row in df_totales_aud.iterrows():
            fig_aud_horiz.add_annotation(y=row[col_auditoria], x=row["Total_Pendientes"], text=f" <b>{row['Total_Pendientes']}</b>", showarrow=False, xanchor="left", yanchor="middle", font=dict(size=13, color="var(--text-color)"))
        max_pend_aud = df_totales_aud["Total_Pendientes"].max() if not df_totales_aud.empty else 10
        fig_aud_horiz.update_layout(
            height=calc_height_auds,
            coloraxis_showscale=False,
            yaxis=dict(type="category", autorange="reversed", title=None, automargin=True, tickfont=dict(color="var(--text-color)")),
            xaxis=dict(showticklabels=False, title=None, visible=False, showgrid=False, zeroline=False, range=[0, max_pend_aud * 1.25]),
            legend_title_text="Estado",
            margin=dict(l=280, r=60, t=60, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )


# ---------------------------------------------------------
# PESTAÑAS PRINCIPALES (8 PESTAÑAS COMPLETAS E INTEGRADAS)
# ---------------------------------------------------------
tab_principal, tab_metricas, tab_historico, tab_paa, tab_alertas, tab_oficios, tab_finalizadas, tab_informes = st.tabs([
    "📊 Tablero",
    "📈 Métricas",
    "📊 Histórico",
    "🗓️ Programa Anual",
    "🚨 Alertas y Edición",
    "📩 Oficios",
    "🎉 Finalizadas",
    "📑 Informes",
])

# =========================================================
# PESTAÑA 1: TABLERO PRINCIPAL
# =========================================================
with tab_principal:
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

        st.markdown(
            f"""
            <div style="display: flex; flex-direction: column; align-items: center; width: 100%;">
                <div class="alert-row-compact">
                    <div class="alert-item-label">
                        <span>5 días</span><span>🔴</span>
                    </div>
                    <div class="alert-val-box">{val_5}</div>
                </div>
                <div class="alert-row-compact">
                    <div class="alert-item-label">
                        <span>10 días</span><span>🟡</span>
                    </div>
                    <div class="alert-val-box">{val_10}</div>
                </div>
                <div class="alert-row-compact">
                    <div class="alert-item-label">
                        <span>20 días</span><span>🟢</span>
                    </div>
                    <div class="alert-val-box">{val_20}</div>
                </div>
                <div class="alert-row-compact">
                    <div class="alert-item-label">
                        <span>30 días</span><span>🔵</span>
                    </div>
                    <div class="alert-val-box">{val_30}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="block-header" style="margin-top:2px;">Distribución de Planes Pendientes</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_bar, use_container_width=True, key="fig_bar_pendientes")

    with c4:
        st.markdown('<div class="block-header">Porcentaje de Acciones Pendientes</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="block-header" style="font-size:0.75rem; text-transform:none; margin-bottom:0px; color:#00B050;">🟢 En tiempo (Abiertos)</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_dona_abiertos, use_container_width=True, key="fig_dona_abiertos_key")
        
        st.markdown('<div class="block-header" style="font-size:0.75rem; text-transform:none; margin-bottom:0px; color:#FF5252;">🔴 Vencidos</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_dona_vencidos, use_container_width=True, key="fig_dona_vencidos_key")

    st.markdown("---")

    col_sub, col_filtro_rapido = st.columns([2, 1])
    with col_sub:
        st.subheader("📋 Detalle General de Compromisos Pendientes")
    with col_filtro_rapido:
        opciones_rapidas = ["(Mostrar Todos)", "Riesgo: Alto", "Riesgo: Medio", "Riesgo: Bajo", "Estado: Abiertos", "Estado: Vencidos", "Estado: Sin definir"]
        if col_a5:
            opciones_rapidas.append("Alerta: Próximos a 5 días")
        if col_a10:
            opciones_rapidas.append("Alerta: Próximos a 10 días")
        if col_a20:
            opciones_rapidas.append("Alerta: Próximos a 20 días")
        if col_a30:
            opciones_rapidas.append("Alerta: Próximos a 30 días")

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

    df_tabla.index = range(1, len(df_tabla) + 1)
    st.dataframe(df_tabla, use_container_width=True)

    st.download_button(
        label="📥 Descargar Excel (.xlsx)",
        data=generar_excel_formateado(df_tabla),
        file_name=f"Detalle_Compromisos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )


# =========================================================
# PESTAÑA 2: MÉTRICAS DE CUMPLIMIENTO
# =========================================================
with tab_metricas:
    st.header("📈 Resumen de Estado y Desempeño")
    st.markdown("Vista general del avance de compromisos por área y auditoría.")

    comp_vencidos_pendientes = df_activos[col_estado].astype(str).str.contains("Vencid", case=False, na=False).sum() if col_estado else 0
    comp_criticos_pendientes = df_activos[col_riesgo].astype(str).str.contains("Alto", case=False, na=False).sum() if col_riesgo else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Planes de Acción Pendientes", total_planes_pendientes)
    m2.metric("🔴 Compromisos Vencidos", comp_vencidos_pendientes, delta=f"{(comp_vencidos_pendientes/total_planes_pendientes*100):.1f}% de pendientes" if total_planes_pendientes > 0 else "0%", delta_color="inverse")
    m3.metric("🔥 Hallazgos Riesgo Alto", comp_criticos_pendientes, delta=f"{(comp_criticos_pendientes/total_planes_pendientes*100):.1f}% de pendientes" if total_planes_pendientes > 0 else "0%", delta_color="inverse")
    m4.metric("🎯 Tasa Global de Cierre", f"{pct_abiertos}%", delta="Objetivo: 85%")

    st.markdown("---")

    st.subheader("👥 Distribución de Compromisos Pendientes por Área")
    st.markdown('<div class="small-note"><b>ℹ️ Nota sobre Responsabilidad Compartida:</b> Los hallazgos con responsabilidad compartida se contabilizan en los compromisos de cada Área individualmente.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="total-acciones-box">📌 Total acciones: {total_acciones_area}</div>', unsafe_allow_html=True)

    if fig_area_horiz is not None:
        st.plotly_chart(fig_area_horiz, use_container_width=True, key="fig_area_horiz_key")
    else:
        st.success("🎉 ¡Excelente! No hay compromisos pendientes en ninguna área.")

    st.markdown("---")
    st.subheader("🔬 Distribución de Compromisos Pendientes por Auditoría")
    st.markdown(f'<div class="total-acciones-box">📌 Total acciones: {total_acciones_aud}</div>', unsafe_allow_html=True)

    if fig_aud_horiz is not None:
        st.plotly_chart(fig_aud_horiz, use_container_width=True, key="fig_aud_horiz_key")
    else:
        st.info("No hay compromisos pendientes en las auditorías.")


# =========================================================
# PESTAÑA 3: COMPARATIVA HISTÓRICA DE PLANES DE MEJORAMIENTO
# =========================================================
with tab_historico:
    st.header("📊 Análisis Histórico e Interanual de Planes de Mejoramiento")
    st.markdown("Evolución del volumen de **Planes de Mejoramiento** por vigencia y distribución por Área Responsable.")

    if col_plan_filtro and col_plan_filtro in df_raw.columns:
        df_hist_calc = df_raw.copy()
        df_hist_calc["Vigencia_Limpia"] = df_hist_calc[col_plan_filtro].astype(str).str.strip()
        
        c_h1, c_h2 = st.columns(2)

        with c_h1:
            df_vigencia_totales = df_hist_calc.groupby("Vigencia_Limpia").size().reset_index(name="Total_Planes").sort_values(by="Vigencia_Limpia")
            max_hall_v = df_vigencia_totales["Total_Planes"].max() if not df_vigencia_totales.empty else 10
            sum_tot_g1 = df_vigencia_totales["Total_Planes"].sum() if not df_vigencia_totales.empty else 0
            
            fig_hist_line = px.bar(
                df_vigencia_totales,
                x="Vigencia_Limpia",
                y="Total_Planes",
                text="Total_Planes",
                title="Evolución Total de Planes de Mejoramiento por Vigencia",
                color_discrete_sequence=["#1F4E78"]
            )
            fig_hist_line.update_traces(textposition="outside", textfont=dict(size=13, color="var(--text-color)"))
            fig_hist_line.update_layout(
                height=360,
                xaxis_title=None,
                yaxis_title=None,
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, max_hall_v * 1.35]),
                margin=dict(t=50, b=40, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_hist_line, use_container_width=True, key="fig_hist_line_key")
            
            st.markdown(f'<div class="total-acciones-box" style="width:100%; text-align:center;">📌 Total Planes de Mejoramiento Históricos: <b>{sum_tot_g1}</b></div>', unsafe_allow_html=True)

        with c_h2:
            df_hist_grouped = df_hist_calc.groupby(["Vigencia_Limpia", col_estado]).size().reset_index(name="Cantidad")
            df_hist_grouped["Texto_Etiqueta"] = df_hist_grouped["Cantidad"].apply(lambda x: str(x) if x > 0 else "")
            max_hist_st = df_hist_grouped.groupby("Vigencia_Limpia")["Cantidad"].sum().max() if not df_hist_grouped.empty else 10
            sum_tot_g2 = df_hist_grouped["Cantidad"].sum() if not df_hist_grouped.empty else 0

            fig_hist_stack = px.bar(
                df_hist_grouped,
                x="Vigencia_Limpia",
                y="Cantidad",
                color=col_estado,
                text="Texto_Etiqueta",
                title="Distribución de Estados por Vigencia",
                barmode="stack",
                color_discrete_map={"Abierta": "#58C57A", "Vencida": "#FF5252", "Finalizada": "#4B92DB", "Sin plan de acción": "#F8A583"}
            )
            fig_hist_stack.update_traces(
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=11, color="white", family="Arial Black")
            )
            
            df_totales_por_vigencia = df_hist_grouped.groupby("Vigencia_Limpia")["Cantidad"].sum().reset_index()
            for _, row_v in df_totales_por_vigencia.iterrows():
                fig_hist_stack.add_annotation(
                    x=row_v["Vigencia_Limpia"],
                    y=row_v["Cantidad"],
                    text=f"<b>{row_v['Cantidad']}</b>",
                    showarrow=False,
                    yanchor="bottom",
                    font=dict(size=12, color="var(--text-color)")
                )

            fig_hist_stack.update_layout(
                height=360,
                xaxis_title=None,
                yaxis_title=None,
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, max_hist_st * 1.35]),
                legend_title_text="Estado",
                margin=dict(t=50, b=40, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_hist_stack, use_container_width=True, key="fig_hist_stack_key")

            st.markdown(f'<div class="total-acciones-box" style="width:100%; text-align:center;">📌 Total Evaluados: <b>{sum_tot_g2}</b></div>', unsafe_allow_html=True)

        st.markdown("---")

        st.subheader("👥 Matriz Comparativa Interanual por Área Responsable")
        st.markdown('<div class="small-note">Detalle del comportamiento y distribución de los <b>Planes de Mejoramiento</b> asignados a cada Área en las distintas vigencias.</div>', unsafe_allow_html=True)

        if col_responsable and col_responsable in df_hist_calc.columns:
            df_area_hist = df_hist_calc.copy()
            df_area_hist[col_responsable] = df_area_hist[col_responsable].astype(str).str.replace("\n", ",").str.split(",")
            df_area_hist_exploded = df_area_hist.explode(col_responsable)
            df_area_hist_exploded[col_responsable] = df_area_hist_exploded[col_responsable].astype(str).str.strip()
            df_area_hist_exploded = df_area_hist_exploded[~df_area_hist_exploded[col_responsable].isin(["", "nan", "None", "None."])]

            df_pivot_area = pd.pivot_table(
                df_area_hist_exploded,
                index=col_responsable,
                columns="Vigencia_Limpia",
                aggfunc="size",
                fill_value=0
            )
            df_pivot_area["Total Histórico"] = df_pivot_area.sum(axis=1)
            df_pivot_area = df_pivot_area.sort_values(by="Total Histórico", ascending=False)
            
            st.dataframe(df_pivot_area, use_container_width=True)

    else:
        st.warning("⚠️ No se detectó la columna 'Plan Auditoría / Vigencia' para estructurar la comparativa histórica.")


# =========================================================
# PESTAÑA 4: PROGRAMA ANUAL DE AUDITORÍA
# =========================================================
with tab_paa:
    st.header("🗓️ Programa Anual de Auditoría (PAA)")
    st.markdown("Relación de actividades, auditorías específicas y su estado de ejecución agrupadas por vigencia.")

    if not df_paa_raw.empty:
        df_paa_vista = df_paa_raw.copy()
        
        col_vig_paa = buscar_columna_por_patron(df_paa_vista, ["vigencia"]) or df_paa_vista.columns[0]
        col_tipo_paa = buscar_columna_por_patron(df_paa_vista, ["tipologia", "tipo"]) or df_paa_vista.columns[1]
        col_nom_paa = buscar_columna_por_patron(df_paa_vista, ["nombre", "auditoria"]) or df_paa_vista.columns[2]
        col_est_paa = buscar_columna_por_patron(df_paa_vista, ["estado"]) or df_paa_vista.columns[3]

        df_paa_vista[col_vig_paa] = df_paa_vista[col_vig_paa].ffill()
        df_paa_vista[col_vig_paa] = (
            df_paa_vista[col_vig_paa]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        if col_tipo_paa:
            df_paa_vista[col_tipo_paa] = df_paa_vista[col_tipo_paa].ffill()

        vigencias_paa_unicas = sorted([
            v for v in df_paa_vista[col_vig_paa].dropna().unique() 
            if str(v).lower() not in ["nan", "none", ""]
        ])

        if vigencias_paa_unicas:
            subtabs_paa = st.tabs([f"📅 Vigencia {v}" if str(v).isdigit() else str(v) for v in vigencias_paa_unicas])

            for i, vig in enumerate(vigencias_paa_unicas):
                with subtabs_paa[i]:
                    df_sub_paa = df_paa_vista[df_paa_vista[col_vig_paa] == vig].copy().reset_index(drop=True)
                    
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

                    df_sub_paa.index = range(1, len(df_sub_paa) + 1)

                    # Formato sin negrita en las filas finalizadas (solo fondo verde suave)
                    def resaltar_finalizadas(row):
                        val_est = str(row[col_est_paa]).lower() if col_est_paa and pd.notnull(row[col_est_paa]) else ""
                        if "finaliz" in val_est:
                            return ["background-color: #D9EAD3; color: #000000; font-weight: normal;"] * len(row)
                        return [""] * len(row)

                    st.dataframe(
                        df_sub_paa.style.apply(resaltar_finalizadas, axis=1),
                        use_container_width=True
                    )

            st.markdown("---")
            st.download_button(
                label="📥 Descargar Programa Anual de Auditoría (.xlsx)",
                data=generar_excel_formateado(df_paa_vista),
                file_name=f"Programa_Anual_Auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_paa",
                use_container_width=False,
            )
        else:
            st.info("ℹ️ No hay vigencias registradas en la hoja 'Programa Anual de Auditoría'.")
    else:
        st.info("ℹ️ No se encontró información en la hoja 'Programa Anual de Auditoría' del archivo Excel.")


# =========================================================
# PESTAÑA 5: ALERTAS Y EDICIÓN
# =========================================================
with tab_alertas:
    st.header("🚨 Alertas Críticas y Edición Directa")

    df_alertas = df_filtrado.copy()
    hoy = pd.to_datetime(date.today())

    if col_fecha_cierre and col_fecha_cierre in df_alertas.columns:
        df_alertas["Fecha_DT"] = pd.to_datetime(df_alertas[col_fecha_cierre], errors="coerce")
        df_alertas["Dias_Atraso"] = (hoy - df_alertas["Fecha_DT"]).dt.days
        df_alertas["Dias_Atraso"] = df_alertas["Dias_Atraso"].apply(lambda x: x if x > 0 else 0)
    else:
        df_alertas["Dias_Atraso"] = 0

    df_criticos_30 = df_alertas[(~df_alertas[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)) & (df_alertas["Dias_Atraso"] >= 30)].sort_values(by="Dias_Atraso", ascending=False)

    col_ac1, col_ac2 = st.columns(2)
    col_ac1.metric("🔴 Planes Críticos (≥ 30 Días Mora)", len(df_criticos_30))
    prom_mora = int(df_criticos_30["Dias_Atraso"].mean()) if not df_criticos_30.empty else 0
    col_ac2.metric("⏱️ Promedio Días Vencidos", f"{prom_mora} días")

    if not df_criticos_30.empty:
        df_criticos_30_vista = df_criticos_30.copy()
        df_criticos_30_vista.index = range(1, len(df_criticos_30_vista) + 1)
        st.subheader("📋 Tabla de Compromisos Críticos")
        st.dataframe(df_criticos_30_vista, use_container_width=True)

        st.download_button(
            label="📥 Descargar Acciones Críticas en Excel (.xlsx)",
            data=generar_excel_formateado(df_criticos_30_vista),
            file_name=f"Compromisos_Criticos_30Dias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=False,
            key="btn_descarga_criticos_30"
        )
    else:
        st.success("🎉 ¡Excelente! No existen planes de acción con mora de 30 días o más.")

    st.markdown("---")
    st.subheader("✏️ Establecer Compromisos")

    col_f_aud, col_f_auditor, col_f_plan, col_f_estado = st.columns(4)

    df_edicion_temp = df_raw.copy()

    # 1. Filtro Auditoría
    opciones_auditoria = ["(Todas)"]
    if col_auditoria and col_auditoria in df_raw.columns:
        opciones_auditoria += sorted([str(x) for x in df_raw[col_auditoria].dropna().unique() if str(x).strip()])
    with col_f_aud:
        aud_seleccionada = st.selectbox("1. Filtrar por Auditoría:", options=opciones_auditoria, key="f_aud_edit")

    if aud_seleccionada != "(Todas)":
        df_edicion_temp = df_edicion_temp[df_edicion_temp[col_auditoria].astype(str).str.strip().str.lower() == aud_seleccionada.strip().lower()]

    # 2. Filtro Auditor
    opciones_auditor = ["(Todos)"]
    if col_auditor_resp and col_auditor_resp in df_edicion_temp.columns:
        opciones_auditor += sorted([str(x) for x in df_edicion_temp[col_auditor_resp].dropna().unique() if str(x).strip()])
    with col_f_auditor:
        auditor_seleccionado = st.selectbox("2. Filtrar por Auditor:", options=opciones_auditor, key="f_auditor_edit")

    if auditor_seleccionado != "(Todos)":
        df_edicion_temp = df_edicion_temp[df_edicion_temp[col_auditor_resp].astype(str).str.strip().str.lower() == auditor_seleccionado.strip().lower()]

    # 3. Filtro Plan / Vigencia
    opciones_plan_v = ["(Todos)"]
    if col_plan_filtro and col_plan_filtro in df_edicion_temp.columns:
        opciones_plan_v += sorted([str(x) for x in df_edicion_temp[col_plan_filtro].dropna().unique() if str(x).strip()])
    with col_f_plan:
        plan_v_seleccionado = st.selectbox("3. Filtrar por Plan / Vigencia:", options=opciones_plan_v, key="f_plan_edit")

    if plan_v_seleccionado != "(Todos)":
        df_edicion_temp = df_edicion_temp[df_edicion_temp[col_plan_filtro].astype(str).str.strip().str.lower() == plan_v_seleccionado.strip().lower()]

    # 4. Filtro Estado
    opciones_estado_f = ["(Todos)"]
    if col_estado and col_estado in df_edicion_temp.columns:
        opciones_estado_f += sorted([str(x) for x in df_edicion_temp[col_estado].dropna().unique() if str(x).strip()])
    with col_f_estado:
        estado_filtro_sel = st.selectbox("4. Filtrar por Estado:", options=opciones_estado_f, key="f_estado_edit")

    if estado_filtro_sel != "(Todos)":
        df_edicion_temp = df_edicion_temp[df_edicion_temp[col_estado].astype(str).str.strip().str.lower() == estado_filtro_sel.strip().lower()]

    # 5. Filtro Plan de Acción
    opciones_pa_f = ["(Todos)"]
    if col_plan_accion and col_plan_accion in df_edicion_temp.columns:
        opciones_pa_f += sorted([str(x) for x in df_edicion_temp[col_plan_accion].dropna().unique() if str(x).strip()])

    pa_filtro_sel = st.selectbox("5. Filtrar por Plan de Acción:", options=opciones_pa_f, key="f_pa_edit")

    if pa_filtro_sel != "(Todos)":
        df_edicion_temp = df_edicion_temp[df_edicion_temp[col_plan_accion].astype(str).str.strip().str.lower() == pa_filtro_sel.strip().lower()]

    # 6. Registros Filtrados Finales
    if col_hallazgo and not df_edicion_temp.empty:
        dict_opciones = {}
        for _, row in df_edicion_temp.dropna(subset=[col_hallazgo]).iterrows():
            val_h = str(row[col_hallazgo])
            val_n = str(row[col_nombre]).strip() if col_nombre and col_nombre in row and pd.notnull(row[col_nombre]) else ""
            etiqueta = f"[{val_n}] - {val_h}" if val_n and val_n.lower() != "nan" else val_h
            dict_opciones[etiqueta] = val_h

        if len(dict_opciones) == 0:
            st.warning("⚠️ No se encontraron hallazgos con la combinación exacta de los filtros seleccionados.")
        else:
            etiqueta_sel = st.selectbox("6. Seleccione el Registro / Hallazgo a Modificar:", options=list(dict_opciones.keys()), key="f_hallazgo_sel")
            id_sel = dict_opciones[etiqueta_sel]

            mask = df_edicion_temp[col_hallazgo] == id_sel
            registro = df_edicion_temp[mask].iloc[0] if mask.any() else None
            idx_exacto_raw = df_edicion_temp[mask].index[0] if mask.any() else None

            plan_actual_val = str(registro[col_plan_accion]) if registro is not None and col_plan_accion and pd.notnull(registro[col_plan_accion]) else ""
            est_actual_val = str(registro[col_estado]) if registro is not None and col_estado and pd.notnull(registro[col_estado]) else "Abierta"
            resp_actual_val = str(registro[col_responsable]) if registro is not None and col_responsable and pd.notnull(registro[col_responsable]) else ""

            fecha_def_obj = date.today()
            fecha_antigua_str = ""
            if registro is not None and col_fecha_cierre and pd.notnull(registro[col_fecha_cierre]):
                try:
                    fecha_def_obj = pd.to_datetime(registro[col_fecha_cierre]).date()
                    fecha_antigua_str = fecha_def_obj.strftime("%d/%m/%Y")
                except Exception:
                    fecha_antigua_str = str(registro[col_fecha_cierre])

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                nueva_fecha_cierre = st.date_input("Nueva Fecha de Cierre / Compromiso:", value=fecha_def_obj, key=f"in_fecha_{idx_exacto_raw}")
                lista_estados = ["Abierta", "Vencida", "Finalizada", "Sin plan de acción"]
                if est_actual_val and est_actual_val not in lista_estados:
                    lista_estados.append(est_actual_val)
                idx_est_def = lista_estados.index(est_actual_val) if est_actual_val in lista_estados else 0
                nuevo_estado = st.selectbox("Estado del Compromiso (Editable):", options=lista_estados, index=idx_est_def, key=f"in_estado_{idx_exacto_raw}")
                nuevo_responsable = st.text_input("Responsable Asignado (Editable):", value=resp_actual_val, key=f"in_resp_{idx_exacto_raw}")

            with col_f2:
                nuevo_plan_accion = st.text_area("Plan de Acción / Compromiso (Editable):", value=plan_actual_val, height=100, key=f"in_plan_{idx_exacto_raw}")
                obs_usuario = st.text_area("Observaciones adicionales / Notas:", value="", height=80, key=f"in_obs_{idx_exacto_raw}")

            btn_guardar = st.button("➕ Registrar Cambio", type="primary", use_container_width=False, key=f"btn_save_{idx_exacto_raw}")

            if btn_guardar:
                fecha_hoy_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                nueva_fecha_str = nueva_fecha_cierre.strftime("%d/%m/%Y")

                col_destino_obs = col_obs_audit if col_obs_audit else "Observación Auditoría"
                obs_historico_previo = str(df_raw.at[idx_exacto_raw, col_destino_obs]) if pd.notnull(df_raw.at[idx_exacto_raw, col_destino_obs]) else ""

                nuevo_registro_historial = f"--- Modificación el {fecha_hoy_str} ---\n"
                if fecha_antigua_str != nueva_fecha_str:
                    nuevo_registro_historial += f"• Fecha Cierre Anterior: {fecha_antigua_str} ➡️ Nueva: {nueva_fecha_str}\n"
                if est_actual_val != nuevo_estado:
                    nuevo_registro_historial += f"• Estado Anterior: {est_actual_val} ➡️ Nuevo: {nuevo_estado}\n"
                if resp_actual_val != nuevo_responsable:
                    nuevo_registro_historial += f"• Responsable Anterior: {resp_actual_val} ➡️ Nuevo: {nuevo_responsable}\n"
                if plan_actual_val != nuevo_plan_accion:
                    nuevo_registro_historial += f"• Plan Anterior: {plan_actual_val}\n• Plan Nuevo: {nuevo_plan_accion}\n"
                if obs_usuario.strip():
                    nuevo_registro_historial += f"• Nota: {obs_usuario.strip()}\n"

                if obs_historico_previo.strip() and obs_historico_previo.lower() != "nan":
                    obs_final = f"{nuevo_registro_historial}\n{obs_historico_previo}"
                else:
                    obs_final = nuevo_registro_historial

                fila_modificada = df_raw.loc[idx_exacto_raw].copy()
                if col_fecha_cierre:
                    fila_modificada[col_fecha_cierre] = nueva_fecha_str
                if col_estado:
                    fila_modificada[col_estado] = nuevo_estado
                if col_responsable:
                    fila_modificada[col_responsable] = nuevo_responsable
                if col_plan_accion:
                    fila_modificada[col_plan_accion] = nuevo_plan_accion
                fila_modificada[col_destino_obs] = obs_final.strip()

                if "lote_filas_modificadas" not in st.session_state:
                    st.session_state["lote_filas_modificadas"] = {}

                st.session_state["lote_filas_modificadas"][id_sel] = fila_modificada

                st.toast("✅ ¡Registro agregado exitosamente!", icon="🎉")

    # ---------------------------------------------------------
    # DESCARGA DE REGISTROS MODIFICADOS
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("📥 Descargar Registros Modificados en el Día")

    if "lote_filas_modificadas" not in st.session_state:
        st.session_state["lote_filas_modificadas"] = {}

    if "limpiar_key" not in st.session_state:
        st.session_state["limpiar_key"] = 0

    version_key = st.session_state["limpiar_key"]

    cant_modificados = len(st.session_state["lote_filas_modificadas"])
    lista_acumulada = list(st.session_state["lote_filas_modificadas"].values())

    if cant_modificados > 0:
        st.markdown(f'<div style="background-color: #D4EDDA; color: #155724; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; font-weight: bold;">✅ ¡Tienes {cant_modificados} plan(es) modificado(s) listo(s) para exportar!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color: #E2E3E5; color: #383D41; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">ℹ️ Aún no has realizado modificaciones en esta sesión.</div>', unsafe_allow_html=True)

    col_btn_dl, col_btn_clear, _ = st.columns([2.5, 1.2, 2.3])

    with col_btn_dl:
        if cant_modificados > 0:
            excel_lote = generar_excel_formateado(pd.DataFrame(lista_acumulada))
            st.download_button(
                label=f"📥 Descargar Modificaciones ({cant_modificados})",
                data=excel_lote,
                file_name=f"Planes_Modificados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"btn_download_lote_{version_key}",
                use_container_width=False,
            )
        else:
            st.button("📥 Descargar Modificaciones (0)", disabled=True, use_container_width=False, key=f"btn_download_disabled_{version_key}")

    with col_btn_clear:
        if st.button("🗑️ Limpiar Historial", type="secondary", use_container_width=False, disabled=(cant_modificados == 0), key=f"btn_clear_historial_{version_key}"):
            st.session_state["lote_filas_modificadas"] = {}
            st.session_state["limpiar_key"] += 1
            st.rerun()


# =========================================================
# PESTAÑA 6: OFICIOS DE SOLICITUD
# =========================================================
with tab_oficios:
    st.header("📩 Registro e Historial de Oficios Radicados")
    st.markdown("Consulta y trazabilidad formal de los oficios enviados para soporte de modificaciones.")

    col_rad_target = df_filtrado.columns[21] if len(df_filtrado.columns) > 21 else buscar_columna_por_patron(df_filtrado, ["radicado"])
    col_fecha_target = df_filtrado.columns[22] if len(df_filtrado.columns) > 22 else buscar_columna_por_patron(df_filtrado, ["fecha"])
    col_area_target = df_filtrado.columns[23] if len(df_filtrado.columns) > 23 else buscar_columna_por_patron(df_filtrado, ["area remitente", "remitente"])
    col_asunto_target = df_filtrado.columns[24] if len(df_filtrado.columns) > 24 else buscar_columna_por_patron(df_filtrado, ["asunto", "solicitud"])
    col_est_sol_target = df_filtrado.columns[25] if len(df_filtrado.columns) > 25 else buscar_columna_por_patron(df_filtrado, ["estado de la solicitud", "estado solicitud"])
    col_link_target = df_filtrado.columns[26] if len(df_filtrado.columns) > 26 else buscar_columna_por_patron(df_filtrado, ["enlace pdf", "enlace", "pdf"])

    if col_rad_target and col_rad_target in df_filtrado.columns:
        df_oficios_raw = df_filtrado.dropna(subset=[col_rad_target]).copy()
        
        palabras_invalidas = ["nan", "none", "", "0", "0.0", "false", "eliminada", "eliminado", "cancelada", "sin radicado"]
        df_oficios_raw = df_oficios_raw[~df_oficios_raw[col_rad_target].astype(str).str.strip().str.lower().isin(palabras_invalidas)]

        if not df_oficios_raw.empty:
            col_id_nombre = "ID" if "ID" in df_oficios_raw.columns else ("id" if "id" in df_oficios_raw.columns else None)
            
            radicados_procesados = {}
            for _, row in df_oficios_raw.iterrows():
                rad_raw = str(row[col_rad_target]).strip()
                rad_val = rad_raw.replace(".0", "") if rad_raw.endswith(".0") else rad_raw

                id_val = str(row[col_id_nombre]).replace(".0", "").strip() if col_id_nombre and col_id_nombre in row and pd.notnull(row[col_id_nombre]) else ""
                
                fecha_val_str = ""
                if col_fecha_target and col_fecha_target in row and pd.notnull(row[col_fecha_target]):
                    f_val = row[col_fecha_target]
                    if isinstance(f_val, (datetime, pd.Timestamp, date)):
                        fecha_val_str = f_val.strftime("%d/%m/%Y")
                    else:
                        try:
                            dt = pd.to_datetime(str(f_val).strip(), errors="coerce")
                            if pd.notnull(dt):
                                fecha_val_str = dt.strftime("%d/%m/%Y")
                            else:
                                fecha_val_str = str(f_val).strip()
                        except Exception:
                            fecha_val_str = str(f_val).strip()

                area_val = str(row[col_area_target]) if col_area_target and pd.notnull(row[col_area_target]) and str(row[col_area_target]).lower() != "none" else ""
                asunto_val = str(row[col_asunto_target]) if col_asunto_target and pd.notnull(row[col_asunto_target]) and str(row[col_asunto_target]).lower() != "none" else ""
                est_sol_val = str(row[col_est_sol_target]) if col_est_sol_target and pd.notnull(row[col_est_sol_target]) and str(row[col_est_sol_target]).lower() != "none" else "Aprobado"
                
                link_val = str(row[col_link_target]).strip() if col_link_target and pd.notnull(row[col_link_target]) and str(row[col_link_target]).lower() != "none" else ""
                if link_val and not link_val.startswith("http"):
                    link_val = f"https://{link_val}"

                if rad_val not in radicados_procesados:
                    radicados_procesados[rad_val] = {
                        "Radicado": rad_val,
                        "IDs Afectados": [id_val] if id_val else [],
                        "Fecha": fecha_val_str,
                        "Área Remitente": area_val,
                        "Asunto": asunto_val,
                        "Estado de la Solicitud": est_sol_val,
                        "Enlace PDF": link_val
                    }
                else:
                    if id_val and id_val not in radicados_procesados[rad_val]["IDs Afectados"]:
                        radicados_procesados[rad_val]["IDs Afectados"].append(id_val)
                    if not radicados_procesados[rad_val]["Fecha"] and fecha_val_str:
                        radicados_procesados[rad_val]["Fecha"] = fecha_val_str

            lista_final_oficios = []
            for rad_val, datos in radicados_procesados.items():
                datos["IDs Afectados"] = ", ".join(sorted(datos["IDs Afectados"]))
                lista_final_oficios.append(datos)

            df_oficios_vista = pd.DataFrame(lista_final_oficios)
            df_oficios_vista.index = range(1, len(df_oficios_vista) + 1)
            
            tot_oficios_unicos = len(df_oficios_vista)
            aprobados_cnt = df_oficios_vista["Estado de la Solicitud"].astype(str).str.contains("Aprob", case=False, na=False).sum() if "Estado de la Solicitud" in df_oficios_vista.columns else tot_oficios_unicos
            
            mo1, mo2, _ = st.columns([1, 1, 2])
            mo1.metric("📑 Total Oficios Radicados", tot_oficios_unicos)
            mo2.metric("✅ Solicitudes Aprobadas", aprobados_cnt)

            st.markdown("---")

            st.dataframe(
                df_oficios_vista,
                use_container_width=True,
                column_config={
                    "Enlace PDF": st.column_config.LinkColumn(
                        "Soporte PDF",
                        help="Haz clic para abrir el archivo en Google Drive",
                        display_text="📄 Ver PDF"
                    )
                }
            )

            st.download_button(
                label="📥 Descargar Listado de Oficios (.xlsx)",
                data=generar_excel_formateado(df_oficios_vista),
                file_name=f"Historial_Oficios_Radicados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_oficios",
                use_container_width=False,
            )
        else:
            st.info("ℹ️ No se han encontrado registros con número de radicado válidos en el archivo.")
    else:
        st.warning("⚠️ No se detectó la columna 'Radicado' en la hoja Base de datos.")


# =========================================================
# PESTAÑA 7: FINALIZADAS
# =========================================================
with tab_finalizadas:
    st.header("🎉 Acciones Finalizadas")

    col_m1, col_m2 = st.columns([0.24, 1])

    with col_m1:
        st.markdown('<div class="titulo-seccion-finaliz">📅 Cierre Mensual 2026</div>', unsafe_allow_html=True)
        st.markdown('<div class="month-container">', unsafe_allow_html=True)
        for m, cant in conteo_meses.items():
            st.markdown(f'<div class="month-row"><span>{m}</span><div class="month-box">{cant}</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_m2:
        st.markdown('<div class="titulo-seccion-finaliz" style="margin-left: 12px !important;">📋 Tabla de Planes Finalizados</div>', unsafe_allow_html=True)
        df_finalizadas_tabla = df_filtrado[df_filtrado[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy() if col_estado else pd.DataFrame()

        if not df_finalizadas_tabla.empty:
            df_finalizadas_tabla.index = range(1, len(df_finalizadas_tabla) + 1)
            st.dataframe(df_finalizadas_tabla, use_container_width=True)

            st.download_button(
                label="📥 Descargar Solo Finalizadas (.xlsx)",
                data=generar_excel_formateado(df_finalizadas_tabla),
                file_name=f"Acciones_Finalizadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_finalizadas_only",
                use_container_width=False,
            )
        else:
            st.info("ℹ️ No hay acciones con estado 'Finalizado' para los filtros aplicados.")


# =========================================================
# PESTAÑA 8: INFORMES DE AUDITORÍA CON SUB-PESTAÑAS
# =========================================================
with tab_informes:
    st.header("📑 Informes de Auditoría Interna por Vigencia")
    st.markdown("Haz clic en cualquier año para consultar únicamente los informes de esa vigencia específica.")

    if not df_informes_raw.empty:
        df_inf_vista = df_informes_raw.copy()
        
        col_vig_inf = buscar_columna_por_patron(df_inf_vista, ["vigencia"]) or df_inf_vista.columns[0]
        col_nom_inf = buscar_columna_por_patron(df_inf_vista, ["nombre", "informe"]) or df_inf_vista.columns[1]
        col_link_inf = buscar_columna_por_patron(df_inf_vista, ["enlace", "pdf", "link", "drive"]) or df_inf_vista.columns[2]

        df_inf_vista[col_vig_inf] = (
            df_inf_vista[col_vig_inf]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        def asegurar_link(u):
            val = str(u).strip()
            if val and val.lower() not in ["nan", "none", ""] and not val.startswith("http"):
                return f"https://{val}"
            return val

        df_inf_vista[col_link_inf] = df_inf_vista[col_link_inf].apply(asegurar_link)

        vigencias_unicas = sorted([
            v for v in df_inf_vista[col_vig_inf].dropna().unique() 
            if str(v).lower() not in ["nan", "none", ""]
        ])

        if vigencias_unicas:
            nombres_subtabs = [f"📅 Vigencia {v}" if str(v).isdigit() else str(v) for v in vigencias_unicas]
            subtabs = st.tabs(nombres_subtabs)

            for i, vig in enumerate(vigencias_unicas):
                with subtabs[i]:
                    df_sub_vig = df_inf_vista[df_inf_vista[col_vig_inf] == vig].copy().reset_index(drop=True)
                    df_sub_vig.index = range(1, len(df_sub_vig) + 1)
                    
                    st.markdown(f"**Listado de informes de la Vigencia {vig} ({len(df_sub_vig)} informe/s):**")
                    
                    st.dataframe(
                        df_sub_vig,
                        use_container_width=True,
                        column_config={
                            col_link_inf: st.column_config.LinkColumn(
                                "Soporte PDF",
                                help="Haz clic para abrir el archivo del informe en PDF",
                                display_text="📄 Ver PDF"
                            )
                        }
                    )

            st.markdown("---")
            st.download_button(
                label="📥 Descargar Relación Completa de Informes (.xlsx)",
                data=generar_excel_formateado(df_inf_vista),
                file_name=f"Relacion_Informes_Auditoria_Interna_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_informes_pdf_ai_subtabs_exclusivas",
                use_container_width=False,
            )
        else:
            st.info("ℹ️ No hay vigencias válidas registradas en los informes.")
    else:
        st.info("ℹ️ Aún no hay informes registrados en la hoja 'Informes PDF' del archivo Excel.")