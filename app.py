import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_drawable_canvas import st_canvas
import io
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import base64
import json
import requests
from PIL import Image

# 1. Configuración de la página
st.set_page_config(page_title="Mantenimiento IT | Kenzo Jeans", layout="wide", page_icon="💻")

# ==============================================================================
# AQUÍ PEGAREMOS LA URL DEL WEBHOOK DE GOOGLE APPS SCRIPT EN EL SIGUIENTE PASO
WEBHOOK_URL = "" 
# ==============================================================================

# Estilos CSS
st.markdown("""
    <style>
    .kpi-card { background-color: #1e2430; border: 1px solid #2d3748; padding: 15px; border-radius: 8px; text-align: center; }
    .kpi-value { font-size: 26px; font-weight: bold; color: #38bdf8; }
    .kpi-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;}
    .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 50px; }
    .status-ok { color: #4ade80; } .status-warning { color: #f59e0b; } .status-critical { color: #ef4444; }
    .firma-card { background-color: #0f172a; border: 1px solid #334155; padding: 10px; border-radius: 6px; margin: 5px 0; }
    </style>
""", unsafe_allow_html=True)

st.title("💻 Gestión y Control de Mantenimiento de Equipos")
st.markdown("Dashboard de indicadores, registro y validación de actas de mantenimiento IT.")

# 2. FUNCIONES DE CARGA Y PROCESAMIENTO DE DATOS
@st.cache_data(ttl=60)
def cargar_datos_mantenimiento():
    ID_HOJA = "1hbXmOgYGoJ1vouSodHnh3nNB9kQQ6ST9EV8lIzd9-m4"
    nombre_encoded = urllib.parse.quote("Respuestas de formulario 1")
    url = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet={nombre_encoded}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            df = pd.read_csv(io.BytesIO(response.read()))

        # Normalizar nombres y desambiguar columnas duplicadas
        df.columns = df.columns.str.strip().str.upper()
        nuevas_columnas = []
        vistas = {}
        for col in df.columns:
            if col not in vistas:
                vistas[col] = 1
                nuevas_columnas.append(col)
            else:
                nuevas_columnas.append(f"{col}_{vistas[col]}")
                vistas[col] += 1
        df.columns = nuevas_columnas

        # Limpieza de fechas
        cols_fecha = [c for c in df.columns if 'FECHA' in c]
        if cols_fecha:
            df['FECHA_CLEAN'] = pd.to_datetime(df[cols_fecha[0]], errors='coerce')
        else:
            df['FECHA_CLEAN'] = pd.NaT

        return df, None
    except Exception as e:
        return pd.DataFrame(), f"Error al conectar con la hoja: {str(e)}"

# Ejecutar carga de datos
df_mantenimiento_full, msj_error = cargar_datos_mantenimiento()

def convertir_imagen_a_base64(image_data):
    if image_data is None:
        return None
    img = Image.fromarray(image_data.astype('uint8'))
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    return img_base64

def decodificar_firma(firma_base64):
    if not firma_base64 or pd.isna(firma_base64):
        return None
    try:
        img_data = base64.b64decode(firma_base64)
        img = Image.open(io.BytesIO(img_data))
        return img
    except:
        return None

# 3. FILTROS EN SIDEBAR (Solo afectan al Dashboard y Tabla)
hoy = datetime.today().date()
st.sidebar.header("⚙️ Filtros Globales")
st.sidebar.markdown("Personaliza la vista del dashboard:")

if not df_mantenimiento_full.empty and 'FECHA_CLEAN' in df_mantenimiento_full.columns:
    fechas_validas = df_mantenimiento_full['FECHA_CLEAN'].dropna()
    if not fechas_validas.empty:
        min_date = fechas_validas.min().date()
        max_date = fechas_validas.max().date()
    else:
        min_date = max_date = hoy
else:
    min_date = max_date = hoy

min_selec = min(min_date, datetime(2020, 1, 1).date())
max_selec = max(max_date, hoy) + timedelta(days=365)

fecha_rango = st.sidebar.date_input(
    "Rango de Fechas",
    value=[min_date, max_date] if min_date <= max_date else [hoy, hoy],
    min_value=min_selec,
    max_value=max_selec
)

df_mantenimiento = df_mantenimiento_full.copy()
if len(fecha_rango) == 2:
    start_date, end_date = fecha_rango
    if 'FECHA_CLEAN' in df_mantenimiento.columns:
        mask = (df_mantenimiento['FECHA_CLEAN'].dt.date >= start_date) & (df_mantenimiento['FECHA_CLEAN'].dt.date <= end_date)
        df_mantenimiento = df_mantenimiento.loc[mask]

