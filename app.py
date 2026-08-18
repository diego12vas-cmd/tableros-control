from datetime import date, datetime
import io
import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS COMPACTOS & RESPONSIVOS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Tablero de Control - Planes de Acción Auditoría Interna",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
        /* 0. Ocultar menús nativos y marcas de Streamlit para usuarios finales */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppDeployButton {display:none !important;}
        [data-testid="stHeader"] {display:none !important;}
        [data-testid="stToolbar"] {display:none !important;}
        [data-testid="stDecoration"] {display:none !important;}
        [data-testid="stStatusWidget"] {display:none !important;}

        /* 1. Reducir la altura del header transparente de Streamlit */
        header[data-testid="stHeader"] {
            height: 2.5rem !important;
            background: transparent !important;
        }

        /* 2. Dar espacio superior suficiente para el título principal */
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 1rem !important;
        }

        /* 3. Estilo del título principal */
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

        /* --- ALINEACIÓN Y ESPACIADO ROBUSTO PARA FINALIZADAS --- */
        [data-testid="stHorizontalBlock"] {
            align-items: flex-start !important;
        }

        /* Espacio superior para que la tabla no se monte en el título */
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

        /* --- CONTROL DE ESPACIO DE LA LISTA DE MESES --- */
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

        /* --- AJUSTES DE DISEÑO RESPONSIVO PARA MÓVILES (CELULARES) --- */
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
        "TABLERO_PA_AI.xlsx",
        "TABLERO_PA_AI.xlsm",
        "TABLERO_PA_I.xlsx",
        "TABLERO_PA_I.xlsm",
        os.path.join(dir_script, "TABLERO_PA_AI.xlsx"),
        os.path.join(dir_script, "TABLERO_PA_AI.xlsm"),
        os.path.join(dir_script, "TABLERO_PA_I.xlsx"),
        os.path.join(dir_script, "TABLERO_PA_I.xlsm"),
        os.path.join(dir_padre, "TABLERO_PA_AI.xlsx"),
        os.path.join(dir_padre, "TABLERO_PA_AI.xlsm"),
    ]

    for ruta in rutas_candidatas:
        if os.path.exists(ruta):
            return ruta

    for folder in [dir_script, dir_padre]:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.endswith((".xlsm", ".xlsx")) and ("TABLERO" in file.upper() or "PA_" in file.upper()) and not file.startswith("~$"):
                    return os.path.join(folder, file)

    return "TABLERO_PA_AI.xlsx"


EXCEL_PATH = buscar_excel_inteligente()


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
# CARGA DE DATOS (TIEMPO REAL)
# ---------------------------------------------------------
def cargar_datos():
    if not os.path.exists(EXCEL_PATH):
        st.error(f"No se encontró el archivo Excel en la ruta: {EXCEL_PATH}")
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(EXCEL_PATH)
        sheet_b = (
            "Base de datos"
            if "Base de datos" in xls.sheet_names
            else ("Base de Datos" if "Base de Datos" in xls.sheet_names else xls.sheet_names[0])
        )
        df_base = pd.read_excel(xls, sheet_name=sheet_b)
        df_base.columns = [str(c).strip() for c in df_base.columns]

        for col in df_base.columns:
            if df_base[col].dtype == "object":
                df_base[col] = df_base[col].astype(str).str.strip()

        return df_base
    except Exception as e:
        st.error(f"Error al cargar el archivo Excel: {e}")
        return pd.DataFrame()


df_raw = cargar_datos()

if df_raw.empty:
    st.stop()


# ---------------------------------------------------------
# DETECCIÓN FLEXIBLE DE COLUMNAS
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


col_estado = "Estado" if "Estado" in df_raw.columns else buscar_columna_por_patron(df_raw, ["estado"])
col_responsable = buscar_columna_por_patron(df_raw, ["area responsable", "responsable", "dependencia"])
col_auditor_resp = buscar_columna_por_patron(df_raw, ["auditor responsable", "auditor"])
col_plan_auditoria = buscar_columna_por_patron(df_raw, ["plan de auditoria", "plan auditoria"])
col_auditoria_esp = buscar_columna_por_patron(df_raw, ["auditoria especifica", "auditoria"])
col_riesgo = "Riesgo" if "Riesgo" in df_raw.columns else buscar_columna_por_patron(df_raw, ["riesgo"])

