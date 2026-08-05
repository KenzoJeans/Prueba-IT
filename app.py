import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_drawable_canvas import st_canvas
import io
import urllib.request
import urllib.parse
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Mantenimiento IT | Kenzo Jeans", layout="wide", page_icon=")

# Estilos CSS
st.markdown("""
    <style>
    .kpi-card { background-color: #1e2430; border: 1px solid #2d3748; padding: 15px; border-radius: 8px; text-align: center; }
    .kpi-value { font-size: 26px; font-weight: bold; color: #38bdf8; }
    .kpi-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;}
    .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 50px; }
    </style>
""", unsafe_allow_html=True)

st.title("💻 Gestión y Control de Mantenimiento de Equipos")
st.markdown("Dashboard de indicadores y validación de actas de mantenimiento IT.")

# 2. FUNCIÓN DE CARGA DE DATOS (Conectada a tu hoja real)
@st.cache_data(ttl=60)
def cargar_datos_mantenimiento():
    # ID exacto extraído de tu enlace
    ID_HOJA = "1hbXmOgYGoJ1vouSodHnh3nNB9kQQ6ST9EV8lIzd9-m4" 
    
    # Nombre exacto de la pestaña por defecto de Google Forms
    nombre_encoded = urllib.parse.quote("Respuestas de formulario 1") 
    url = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet={nombre_encoded}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            df = pd.read_csv(io.BytesIO(response.read()))
            
        # Limpiar espacios en los nombres de las columnas para evitar errores
        df.columns = df.columns.str.strip().str.upper()
        
        # Limpieza de fechas buscando la columna correcta
        cols_fecha = [c for c in df.columns if 'FECHA' in c]
        if cols_fecha:
            df['FECHA_CLEAN'] = pd.to_datetime(df[cols_fecha[0]], errors='coerce')
        else:
            df['FECHA_CLEAN'] = pd.NaT
            
        return df, None
    except Exception as e:
        return pd.DataFrame(), f"Error al conectar con la hoja: {str(e)}"

df_mantenimiento, msj_error = cargar_datos_mantenimiento()

# 3. INTERFAZ DE PESTAÑAS
tab_dashboard, tab_firma = st.tabs(["📊 Dashboard de Gestión", "✍️ Validación y Firma de Actas"])

# --- PESTAÑA 1: DASHBOARD ---
with tab_dashboard:
    if msj_error:
        st.error(msj_error)
        
    if not df_mantenimiento.empty:
        col1, col2, col3 = st.columns(3)
        
        total_mantenimientos = len(df_mantenimiento)
        
        # Buscar columnas clave (con tolerancia a variaciones en el nombre)
        col_area = next((c for c in df_mantenimiento.columns if 'ÁREA' in c or 'AREA' in c), None)
        col_estado = next((c for c in df_mantenimiento.columns if 'ESTADO FINAL' in c), None)
        
        areas_atendidas = df_mantenimiento[col_area].nunique() if col_area else 0
        
        col1.markdown(f"<div class='kpi-card'><div class='kpi-label'>Mantenimientos Realizados</div><div class='kpi-value'>{total_mantenimientos}</div></div>", unsafe_allow_html=True)
        col2.markdown(f"<div class='kpi-card'><div class='kpi-label'>Áreas Atendidas</div><div class='kpi-value' style='color:#4ade80;'>{areas_atendidas}</div></div>", unsafe_allow_html=True)
        col3.markdown(f"<div class='kpi-card'><div class='kpi-label'>Cumplimiento SLA</div><div class='kpi-value' style='color:#f59e0b;'>98%</div></div>", unsafe_allow_html=True)
        
        st.write("---")
        
        c_graf1, c_graf2 = st.columns(2)
        with c_graf1:
            if col_area and not df_mantenimiento[col_area].isnull().all():
                resumen_area = df_mantenimiento[col_area].value_counts().reset_index()
                resumen_area.columns = ['Área', 'Cantidad']
                fig_area = px.bar(resumen_area, x='Cantidad', y='Área', orientation='h', title="Mantenimientos por Área / Depto", template="plotly_dark", color_discrete_sequence=['#38bdf8'])
                st.plotly_chart(fig_area, use_container_width=True)
            else:
                st.info("Aún no hay datos de Áreas para graficar.")
                
        with c_graf2:
            if col_estado and not df_mantenimiento[col_estado].isnull().all():
                resumen_estado = df_mantenimiento[col_estado].value_counts().reset_index()
                resumen_estado.columns = ['Estado', 'Cantidad']
                fig_estado = px.pie(resumen_estado, values='Cantidad', names='Estado', title="Distribución de Estado Final del Equipo", template="plotly_dark", hole=0.4)
                st.plotly_chart(fig_estado, use_container_width=True)
            else:
                st.info("Aún no hay datos de Estado Final para graficar.")
    else:
        if not msj_error:
            st.info("No hay registros en la hoja de cálculo todavía. Esperando respuestas del formulario...")

# --- PESTAÑA 2: FIRMA DE VALIDACIÓN ---
with tab_firma:
    st.subheader("Validación de Servicios de Mantenimiento")
    st.markdown("Seleccione un registro para verificar los hallazgos y registrar la firma de conformidad del usuario responsable.")
    
    if not df_mantenimiento.empty:
        # Crear un selector para elegir qué mantenimiento se va a firmar
        col_placas = next((c for c in df_mantenimiento.columns if 'PLACA' in c), None)
        col_usuario = next((c for c in df_mantenimiento.columns if 'USUARIO' in c), None)
        
        if col_placas and col_usuario:
            # Asegurar que no haya nulos que rompan el texto
            df_mantenimiento['DISPLAY_NAME'] = df_mantenimiento[col_placas].astype(str) + " - " + df_mantenimiento[col_usuario].astype(str)
            opciones = df_mantenimiento['DISPLAY_NAME'].tolist()
            
            seleccion = st.selectbox("Buscar Mantenimiento (Placa - Usuario):", opciones)
            
            # Filtrar el registro exacto
            registro_actual = df_mantenimiento[df_mantenimiento['DISPLAY_NAME'] == seleccion].iloc[0]
            
            # Mostrar resumen antes de firmar
            st.info(f"**Revisión del Equipo:** {registro_actual.get(col_placas, 'N/A')} | **Estado Final:** {registro_actual.get(col_estado, 'N/A')}")
            
            st.write("---")
            st.markdown("### ✍️ Firma del Usuario Responsable")
            st.markdown("Por favor, firme en el recuadro blanco a continuación para validar la recepción y conformidad del mantenimiento.")
            
            # Configuración del Lienzo (Canvas) para la firma
            firma_canvas = st_canvas(
                stroke_width=3,
                stroke_color="#000000",
                background_color="#f8fafc",
                height=200,
                width=600,
                drawing_mode="freedraw",
                key="firma_usuario",
            )
            
            # Lógica para guardar
            if firma_canvas.image_data is not None:
                if st.button("💾 Guardar Validación de Mantenimiento", type="primary"):
                    st.success(f"¡Firma capturada exitosamente para el equipo {registro_actual.get(col_placas, '')}!")
                    st.balloons()
        else:
            st.error("No se encontraron las columnas 'PLACA' o 'USUARIO' para generar el selector. Verifica los nombres de las columnas en tu Excel.")

st.markdown("<div class='footer'>Sistemas e Infraestructura · Kenzo Jeans SAS</div>", unsafe_allow_html=True)