col_area = next((c for c in df_mantenimiento.columns if 'ÁREA' in c or 'AREA' in c), None)
if col_area and not df_mantenimiento[col_area].isnull().all():
    areas_disponibles = sorted(df_mantenimiento[col_area].dropna().unique().tolist())
    area_filtro = st.sidebar.multiselect("Filtrar por Área/Depto:", areas_disponibles, default=areas_disponibles)
    if area_filtro:
        df_mantenimiento = df_mantenimiento[df_mantenimiento[col_area].isin(area_filtro)]

st.sidebar.markdown("---")

# 4. INTERFAZ DE PESTAÑAS
tab_form, tab_dashboard, tab_datos, tab_firmas = st.tabs([
    "📝 Nuevo Mantenimiento",
    "📊 Dashboard de Gestión", 
    "📋 Datos Completos", 
    "📄 Historial de Firmas"
])

# --- PESTAÑA 1: FORMULARIO DE REGISTRO NATIVO ---
with tab_form:
    st.subheader("Registrar Nuevo Mantenimiento IT")
    st.markdown("Completa los datos del equipo y registra la firma de conformidad en tiempo real.")
    
    col_form1, col_form2 = st.columns(2)
    
    with col_form1:
        fecha_mant = st.date_input("Fecha del Mantenimiento", datetime.today())
        placa_eq = st.text_input("Placa / Serial del Equipo*")
        usuario_resp = st.text_input("Usuario Responsable*")
        area_depto = st.selectbox("Área / Departamento", [
            "Administración", "Sistemas", "Operaciones", "Ventas", "Gerencia", "Jurídico", "Bodega"
        ])
        
    with col_form2:
        cargo_usuario = st.text_input("Cargo del Usuario")
        estado_final = st.selectbox("Estado Final del Equipo*", [
            "✅ Operativo", 
            "⚠️ Operativo con Observaciones", 
            "❌ Fuera de Servicio"
        ])
        observaciones_mant = st.text_area("Hallazgos / Observaciones", height=130, placeholder="Detalles de la reparación o pendientes...")

    st.write("---")
    st.markdown("### ✍️ Firma del Técnico o Usuario")
    st.markdown("Firma en el recuadro blanco para validar la información.")
    
    firma_nueva = st_canvas(
        stroke_width=3,
        stroke_color="#000000",
        background_color="#f8fafc",
        height=200,
        width=600,
        drawing_mode="freedraw",
        key="firma_formulario",
    )
    
    if st.button("💾 Guardar y Subir Mantenimiento", type="primary"):
        if not placa_eq or not usuario_resp:
            st.error("⚠️ Los campos de Placa y Usuario Responsable son obligatorios.")
        elif firma_nueva.image_data is None:
            st.warning("⚠️ Debes proporcionar una firma en el lienzo antes de guardar.")
        else:
            firma_b64 = convertir_imagen_a_base64(firma_nueva.image_data)
            
            # Construir el diccionario de datos a enviar
            datos_mantenimiento = {
                "fecha": fecha_mant.strftime("%Y-%m-%d"),
                "placa": placa_eq.strip().upper(),
                "usuario": usuario_resp.strip().upper(),
                "area": area_depto,
                "cargo": cargo_usuario.strip().upper(),
                "estado": estado_final,
                "observaciones": observaciones_mant,
                "firma_base64": firma_b64
            }
            
            if WEBHOOK_URL == "":
                st.info("ℹ️ El código está listo. En el siguiente paso conectaremos la base de datos para que esto viaje a tu Google Sheet.")
                st.json({"estado": "Pendiente de configuración de Webhook", "datos": datos_mantenimiento})
            else:
                try:
                    respuesta = requests.post(WEBHOOK_URL, json=datos_mantenimiento)
                    if respuesta.status_code == 200:
                        st.success(f"✅ ¡El mantenimiento del equipo {placa_eq} se ha guardado correctamente en Google Sheets!")
                        st.balloons()
                    else:
                        st.error("Hubo un problema al contactar con la hoja de cálculo.")
                except Exception as e:
                    st.error(f"Error de conexión: {str(e)}")