col_hallazgo = "Titulo del Hallazgo" if "Titulo del Hallazgo" in df_raw.columns else buscar_columna_por_patron(df_raw, ["titulo del hallazgo", "hallazgo", "id"])
col_plan_accion = "Plan de Acción" if "Plan de Acción" in df_raw.columns else buscar_columna_por_patron(df_raw, ["plan de accion", "accion", "compromiso"])
col_fecha_cierre = "Fecha Estimada de Cierre" if "Fecha Estimada de Cierre" in df_raw.columns else buscar_columna_por_patron(df_raw, ["fecha estimada de cierre", "vencimiento", "cierre", "fecha cierre"])
col_fecha_cierre_aud = "Fecha cierre x Auditoría" if "Fecha cierre x Auditoría" in df_raw.columns else buscar_columna_por_patron(df_raw, ["fecha cierre x auditoria", "cierre x auditoria"])
col_obs_audit = "Observación Auditoría" if "Observación Auditoría" in df_raw.columns else (buscar_columna_por_patron(df_raw, ["observacion auditoria", "observacion"]) or "Observación Auditoría")

col_a5 = "Alerta 5" if "Alerta 5" in df_raw.columns else buscar_columna_por_patron(df_raw, ["alerta 5"])
col_a10 = "Alerta 10" if "Alerta 10" in df_raw.columns else buscar_columna_por_patron(df_raw, ["alerta 10"])
col_a20 = "Alerta 20" if "Alerta 20" in df_raw.columns else buscar_columna_por_patron(df_raw, ["alerta 20"])
col_a30 = "Alerta 30" if "Alerta 30" in df_raw.columns else buscar_columna_por_patron(df_raw, ["alerta 30"])

if col_estado:
    df_raw[col_estado] = df_raw[col_estado].astype(str).str.capitalize()

# ---------------------------------------------------------
# BARRA LATERAL: FILTROS MULTISELECT (EXCLUYENDO FINALIZADAS)
# ---------------------------------------------------------
st.sidebar.title("🔍 Filtros del Tablero")

df_filtrado = df_raw.copy()

if col_estado:
    estados_vals = sorted([
        e for e in df_raw[col_estado].dropna().unique() 
        if str(e).lower() not in ["nan", "none", ""] and not re.search(r"finaliz|cerrad", str(e), re.IGNORECASE)
    ])
    with st.sidebar.expander("📌 Estado del compromiso", expanded=True):
        estado_sel = st.multiselect("Seleccione uno o varios Estados:", options=estados_vals, default=[], key="multi_estado_ai")
    if estado_sel:
        df_filtrado = df_filtrado[df_filtrado[col_estado].isin(estado_sel)]

if col_responsable:
    resp_vals = sorted(list(set([r for r in df_raw[col_responsable].dropna().unique() if str(r).lower() not in ["nan", "none", ""]])))
    with st.sidebar.expander("👤 Responsables", expanded=False):
        resp_sel = st.multiselect("Seleccione uno o varios Responsables:", options=resp_vals, default=[], key="multi_resp_ai")
    if resp_sel:
        df_filtrado = df_filtrado[df_filtrado[col_responsable].isin(resp_sel)]

if col_auditor_resp:
    aud_vals = sorted(list(set([a for a in df_raw[col_auditor_resp].dropna().unique() if str(a).lower() not in ["nan", "none", ""]])))
    with st.sidebar.expander("👨‍💼 Auditor Responsable", expanded=False):
        auditor_sel = st.multiselect("Seleccione uno o varios Auditores:", options=aud_vals, default=[], key="multi_auditor_ai")
    if auditor_sel:
        df_filtrado = df_filtrado[df_filtrado[col_auditor_resp].isin(auditor_sel)]

