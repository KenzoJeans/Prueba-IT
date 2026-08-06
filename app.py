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
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbx7Fr087dY6pNLtuNEIWQaJKc06U1jO0r1V7uOiR2ZeaXIppC9eXgv51MAZvaea3Zhh/exec" 
# ==============================================================================

# Estilos CSS
st.markdown("""
    <style>
    .kpi-card { background-color: #1e2430; border: 1px solid #2d3748; padding: 15px; border-radius: 8px; text-align: center; }
    .kpi-value { font-size: 26px; font-weight: bold; color: #38bdf8; }
    .kpi-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;}
    .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 50px; }
    .status-ok { color: #4ade80; } .status-warning { color: #f59e0b; } .status-critical { color: #ef4444; }
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

        cols_fecha = [c for c in df.columns if 'FECHA' in c]
        if cols_fecha:
            df['FECHA_CLEAN'] = pd.to_datetime(df[cols_fecha[0]], errors='coerce')
        else:
            df['FECHA_CLEAN'] = pd.NaT

        return df, None
    except Exception as e:
        return pd.DataFrame(), f"Error al conectar con la hoja: {str(e)}"

df_mantenimiento_full, msj_error = cargar_datos_mantenimiento()

def convertir_imagen_a_base64(image_data):
    if image_data is None:
        return None
    img = Image.fromarray(image_data.astype('uint8'))
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# 3. FILTROS EN SIDEBAR
hoy = datetime.today().date()
st.sidebar.header("⚙️ Filtros Globales")
st.sidebar.markdown("Personaliza la vista del dashboard:")

if not df_mantenimiento_full.empty and 'FECHA_CLEAN' in df_mantenimiento_full.columns:
    fechas_validas = df_mantenimiento_full['FECHA_CLEAN'].dropna()
    min_date = fechas_validas.min().date() if not fechas_validas.empty else hoy
    max_date = fechas_validas.max().date() if not fechas_validas.empty else hoy
else:
    min_date = max_date = hoy

min_selec = min(min_date, datetime(2020, 1, 1).date())
max_selec = max(max_date, hoy) + timedelta(days=365)

fecha_rango = st.sidebar.date_input("Rango de Fechas", value=[min_date, max_date] if min_date <= max_date else [hoy, hoy], min_value=min_selec, max_value=max_selec)

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

# --- PESTAÑA 1: FORMULARIO DE REGISTRO NATIVO (IT) ---
with tab_form:
    st.markdown("### Registro de Mantenimiento Preventivo / Correctivo")
    st.info("Complete todos los campos requeridos según el formato técnico.")
    
    # SECCIÓN 1
    st.markdown("#### 1. INFORMACIÓN GENERAL DEL EQUIPO")
    col1, col2 = st.columns(2)
    with col1:
        f_fecha = st.date_input("Fecha del mantenimiento", datetime.today())
        f_usuario = st.text_input("Usuario responsable*")
        f_cargo = st.text_input("Cargo")
        f_area = st.text_input("Área/Departamento")
    with col2:
        f_placas = st.text_input("Placas*")
        f_marca = st.text_input("Marca/Modelo")
        f_serie = st.text_input("Número de serie")

    st.write("---")

    # SECCIÓN 2
    st.markdown("#### 2. CONDICIONES INICIALES DEL EQUIPO")
    f_condiciones = st.multiselect(
        "Seleccione los ítems revisados al recibir el equipo:",
        ["Encendido correcto", "Ruidos extraños", "Sobrecargas eléctricas", 
         "Estado general externo", "Estado de cables y conectores", 
         "Estado de puertos USB / HDMI / Red", "Lectura de temperaturas (si aplica)", 
         "Revisión visual de daños físicos"]
    )

    st.write("---")

    # SECCIÓN 3
    st.markdown("#### 3. ACTIVIDADES REALIZADAS EN EL MANTENIMIENTO PREVENTIVO")
    col_act1, col_act2 = st.columns(2)
    
    with col_act1:
        f_limpieza = st.multiselect("Limpieza física del equipo:", [
            "Limpieza externa del chasis", "Limpieza interna (remoción de polvo)", 
            "Limpieza de ventiladores", "Cambio de pasta térmica (si aplica)", 
            "Limpieza de pantalla y periféricos"
        ])
        
        f_pruebas = st.multiselect("Pruebas de funcionamiento:", [
            "Prueba de encendido", "Prueba de conectividad a red", 
            "Prueba de velocidad del sistema", "Prueba de periféricos (mouse, teclado, monitor)", 
            "Revisión del funcionamiento del software básico"
        ])
        
        f_respaldo = st.multiselect("Respaldo y seguridad:", [
            "Verificación de políticas de backup", "Backup realizado correctamente", 
            "Revisión de contraseñas y accesos", "Verificación de firewall", 
            "Verificación de software autorizado"
        ])

    with col_act2:
        f_revision_elec = st.multiselect("Revisión eléctrica y electrónica:", [
            "Revisión de la fuente de poder", "Revisión de cables de corriente", 
            "Verificación de toma regulada/UPS", "Revisión de tarjeta madre", 
            "Revisión de memorias RAM", "Revisión de disco duro / SSD"
        ])
        
        f_optimizacion = st.multiselect("Optimización del sistema:", [
            "Eliminación de archivos temporales", "Desfragmentación (si aplica)", 
            "Optimización de disco", "Actualización de sistema operativo", 
            "Actualización de controladores", "Actualización de antivirus"
        ])

    st.write("---")

    # SECCIONES 4, 5 Y 6
    st.markdown("#### 4. HALLAZGOS ENCONTRADOS")
    f_hallazgos = st.text_area("Describa los problemas o hallazgos relevantes:", height=100)
    
    st.markdown("#### 5. REPUESTOS UTILIZADOS / MATERIALES")
    f_repuestos = st.text_area("Describa los repuestos cambiados o materiales usados:", height=100)
    
    st.markdown("#### 6. RECOMENDACIONES")
    f_recomendaciones = st.text_area("Recomendaciones para el usuario:", height=100)

    st.write("---")

    # SECCIÓN 7
    st.markdown("#### 7. VALIDACIÓN DEL MANTENIMIENTO")
    col_val1, col_val2 = st.columns(2)
    
    with col_val1:
        f_validacion = st.selectbox("Estado del equipo post-mantenimiento:", [
            "Óptimo", "Requiere seguimiento", "En falla"
        ])
        
        opcion_analista = st.selectbox("Analista responsable:", [
            "Joan Quintero", "Gloria Isaquita", "Luis Serrato", "Michelle Zabala", "Otro"
        ])
        
        f_analista = opcion_analista
        if opcion_analista == "Otro":
            f_analista = st.text_input("Especifique el nombre del Analista:")
            
    with col_val2:
        # Se sugiere un próximo mantenimiento en 6 meses por defecto
        f_proximo = st.date_input("Próximo mantenimiento recomendado para:", datetime.today() + timedelta(days=180))

    st.write("---")

    # FIRMA
    st.markdown("### ✍️ Firma de Conformidad")
    st.markdown("Firma del usuario responsable aceptando el equipo tras el mantenimiento.")
    
    firma_nueva = st_canvas(
        stroke_width=3, stroke_color="#000000", background_color="#f8fafc",
        height=200, width=600, drawing_mode="freedraw", key="firma_formulario",
    )
    
    if st.button("💾 Guardar y Subir Mantenimiento", type="primary"):
        if not f_placas or not f_usuario or not f_analista:
            st.error("⚠️ Los campos de Placa, Usuario Responsable y Analista son obligatorios.")
        elif firma_nueva.image_data is None:
            st.warning("⚠️ Debes proporcionar una firma en el lienzo antes de guardar.")
        else:
            firma_b64 = convertir_imagen_a_base64(firma_nueva.image_data)
            
            # Recopilar todos los datos en un diccionario unificado
            datos_mantenimiento = {
                "fecha_mantenimiento": f_fecha.strftime("%Y-%m-%d"),
                "usuario": f_usuario.strip().upper(),
                "cargo": f_cargo.strip().upper(),
                "area": f_area.strip().upper(),
                "placas": f_placas.strip().upper(),
                "marca_modelo": f_marca.strip().upper(),
                "num_serie": f_serie.strip().upper(),
                
                "condiciones_iniciales": ", ".join(f_condiciones),
                "act_limpieza": ", ".join(f_limpieza),
                "act_revision_elec": ", ".join(f_revision_elec),
                "act_pruebas": ", ".join(f_pruebas),
                "act_optimizacion": ", ".join(f_optimizacion),
                "act_respaldo": ", ".join(f_respaldo),
                
                "hallazgos": f_hallazgos.replace('\n', ' | '),
                "repuestos": f_repuestos.replace('\n', ' | '),
                "recomendaciones": f_recomendaciones.replace('\n', ' | '),
                
                "validacion_estado": f_validacion,
                "analista": f_analista.strip().upper(),
                "proximo_mantenimiento": f_proximo.strftime("%Y-%m-%d"),
                
                "firma_base64": firma_b64
            }
            
            if WEBHOOK_URL == "":
                st.info("ℹ️ El formulario funciona perfectamente. En el siguiente paso conectaremos la base de datos para registrar esto.")
            else:
                try:
                    respuesta = requests.post(WEBHOOK_URL, json=datos_mantenimiento)
                    if respuesta.status_code == 200:
                        st.success(f"✅ ¡El acta del equipo {f_placas} se ha subido correctamente!")
                        st.balloons()
                    else:
                        st.error("Hubo un problema al contactar con la base de datos.")
                except Exception as e:
                    st.error(f"Error de conexión: {str(e)}")

# --- PESTAÑA 2: DASHBOARD ---
with tab_dashboard:
    if msj_error:
        st.error(msj_error)
    if not df_mantenimiento.empty:
        col1, col2, col3, col4 = st.columns(4)
        def calcular_sla_compliance(df):
            col_est = next((c for c in df.columns if 'VALIDACION_ESTADO' in c or 'ESTADO' in c), None)
            if col_est and not df[col_est].isnull().all():
                total = len(df)
                operativos = len(df[df[col_est].astype(str).str.contains('Operativo|Óptimo', case=False, na=False)])
                return round((operativos / total * 100), 1) if total > 0 else 0
            return 0

        col1.markdown(f"<div class='kpi-card'><div class='kpi-label'>Mantenimientos Realizados</div><div class='kpi-value'>{len(df_mantenimiento)}</div></div>", unsafe_allow_html=True)
        
        col_equipo = next((c for c in df_mantenimiento.columns if 'PLACA' in c), None)
        equipos_unicos = df_mantenimiento[col_equipo].nunique() if col_equipo else 0
        col2.markdown(f"<div class='kpi-card'><div class='kpi-label'>Equipos Diferentes</div><div class='kpi-value' style='color:#4ade80;'>{equipos_unicos}</div></div>", unsafe_allow_html=True)
        
        areas_atendidas = df_mantenimiento[col_area].nunique() if col_area else 0
        col3.markdown(f"<div class='kpi-card'><div class='kpi-label'>Áreas Atendidas</div><div class='kpi-value' style='color:#38bdf8;'>{areas_atendidas}</div></div>", unsafe_allow_html=True)
        
        sla_compliance = calcular_sla_compliance(df_mantenimiento)
        sla_color = "#4ade80" if sla_compliance >= 95 else "#f59e0b" if sla_compliance >= 80 else "#ef4444"
        col4.markdown(f"<div class='kpi-card'><div class='kpi-label'>Equipos Óptimos</div><div class='kpi-value' style='color:{sla_color};'>{sla_compliance}%</div></div>", unsafe_allow_html=True)

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
            st.download_button("⬇️ Descargar CSV", data=csv_data, file_name=f"mantenimientos_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
        with col_desc2:
            try:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df_mantenimiento.drop(columns=['FECHA_CLEAN'], errors='ignore').to_excel(writer, sheet_name='Mantenimientos', index=False)
                excel_buffer.seek(0)
                st.download_button("⬇️ Descargar Excel", data=excel_buffer.getvalue(), file_name=f"mantenimientos_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except ModuleNotFoundError:
                st.warning("⚠️ Agrega `openpyxl` a tu `requirements.txt` en GitHub para descargar en Excel.")
                
        st.write("---")
        st.dataframe(df_mantenimiento.drop(columns=['FECHA_CLEAN'], errors='ignore'), use_container_width=True, height=500)
    else:
        st.info("No hay registros para mostrar.")

# --- PESTAÑA 4: HISTORIAL DE FIRMAS ---
with tab_firmas:
    st.subheader("📄 Registros Consolidados con Firma")
    st.info("Esta sección se alimentará automáticamente de los datos de la nueva estructura una vez conectemos el Webhook.")

st.markdown("<div class='footer'>SGA v2.0 · Sistemas e Infraestructura · Kenzo Jeans SAS</div>", unsafe_allow_html=True)