# --- PESTAÑA 2: DASHBOARD ---
with tab_dashboard:
    if msj_error:
        st.error(msj_error)

    if not df_mantenimiento.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        def calcular_sla_compliance(df):
            col_est = next((c for c in df.columns if 'ESTADO FINAL' in c), None)
            if col_est and not df[col_est].isnull().all():
                total = len(df)
                operativos = len(df[df[col_est].str.contains('Operativo', case=False, na=False)])
                return round((operativos / total * 100), 1) if total > 0 else 0
            return 0

        total_mantenimientos = len(df_mantenimiento)
        areas_atendidas = df_mantenimiento[col_area].nunique() if col_area else 0
        sla_compliance = calcular_sla_compliance(df_mantenimiento)
        col_equipo = next((c for c in df_mantenimiento.columns if 'PLACA' in c or 'EQUIPO' in c), None)
        equipos_unicos = df_mantenimiento[col_equipo].nunique() if col_equipo else 0

        col1.markdown(f"<div class='kpi-card'><div class='kpi-label'>Mantenimientos Realizados</div><div class='kpi-value'>{total_mantenimientos}</div></div>", unsafe_allow_html=True)
        col2.markdown(f"<div class='kpi-card'><div class='kpi-label'>Equipos Diferentes</div><div class='kpi-value' style='color:#4ade80;'>{equipos_unicos}</div></div>", unsafe_allow_html=True)
        col3.markdown(f"<div class='kpi-card'><div class='kpi-label'>Áreas Atendidas</div><div class='kpi-value' style='color:#38bdf8;'>{areas_atendidas}</div></div>", unsafe_allow_html=True)
        
        sla_color = "#4ade80" if sla_compliance >= 95 else "#f59e0b" if sla_compliance >= 80 else "#ef4444"
        col4.markdown(f"<div class='kpi-card'><div class='kpi-label'>Cumplimiento SLA</div><div class='kpi-value' style='color:{sla_color};'>{sla_compliance}%</div></div>", unsafe_allow_html=True)

        st.write("---")
        c_graf1, c_graf2 = st.columns(2)
        
        with c_graf1:
            if col_area and not df_mantenimiento[col_area].isnull().all():
                resumen_area = df_mantenimiento[col_area].value_counts().reset_index()
                resumen_area.columns = ['Área', 'Cantidad']
                fig_area = px.bar(resumen_area, x='Cantidad', y='Área', orientation='h', title="<b>Mantenimientos por Área / Depto</b>", template="plotly_dark", color_discrete_sequence=['#38bdf8'])
                fig_area.update_layout(height=400)
                st.plotly_chart(fig_area, use_container_width=True)
            else:
                st.info("Aún no hay datos de Áreas para graficar.")

        with c_graf2:
            col_estado = next((c for c in df_mantenimiento.columns if 'ESTADO FINAL' in c), None)
            if col_estado and not df_mantenimiento[col_estado].isnull().all():
                resumen_estado = df_mantenimiento[col_estado].value_counts().reset_index()
                resumen_estado.columns = ['Estado', 'Cantidad']
                fig_estado = px.pie(resumen_estado, values='Cantidad', names='Estado', title="<b>Distribución de Estado Final del Equipo</b>", template="plotly_dark", hole=0.4)
                fig_estado.update_layout(height=400)
                st.plotly_chart(fig_estado, use_container_width=True)
            else:
                st.info("Aún no hay datos de Estado Final para graficar.")

        st.write("---")
        st.markdown("### 📅 Registros Más Recientes")
        st.dataframe(df_mantenimiento.drop(columns=['FECHA_CLEAN', 'DISPLAY_NAME'], errors='ignore').head(10), use_container_width=True)
    else:
        if not msj_error:
            st.info("No hay registros en la hoja de cálculo todavía.")

# --- PESTAÑA 3: DATOS COMPLETOS ---
with tab_datos:
    st.subheader("Tabla Completa de Mantenimientos")
    
    if not df_mantenimiento.empty:
        col_desc1, col_desc2 = st.columns(2)
        
        with col_desc1:
            csv_data = df_mantenimiento.drop(columns=['FECHA_CLEAN'], errors='ignore').to_csv(index=False).encode('utf-8-sig')
            st.download_button("⬇️ Descargar como CSV", data=csv_data, file_name=f"mantenimientos_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
            
        with col_desc2:
            try:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df_mantenimiento.drop(columns=['FECHA_CLEAN'], errors='ignore').to_excel(writer, sheet_name='Mantenimientos', index=False)
                excel_buffer.seek(0)
                st.download_button("⬇️ Descargar como Excel", data=excel_buffer.getvalue(), file_name=f"mantenimientos_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except ModuleNotFoundError:
                st.warning("⚠️ Para habilitar la descarga en Excel, agrega `openpyxl` a tu archivo `requirements.txt` en GitHub.")
                
        st.write("---")
        st.dataframe(df_mantenimiento.drop(columns=['FECHA_CLEAN'], errors='ignore'), use_container_width=True, height=500)
    else:
        st.info("No hay registros para mostrar.")

# --- PESTAÑA 4: HISTORIAL DE FIRMAS ---
with tab_firmas:
    st.subheader("📄 Registros Consolidados con Firma")
    st.markdown("Aquí visualizaremos las firmas obtenidas del nuevo flujo de registro.")
    st.info("Esta sección se alimentará automáticamente de los datos de la base de datos una vez conectemos el Webhook.")

st.markdown("<div class='footer'>SGA v2.0 · Sistemas e Infraestructura · Kenzo Jeans SAS</div>", unsafe_allow_html=True)