if col_plan_auditoria:
    plan_vals = sorted(list(set([p for p in df_raw[col_plan_auditoria].dropna().unique() if str(p).lower() not in ["nan", "none", ""]])))
    with st.sidebar.expander("📁 Plan Auditoría / Vigencia", expanded=False):
        plan_sel = st.multiselect("Seleccione uno o varios Planes:", options=plan_sel, default=[], key="multi_plan_ai") if 'plan_sel' in locals() and plan_sel else st.multiselect("Seleccione uno o varios Planes:", options=plan_vals, default=[], key="multi_plan_ai")
    if plan_sel:
        df_filtrado = df_filtrado[df_filtrado[col_plan_auditoria].isin(plan_sel)]

if col_auditoria_esp:
    esp_vals = sorted(list(set([e for e in df_raw[col_auditoria_esp].dropna().unique() if str(e).lower() not in ["nan", "none", ""]])))
    with st.sidebar.expander("🔬 Auditoría Específica", expanded=False):
        esp_sel = st.multiselect("Seleccione una o varias Auditorías:", options=esp_vals, default=[], key="multi_esp_ai")
    if esp_sel:
        df_filtrado = df_filtrado[df_filtrado[col_auditoria_esp].isin(esp_sel)]


# ---------------------------------------------------------
# CÁLCULO DE MESES PARA PESTAÑA FINALIZADAS
# ---------------------------------------------------------
meses_es_map = {1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAY", 6: "JUN", 7: "JUL", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"}
conteo_meses = {m: 0 for m in meses_es_map.values()}

