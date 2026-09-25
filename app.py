import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai
import io
import os

st.set_page_config(page_title="La Tinka - Avance Mensual NPS", layout="wide", initial_sidebar_state="collapsed")

# --- INYECCIÓN CSS: IDENTIDAD CORPORATIVA Y ANTI-DARK MODE ---
st.markdown("""
<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F5F0D4 !important;
        color: #000000 !important;
    }
    p, label, span, div { color: #000000 !important; }
    h1, h2, h3, h4, h5, h6 { color: #096045 !important; font-weight: 800 !important; }
    label[data-testid="stWidgetLabel"] p { color: #096045 !important; font-weight: bold !important; font-size: 1.05rem !important; }
    div[data-baseweb="select"] > div { background-color: #FFFFFF !important; border: 2px solid #096045 !important; border-radius: 8px !important; color: #000000 !important; }
    div[data-baseweb="select"] * { color: #000000 !important; background-color: #FFFFFF !important; }
    [data-baseweb="popover"], [data-baseweb="menu"], ul[role="listbox"], li[role="option"] { background-color: #FFFFFF !important; color: #000000 !important; }
    li[role="option"] * { color: #000000 !important; background-color: #FFFFFF !important; }
    li[role="option"]:hover, li[role="option"][aria-selected="true"] { background-color: #F5F0D4 !important; }
    li[role="option"]:hover *, li[role="option"][aria-selected="true"] * { color: #096045 !important; background-color: #F5F0D4 !important; font-weight: bold !important; }
    [data-testid="stMetric"] { background-color: #FFFFFF !important; padding: 12px 16px !important; border-radius: 10px !important; border-left: 6px solid #096045 !important; box-shadow: 0px 2px 6px rgba(0,0,0,0.08); }
    [data-testid="stMetricLabel"] p { color: #096045 !important; font-weight: bold !important; }
    [data-testid="stMetricValue"] div { color: #000000 !important; font-weight: 800 !important; }
    div[data-testid="stExpander"] { background-color: #FFFFFF !important; border: 2px solid #096045 !important; border-radius: 10px !important; }
    div[data-testid="stExpander"] summary p { color: #096045 !important; font-weight: bold !important; font-size: 1.05rem !important; }
    div.stButton > button, div.stDownloadButton > button, div.stButton > button *, div.stDownloadButton > button * { background-color: #096045 !important; color: #FFFFFF !important; border-radius: 8px !important; border: none !important; font-weight: 800 !important; font-size: 1rem !important; margin-bottom: 4px !important; }
    div.stButton > button:hover, div.stDownloadButton > button:hover, div.stButton > button:hover *, div.stDownloadButton > button:hover * { background-color: #FF6700 !important; color: #FFFFFF !important; }
    [data-testid="stDataFrame"] { background-color: #FFFFFF !important; border: 1px solid #096045 !important; border-radius: 8px !important; }
    div[data-testid="stCodeBlock"] { background-color: #FFFFFF !important; border: 1px solid #096045 !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=220)
else:
    st.markdown("<h2 style='color:#096045;'>🎯 La Tinka Agente</h2>", unsafe_allow_html=True)

st.title("📊 Control de Avance Mensual NPS")

# --- AUTENTICACIÓN IA ---
api_key = st.secrets.get("GEMINI_API_KEY", None)
st.sidebar.header("⚙️ Configuración")
if not api_key:
    api_key = st.sidebar.text_input("Gemini API Key (AQ...)", type="password")

# --- CARGA DE DATOS ---
uploaded_file = st.sidebar.file_uploader("Actualizar Base Excel (.xlsx)", type=["xlsx"])
file_to_load = uploaded_file if uploaded_file else ("data.xlsx" if os.path.exists("data.xlsx") else None)

if file_to_load:
    xls = pd.ExcelFile(file_to_load)
    
    # Hoja 1: Avance numérico
    df_avance = pd.read_excel(xls, sheet_name=0)
    # Hoja 2: Comentarios cualitativos
    df_comentarios = pd.read_excel(xls, sheet_name=1) if len(xls.sheet_names) > 1 else pd.DataFrame()

    # --- LIMPIEZA BÁSICA ---
    col_cumplimiento = '% NPS Cumplimiento Terminales'
    
    # Llenar vacíos con 0 en la columna de cumplimiento para facilitar cálculos
    if col_cumplimiento in df_avance.columns:
        df_avance[col_cumplimiento] = pd.to_numeric(df_avance[col_cumplimiento], errors='coerce').fillna(0)
    
    # --- FILTROS EN CASCADA ---
    col_mes, col_terr = st.columns([1, 1])

    with col_mes:
        meses_disponibles = df_avance['Mes'].dropna().unique().tolist()
        selected_mes = st.selectbox("📅 Seleccionar Mes:", meses_disponibles)

    df_mes = df_avance[df_avance['Mes'] == selected_mes].copy()

    with col_terr:
        territoriales = df_mes['TERRITORIAL'].dropna().unique()
        selected_terr = st.selectbox("🎯 Seleccionar Líder Territorial:", territoriales)

    df_terr = df_mes[df_mes['TERRITORIAL'] == selected_terr].copy()

    # --- SECCIÓN DE IA: ANÁLISIS DE COMENTARIOS NPS ---
    with st.expander("💡 Generar Análisis Inteligente de Feedback (NPS Global)", expanded=False):
        st.info("Este análisis lee la Hoja 2 del Excel para detectar áreas de oportunidad basadas en comentarios negativos.")
        if st.button("🚀 Analizar Comentarios NPS", type="primary", key="btn_ia"):
            if not api_key:
                st.error("API Key no configurada en los Secrets.")
            elif df_comentarios.empty or 'RESPUESTA' not in df_comentarios.columns:
                st.warning("No se encontró la hoja de comentarios o la columna 'RESPUESTA'.")
            else:
                client = genai.Client(api_key=api_key)
                
                # Extraer muestra de comentarios para la IA
                comentarios_limpios = df_comentarios['RESPUESTA'].dropna().astype(str).tolist()
                muestra_comentarios = "\n- ".join(comentarios_limpios)

                prompt_nps = f"""
                Actúa como un Analista de Experiencia del Cliente (CX). A continuación te presento un listado de comentarios reales de la encuesta NPS del mes.
                
                Tu tarea es enfocarte EXCLUSIVAMENTE en identificar los problemas, fricciones o comentarios NEGATIVOS u OPORTUNIDADES DE MEJORA, ignorando los comentarios positivos (como "buena atención").
                
                Redacta un breve informe estructurado así:
                1. Principales Puntos de Dolor (Agrupa las quejas más comunes en 3 viñetas claras).
                2. Sugerencias de Acción Inmediata (Propón 2 acciones concretas para mejorar estos puntos).
                
                Comentarios a analizar:
                - {muestra_comentarios}
                """
                with st.spinner("Analizando feedback de clientes..."):
                    try:
                        res = client.models.generate_content(model="gemini-3.6-flash", contents=prompt_nps)
                        st.markdown(res.text)
                        st.caption("📋 **Toca el recuadro inferior para copiar el análisis:**")
                        st.code(res.text, language=None)
                    except Exception as e:
                        st.error(f"Error al conectar con la IA: {e}")
    st.divider()

    # --- FILTRO SECUNDARIO Y MÉTRICAS ---
    regionales = ["Todos"] + df_terr['REGIONAL'].dropna().unique().tolist()
    selected_reg = st.selectbox("👤 Filtrar por Regional:", regionales)

    df_disp = df_terr.copy()
    if selected_reg != "Todos":
        df_disp = df_disp[df_disp['REGIONAL'] == selected_reg]

    # Cálculos
    total_universo = len(df_disp)
    if col_cumplimiento in df_disp.columns:
        completados = df_disp[df_disp[col_cumplimiento] > 0].shape[0]
    else:
        completados = 0
        
    pendientes = total_universo - completados
    porcentaje_avance = (completados / total_universo * 100) if total_universo > 0 else 0

    # Tarjetas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Terminales", total_universo)
    c2.metric("NPS Completado", completados)
    c3.metric("Terminales Pendientes", pendientes, delta="-Atención Requerida", delta_color="inverse")
    c4.metric("% de Avance", f"{porcentaje_avance:.1f}%")

    st.divider()

    # --- TABLA DE PENDIENTES ---
    st.subheader("📋 Detalle de Terminales Pendientes")
    
    # Filtrar SOLO los que tienen cumplimiento 0 o vacío
    if col_cumplimiento in df_disp.columns:
        df_pendientes = df_disp[df_disp[col_cumplimiento] == 0].copy()
    else:
        df_pendientes = df_disp.copy()

    st.dataframe(df_pendientes, use_container_width=True, height=300)

    # --- BOTONES DE EXPORTACIÓN ---
    col_btn1, col_btn2 = st.columns([1, 4])
    
    with col_btn1:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_pendientes.to_excel(writer, index=False, sheet_name='Pendientes_NPS')
        excel_data = output.getvalue()
        
        st.download_button(
            label=f"📥 Descargar Pendientes ({len(df_pendientes)})",
            data=excel_data,
            file_name=f"Pendientes_NPS_{selected_terr}_{selected_mes}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    with col_btn2:
        if st.button(f"📋 Copiar datos para WhatsApp", key="btn_copiar"):
            if not df_pendientes.empty:
                filas = []
                # Intentamos extraer Terminal y Regional para el listado de WhatsApp
                col_t = 'TERMINAL' if 'TERMINAL' in df_pendientes.columns else df_pendientes.columns[0]
                col_r = 'REGIONAL' if 'REGIONAL' in df_pendientes.columns else df_pendientes.columns[1]
                
                for _, row in df_pendientes.iterrows():
                    vt = str(row[col_t])
                    vr = str(row[col_r])
                    filas.append(f"Regional: {vr} | Terminal: {vt}")
                
                texto_copia = "\n".join(filas)
                st.caption("📋 **Copia la lista de terminales pendientes abajo:**")
                st.code(texto_copia, language=None)
            else:
                st.warning("No hay terminales pendientes para copiar.")

else:
    st.warning("⚠️ Sube el archivo base de NPS para visualizar el dashboard.")
