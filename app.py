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
        date_cell_format =