if col_fecha_cierre_aud and col_fecha_cierre_aud in df_filtrado.columns:
    df_fin = df_filtrado[df_filtrado[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy() if col_estado else pd.DataFrame()
    if not df_fin.empty:
        fechas_dt = pd.to_datetime(df_fin[col_fecha_cierre_aud], errors="coerce")
        for f in fechas_dt.dropna():
            m_num = f.month
            if m_num in meses_es_map:
                conteo_meses[meses_es_map[m_num]] += 1


# ---------------------------------------------------------
# MÉTRICAS Y FIGURAS EXCLUYENDO FINALIZADAS
# ---------------------------------------------------------
df_activos = df_filtrado[~df_filtrado[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy() if col_estado else df_filtrado.copy()

if col_hallazgo and col_hallazgo in df_activos.columns:
    hallazgos_limpios = df_activos[col_hallazgo].dropna().astype(str).str.strip().str.upper()
    hallazgos_validos = hallazgos_limpios[~hallazgos_limpios.isin(["", "NAN", "NONE", "0"])]
    total_hallazgos_unicos_pendientes = hallazgos_validos.nunique()
else:
    total_hallazgos_unicos_pendientes = len(df_activos)

r_alto = df_activos[col_riesgo].astype(str).str.contains("Alto", case=False, na=False).sum() if col_riesgo else 0
r_medio = df_activos[col_riesgo].astype(str).str.contains("Medio", case=False, na=False).sum() if col_riesgo else 0
r_bajo = df_activos[col_riesgo].astype(str).str.contains("Bajo", case=False, na=False).sum() if col_riesgo else 0

abiertos = df_filtrado[col_estado].astype(str).str.contains("Abiert", case=False, na=False).sum() if col_estado else 0
vencidos = df_filtrado[col_estado].astype(str).str.contains("Vencid", case=False, na=False).sum() if col_estado else 0
sin_definir = df_filtrado[col_estado].astype(str).str.contains("Sin definir", case=False, na=False).sum() if col_estado else 0

total_planes_pendientes = abiertos + vencidos + sin_definir

# --- BARRAS ---
max_val = max([abiertos, vencidos, sin_definir])
df_bar = pd.DataFrame({"Estado": ["Abiertos", "Vencidos", "Sin definir"], "Cantidad": [abiertos, vencidos, sin_definir]})

fig_bar = px.bar(df_bar, x="Estado", y="Cantidad", text="Cantidad", color="Estado", color_discrete_map={"Abiertos": "#58C57A", "Vencidos": "#FF5252", "Sin definir": "#FFB366"})
fig_bar.update_traces(textposition="outside", textfont=dict(size=12, color="var(--text-color)", family="Arial"), cliponaxis=False)
fig_bar.update_layout(
    autosize=True,
    showlegend=False, 
    height=180, 
    margin=dict(t=25, b=5, l=5, r=5), 
    xaxis_title=None, 
    yaxis_title=None, 
    xaxis=dict(tickfont=dict(size=11, color="var(--text-color)", family="Arial")), 
    yaxis=dict(showticklabels=False, range=[0, max_val * 1.25 if max_val > 0 else 10]), 
    paper_bgcolor="rgba(0,0,0,0)", 
    plot_bgcolor="rgba(0,0,0,0)"
)

# --- LAS 2 DONAS ---
# 1. En Tiempo (Abiertos)
pct_abiertos = round((abiertos / total_planes_pendientes) * 100) if total_planes_pendientes > 0 else 0
colors_abiertos = ["#00B050" if i < (pct_abiertos / 5) else "#E0E0E0" for i in range(20)]

fig_dona_abiertos = go.Figure(data=[
    go.Pie(values=[1]*20, hole=0.68, marker_colors=colors_abiertos, marker_line=dict(color="#FFFFFF", width=2), textinfo="none", hoverinfo="none")
])
fig_dona_abiertos.add_annotation(text=f"<b>{pct_abiertos}%</b>", x=0.5, y=0.5, font=dict(size=28, color="var(--text-color)"), showarrow=False)
fig_dona_abiertos.update_layout(autosize=True, showlegend=False, height=145, margin=dict(t=2, b=2, l=2, r=2), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

# 2. Vencidos
pct_vencidos = round((vencidos / total_planes_pendientes) * 100) if total_planes_pendientes > 0 else 0
colors_vencidos = ["#FF5252" if i < (pct_vencidos / 5) else "#E0E0E0" for i in range(20)]

fig_dona_vencidos = go.Figure(data=[
    go.Pie(values=[1]*20, hole=0.68, marker_colors=colors_vencidos, marker_line=dict(color="#FFFFFF", width=2), textinfo="none", hoverinfo="none")
])
fig_dona_vencidos.add_annotation(text=f"<b>{pct_vencidos}%</b>", x=0.5, y=0.5, font=dict(size=28, color="var(--text-color)"), showarrow=False)
fig_dona_vencidos.update_layout(autosize=True, showlegend=False, height=145, margin=dict(t=2, b=2, l=2, r=2), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")


# ---------------------------------------------------------
# DEFINICIÓN DE PESTAÑAS
# ---------------------------------------------------------
tab_principal, tab_metricas, tab_alertas, tab_finalizadas = st.tabs([
    "📊 Tablero Principal",
    "📈 Métricas de Cumplimiento",
    "🚨 Alertas y Edición Directa",
    "🎉 Finalizadas",
])

# =========================================================
# PESTAÑA 1: TABLERO PRINCIPAL
# =========================================================
with tab_principal:
    c2, c3, c4 = st.columns([2.5, 2.5, 2.0])

    # --- COLUMNA 1: HALLAZGOS Y PLANES ---
    with c2:
        st.markdown('<div class="block-header">Total Hallazgos Pendientes</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-box" style="background-color:#4B92DB; font-size:1.3rem; height:34px; line-height:26px;">{total_hallazgos_unicos_pendientes}</div>', unsafe_allow_html=True)

        st.markdown('<div class="block-header" style="font-size:0.75rem; margin-top:2px;">Detalle por Nivel de Riesgo</div>', unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown('<div class="block-header" style="font-size:0.65rem; text-transform:none;">Riesgo Alto</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-box" style="background-color:#FFBF00;">{r_alto}</div>', unsafe_allow_html=True)
        with r2:
            st.markdown('<div class="block-header" style="font-size:0.65rem; text-transform:none;">Riesgo Medio</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-box" style="background-color:#FFFF00;">{r_medio}</div>', unsafe_allow_html=True)
        with r3:
            st.markdown('<div class="block-header" style="font-size:0.65rem; text-transform:none;">Riesgo Bajo</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-box" style="background-color:#00B050;">{r_bajo}</div>', unsafe_allow_html=True)

        st.markdown('<div class="block-header" style="font-size:0.78rem;">Planes de Acción Pendientes</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-box" style="background-color:#00B050; height:36px; line-height:26px; font-size:1.4rem; margin-bottom:8px;">{total_planes_pendientes}</div>', unsafe_allow_html=True)

        st.markdown('<div class="block-header" style="font-size:0.78rem;">Detalle de Estados Pendientes</div>', unsafe_allow_html=True)
        e1, e2, e3 = st.columns(3)
        with e1:
            st.markdown('<div class="block-header" style="font-size:0.7rem; text-transform:none;">Abiertos</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-box" style="background-color:#58C57A; font-size:1.1rem; padding:6px;">{abiertos}</div>', unsafe_allow_html=True)
        with e2:
            st.markdown('<div class="block-header" style="font-size:0.7rem; text-transform:none;">Vencidos</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-box" style="background-color:#FF5252; color:#FFFFFF; font-size:1.1rem; padding:6px;">{vencidos}</div>', unsafe_allow_html=True)
        with e3:
            st.markdown('<div class="block-header" style="font-size:0.7rem; text-transform:none;">Sin definir</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-box" style="background-color:#FFB366; font-size:1.1rem; padding:6px;">{sin_definir}</div>', unsafe_allow_html=True)

    # --- COLUMNA 2: ALERTAS Y BARRAS ---
    with c3:
        st.markdown('<div class="block-header">Acciones próximas a vencer</div>', unsafe_allow_html=True)

        def obtener_valor_alerta(col_name):
            if col_name and col_name in df_filtrado.columns:
                s = pd.to_numeric(df_filtrado[col_name], errors="coerce").fillna(0)
                cant = (s > 0).sum()
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
                    <div class="alert-item-label"><span>5 días</span><span>🔴</span></div>
                    <div class="alert-val-box">{val_5}</div>
                </div>
                <div class="alert-row-compact">
                    <div class="alert-item-label"><span>10 días</span><span>🟡</span></div>
                    <div class="alert-val-box">{val_10}</div>
                </div>
                <div class="alert-row-compact">
                    <div class="alert-item-label"><span>20 días</span><span>🟢</span></div>
                    <div class="alert-val-box">{val_20}</div>
                </div>
                <div class="alert-row-compact">
                    <div class="alert-item-label"><span>30 días</span><span>🔵</span></div>
                    <div class="alert-val-box">{val_30}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="block-header" style="margin-top:2px;">Distribución de Planes Pendientes</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_bar, use_container_width=True, key="fig_bar_ai")

    # --- COLUMNA 3: DONAS ---
    with c4:
        st.markdown('<div class="block-header">Porcentaje de Acciones Pendientes</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="block-header" style="font-size:0.75rem; text-transform:none; margin-bottom:0px; color:#00B050;">🟢 En tiempo (Abiertos)</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_dona_abiertos, use_container_width=True, key="fig_dona_abiertos_ai")
        
        st.markdown('<div class="block-header" style="font-size:0.75rem; text-transform:none; margin-bottom:0px; color:#FF5252;">🔴 Vencidos</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_dona_vencidos, use_container_width=True, key="fig_dona_vencidos_ai")

    st.markdown("---")
    
    # --- FILTRO DESPLEGABLE EN EL ENCABEZADO DE LA TABLA ---
    col_t1, col_t2 = st.columns([2.5, 1.5])
    with col_t1:
        st.subheader("📋 Detalle General de Compromisos Pendientes")
    with col_t2:
        cat_opciones = ["(Mostrar Todos)"]
        if col_plan_auditoria and col_plan_auditoria in df_activos.columns:
            cat_opciones += sorted([str(x) for x in df_activos[col_plan_auditoria].dropna().unique() if str(x).strip()])
        cat_sel = st.selectbox("⚡ Filtrar vista detallada por categoría:", options=cat_opciones, key="filtro_categoria_tabla_ai")

    df_tabla_ai = df_activos.copy()
    if cat_sel != "(Mostrar Todos)" and col_plan_auditoria and col_plan_auditoria in df_tabla_ai.columns:
        df_tabla_ai = df_tabla_ai[df_tabla_ai[col_plan_auditoria].astype(str) == cat_sel]

    df_tabla_ai.index = range(1, len(df_tabla_ai) + 1)
    st.dataframe(df_tabla_ai, use_container_width=True)

    st.download_button(
        label="📥 Descargar Excel (.xlsx)",
        data=generar_excel_formateado(df_tabla_ai),
        file_name=f"Detalle_Auditoria_Interna_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )


# =========================================================
# PESTAÑA 2: MÉTRICAS DE CUMPLIMIENTO
# =========================================================
with tab_metricas:
    st.header("📈 Resumen de Estado y Desempeño")
    st.markdown("Vista general del avance de compromisos por área y plan de auditoría.")

    comp_vencidos_pend = df_activos[col_estado].astype(str).str.contains("Vencid", case=False, na=False).sum() if col_estado else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Planes de Acción Pendientes", total_planes_pendientes)
    m2.metric("🔴 Compromisos Vencidos", comp_vencidos_pend, delta=f"{(comp_vencidos_pend/total_planes_pendientes*100):.1f}% de pendientes" if total_planes_pendientes > 0 else "0%", delta_color="inverse")
    m3.metric("🎯 Tasa Global de Cierre", f"{pct_abiertos}%", delta="Objetivo: 100%")

    st.markdown("---")
    st.subheader("👥 Distribución de Compromisos Pendientes por Área / Dependencia")
    st.dataframe(df_activos, use_container_width=True)


# =========================================================
# PESTAÑA 3: ALERTAS CRÍTICAS Y EDICIÓN EN MEMORIA
# =========================================================
with tab_alertas:
    st.header("🚨 Alertas Críticas y Edición Directa")
    st.markdown("Gestión de casos graves (vencimientos mayores a 30 días) y registro de modificaciones.")

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

    st.markdown("<br>", unsafe_allow_html=True)

    if not df_criticos_30.empty:
        df_criticos_30.index = range(1, len(df_criticos_30) + 1)
        st.subheader("📋 Tabla de Compromisos Críticos")
        st.dataframe(df_criticos_30, use_container_width=True)
    else:
        st.success("🎉 ¡Excelente! No existen planes de acción con mora de 30 días o más.")

    st.markdown("---")
    st.subheader("✏️ Establecer Compromisos Auditoría Interna")
    st.caption("Filtra por Plan de Auditoría y Estado. Luego selecciona el Hallazgo a editar.")

    df_edicion_temp = df_raw.copy()

    col_f_aud, col_f_estado = st.columns(2)

    opciones_auditoria = ["(Todas)"]
    if col_plan_auditoria and col_plan_auditoria in df_raw.columns:
        opciones_auditoria += sorted([str(x).strip() for x in df_raw[col_plan_auditoria].dropna().unique() if str(x).strip()])
    with col_f_aud:
        aud_seleccionada = st.selectbox("1. Filtrar por Plan de Auditoría:", options=opciones_auditoria, key="f_aud_edit_ai")

    if aud_seleccionada != "(Todas)":
        df_edicion_temp = df_edicion_temp[df_edicion_temp[col_plan_auditoria].astype(str).str.strip().str.lower() == aud_seleccionada.strip().lower()]

    opciones_estado_f = ["(Todos)"]
    if col_estado and col_estado in df_edicion_temp.columns:
        opciones_estado_f += sorted([str(x).strip() for x in df_edicion_temp[col_estado].dropna().unique() if str(x).strip()])
    with col_f_estado:
        estado_filtro_sel = st.selectbox("2. Filtrar por Estado:", options=opciones_estado_f, key="f_estado_edit_ai")

    if estado_filtro_sel != "(Todos)":
        df_edicion_temp = df_edicion_temp[df_edicion_temp[col_estado].astype(str).str.strip().str.lower() == estado_filtro_sel.strip().lower()]

    opciones_hallazgos = df_edicion_temp[col_hallazgo].dropna().unique() if col_hallazgo and not df_edicion_temp.empty else []

    if len(opciones_hallazgos) == 0:
        st.warning("⚠️ No se encontraron hallazgos con la combinación exacta de los filtros seleccionados.")
    else:
        id_sel = st.selectbox("3. Seleccione el Registro / Hallazgo a Modificar:", options=opciones_hallazgos, key="f_hallazgo_sel_ai")

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
            nueva_fecha_cierre = st.date_input("Nueva Fecha de Cierre / Terminación:", value=fecha_def_obj, key=f"in_fecha_{idx_exacto_raw}_ai")
            lista_estados = ["Abierta", "Vencida", "Finalizada", "Sin plan de acción"]
            if est_actual_val and est_actual_val not in lista_estados:
                lista_estados.append(est_actual_val)
            idx_est_def = lista_estados.index(est_actual_val) if est_actual_val in lista_estados else 0
            nuevo_estado = st.selectbox("Estado del Compromiso:", options=lista_estados, index=idx_est_def, key=f"in_estado_{idx_exacto_raw}_ai")
            nuevo_responsable = st.text_input("Responsable Asignado:", value=resp_actual_val, key=f"in_resp_{idx_exacto_raw}_ai")

        with col_f2:
            nuevo_plan_accion = st.text_area("Plan de Acción / Compromiso:", value=plan_actual_val, height=100, key=f"in_plan_{idx_exacto_raw}_ai")
            obs_usuario = st.text_area("Observaciones adicionales / Notas:", value="", height=80, key=f"in_obs_{idx_exacto_raw}_ai")

        btn_guardar = st.button("➕ Registrar Cambio", type="primary", use_container_width=False, key=f"btn_save_{idx_exacto_raw}_ai")

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

            if "lote_filas_modificadas_ai" not in st.session_state:
                st.session_state["lote_filas_modificadas_ai"] = {}

            st.session_state["lote_filas_modificadas_ai"][id_sel] = fila_modificada

            st.toast("✅ ¡Registro agregado exitosamente!", icon="🎉")

    # ---------------------------------------------------------
    # DESCARGA DE REGISTROS MODIFICADOS EN EL DÍA
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("📥 Descargar Registros Modificados en el Día")

    if "lote_filas_modificadas_ai" not in st.session_state:
        st.session_state["lote_filas_modificadas_ai"] = {}

    if "limpiar_key_ai" not in st.session_state:
        st.session_state["limpiar_key_ai"] = 0

    version_key = st.session_state["limpiar_key_ai"]

    cant_modificados = len(st.session_state["lote_filas_modificadas_ai"])
    lista_acumulada = list(st.session_state["lote_filas_modificadas_ai"].values())

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
                file_name=f"Planes_Modificados_Auditoria_Interna_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"btn_download_lote_ai_{version_key}",
                use_container_width=False,
            )
        else:
            st.button("📥 Descargar Modificaciones (0)", disabled=True, use_container_width=False, key=f"btn_download_disabled_ai_{version_key}")

    with col_btn_clear:
        if st.button("🗑️ Limpiar Historial", type="secondary", use_container_width=False, disabled=(cant_modificados == 0), key=f"btn_clear_historial_ai_{version_key}"):
            st.session_state["lote_filas_modificadas_ai"] = {}
            st.session_state["limpiar_key_ai"] += 1
            st.rerun()


# =========================================================
# PESTAÑA 4: FINALIZADAS
# =========================================================
with tab_finalizadas:
    st.header("🎉 Acciones Finalizadas Auditoría Interna")
    st.markdown("Consulta y métricas exclusivas de las acciones que han completado su ciclo.")

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
                file_name=f"Acciones_Finalizadas_Auditoria_Interna_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_finalizadas_only_ai",
                use_container_width=False,
            )
        else:
            st.info("ℹ️ No hay acciones con estado 'Finalizado' para los filtros aplicados.")