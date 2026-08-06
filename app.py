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
# Preferido: define WEBHOOK_URL en .streamlit/secrets.toml como:
# webhook_url = "https://script.google.com/macros/s/..."
# Si no existe el secreto (o no hay secrets.toml), cae al valor hardcodeado como respaldo.
try:
    WEBHOOK_URL = st.secrets.get("webhook_url", "https://script.google.com/macros/s/AKfycbyDniiOlytcSqjvACWjoaJpSb5kXodI_qOcvT0gHlv7_rqW_DlFQg2RCDSD8UsLojyZ/exec")
except Exception:
    WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyDniiOlytcSqjvACWjoaJpSb5kXodI_qOcvT0gHlv7_rqW_DlFQg2RCDSD8UsLojyZ/exec"
# ==============================================================================
 
# ==============================================================================
# LISTAS CERRADAS DE ÁREAS/ALMACENES — editar aquí si se agrega, quita o renombra
# una sede. El operario del formulario NO puede escribir nombres libres: solo
# selecciona de estas listas, para evitar nombres duplicados o mal escritos.
# ==============================================================================
AREAS_ALMACENES = sorted([
    "SALITRE PLAZA", "RESTREPO 1", "FONTIBÓN", "QUIRIGUA", "TUNAL",
    "PLAZA DE LAS AMÉRICAS 1", "CENTRO SUBA", "SANTA HELENITA", "KENNEDY",
    "CHAPINERO", "ESTRADA", "CENTRO 1", "RESTREPO 2", "OUTLET ZONA", "PORTAL 80",
    "UNICENTRO OCCIDENTE", "YOPAL", "TINTAL PLAZA", "PLAZA IMPERIAL",
    "CENTRO COMERCIAL SANTAFÉ", "CENTRO MAYOR", "TITÁN PLAZA", "DIVER PLAZA",
    "ZIPAQUIRÁ", "MERCURIO", "FACTORY", "MOSQUERA", "HAYUELOS",
    "PLAZA DE LAS AMÉRICAS 2", "FUNZA MI CENTRO", "GIRARDOT", "IPIALES",
    "CALLE 13 ZONA", "POPAYÁN", "PLAZA CENTRAL", "BOSA PIAMONTE CALLE",
    "TOBERÍN", "VENTURA TERREROS", "GRAN PLAZA ENSUEÑO", "CAJICÁ",
    "FACATATIVÁ", "TUNJA", "GRAN PLAZA BOSA", "PASEO VILLA DEL RÍO",
    "NUESTRO BOGOTÁ", "ATRÉVETE FONTIBÓN", "ATRÉVETE SEVILLANA", "MADRID",
    "CARRERA 62", "OUTLET CENTER", "FUSAGASUGÁ", "ALTA VISTA",
    "OUTLET CARRERA 62", "RIONEGRO – ANTIOQUIA", "OUTLET FLORESTA", "ESPINAL",
    "FUNZA CENTRO", "BODEGA CRA 62",
])
 
AREAS_ADMINISTRATIVOS = sorted([
    "SECRETARIA (Gerencia / Presidencia)", "ENFERMERÍA",
    "PORTERIA SEGURIDAD – IMEGA", "PORTERIA SEGURIDAD - CARRERA 62",
    "ABOGADA LABORAL", "DISEÑO KENZO", "BORDADO INDUSTRIAL", "TALENTO HUMANO",
    "NÓMINA – TH", "TESORERÍA", "CONTABILIDAD", "PLANTAS PRODUCCIÓN",
    "TIENDA ONLINE", "RETIROS - LIQUIDACIONES RH", "PLANEACIÓN",
    "PRODUCTO TERMINADO", "INSUMOS", "COMPRAS", "BODEGA DE QUÍMICOS",
    "SELECCIÓN Y CONTRATACION", "BIENESTAR", "AREA COMERCIAL", "INVENTARIOS",
    "PRODUCCION", "VALIDACIÓN", "SELECCIÓN Y RECLUTAMIENTO",
    "DIRECTOR FINANCIERO", "TIENDA ON LINE - (Servicio al Cliente)",
    "BITÁCORAS - INCAPACIDADES – RH", "TESORERÍA (Pagos)",
    "CCM - MONITOREO DE ALARMAS", "LÍDER – SISTEMAS",
    "MESA DE AYUDA – SISTEMAS", "SG – SST", "COMUNICACIONES Y MARKETING",
    "CCM 2 (MONITOREO DE ALARMAS)", "COSTOS DISEÑO",
    "SERVICIO AL CLIENTE EXTERNO-PRE VENTA", "CORTE", "CÓDIGOS – IMPORTADOS",
    "CENTRAL DE OPERACIONES - POST VENTA", "REVISOR FISCAL",
    "ANALISTA DE PRODUCTO – PLANEACION", "COSTOS CONTABILIDAD",
    "INGENIERÍA – SATÉLITE", "AMBIENTAL",
])
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
    nombre_encoded = urllib.parse.quote("Form_Responses")
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
 
# Lista maestra de áreas para el formulario: se toma de TODO el histórico (sin filtro de fecha)
# para que el desplegable del filtro del sidebar siempre incluya todas las áreas registradas.
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
 
        tipo_area = st.radio("Tipo de área*", ["🏬 Almacén", "🏢 Administrativo"], horizontal=True)
        lista_areas = AREAS_ALMACENES if tipo_area == "🏬 Almacén" else AREAS_ADMINISTRATIVOS
        placeholder_area = "Busca el almacén..." if tipo_area == "🏬 Almacén" else "Busca el área administrativa..."
        f_area = st.selectbox(
            "Área/Departamento*",
            lista_areas,
            index=None,
            placeholder=placeholder_area
        )
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
        if not f_placas or not f_usuario or not f_analista or not f_area:
            st.error("⚠️ Los campos de Placa, Usuario Responsable, Área/Departamento y Analista son obligatorios.")
        elif firma_nueva.image_data is None:
            st.warning("⚠️ Debes proporcionar una firma en el lienzo antes de guardar.")
        else:
            firma_b64 = convertir_imagen_a_base64(firma_nueva.image_data)
            
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
 
                    if respuesta.status_code == 200 and "success" in respuesta.text:
                        st.success(f"✅ ¡El acta del equipo {f_placas} se ha subido correctamente!")
                        st.balloons()
                    else:
                        st.error("⚠️ Google rechazó el registro. Revisa los detalles a continuación.")
                        with st.expander("Detalles técnicos del error"):
                            st.write(f"Código HTTP: {respuesta.status_code}")
                            st.write(f"Respuesta cruda de Google: {respuesta.text}")
                except Exception as e:
                    st.error(f"Error de conexión: {str(e)}")
 
# --- PESTAÑA 2: DASHBOARD ---
with tab_dashboard:
    if msj_error:
        st.error(msj_error)
 
    if not df_mantenimiento.empty:
        col_equipo = next((c for c in df_mantenimiento.columns if 'PLACA' in c), None)
        col_estado = next((c for c in df_mantenimiento.columns if 'VALIDACION_ESTADO' in c or 'ESTADO' in c), None)
        col_condiciones = next((c for c in df_mantenimiento.columns if 'CONDICIONES_INICIALES' in c), None)
 
        def calcular_pct_optimo(df):
            if col_estado and not df[col_estado].isnull().all():
                total = len(df)
                optimos = len(df[df[col_estado].astype(str).str.contains('Óptimo|Optimo|Operativo', case=False, na=False)])
                return round((optimos / total * 100), 1) if total > 0 else 0
            return 0
 
        # --- KPIs GLOBALES ---
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f"<div class='kpi-card'><div class='kpi-label'>Mantenimientos Realizados</div><div class='kpi-value'>{len(df_mantenimiento)}</div></div>", unsafe_allow_html=True)
 
        equipos_unicos = df_mantenimiento[col_equipo].nunique() if col_equipo else 0
        col2.markdown(f"<div class='kpi-card'><div class='kpi-label'>Equipos Diferentes</div><div class='kpi-value' style='color:#4ade80;'>{equipos_unicos}</div></div>", unsafe_allow_html=True)
 
        areas_atendidas = df_mantenimiento[col_area].nunique() if col_area else 0
        col3.markdown(f"<div class='kpi-card'><div class='kpi-label'>Áreas Atendidas</div><div class='kpi-value' style='color:#38bdf8;'>{areas_atendidas}</div></div>", unsafe_allow_html=True)
 
        pct_optimo = calcular_pct_optimo(df_mantenimiento)
        color_optimo = "#4ade80" if pct_optimo >= 95 else "#f59e0b" if pct_optimo >= 80 else "#ef4444"
        col4.markdown(f"<div class='kpi-card'><div class='kpi-label'>Equipos Óptimos</div><div class='kpi-value' style='color:{color_optimo};'>{pct_optimo}%</div></div>", unsafe_allow_html=True)
 
        st.write("---")
 
        # --- TARJETAS POR ÁREA ---
        if col_area and not df_mantenimiento[col_area].isnull().all():
            st.markdown("### 🏢 Resumen por Área / Departamento")
            areas_resumen = []
            for area_nombre, grupo in df_mantenimiento.groupby(col_area):
                if pd.isna(area_nombre) or str(area_nombre).strip() == "":
                    continue
                pct = calcular_pct_optimo(grupo)
                ultima_fecha = grupo['FECHA_CLEAN'].max()
                ultima_fecha_str = ultima_fecha.strftime('%d/%m/%Y') if pd.notna(ultima_fecha) else "N/D"
                areas_resumen.append({
                    "area": area_nombre, "total": len(grupo),
                    "pct_optimo": pct, "ultima_fecha": ultima_fecha_str
                })
            areas_resumen = sorted(areas_resumen, key=lambda x: x["total"], reverse=True)
 
            cols_por_fila = 4
            for i in range(0, len(areas_resumen), cols_por_fila):
                fila = st.columns(cols_por_fila)
                for j, item in enumerate(areas_resumen[i:i + cols_por_fila]):
                    color = "#4ade80" if item["pct_optimo"] >= 95 else "#f59e0b" if item["pct_optimo"] >= 80 else "#ef4444"
                    fila[j].markdown(f"""
                        <div class='kpi-card'>
                            <div class='kpi-label'>{item['area']}</div>
                            <div class='kpi-value' style='font-size:20px;'>{item['total']} mant.</div>
                            <div style='color:{color}; font-size:14px; font-weight:bold;'>{item['pct_optimo']}% óptimo</div>
                            <div style='color:#64748b; font-size:11px; margin-top:4px;'>Último: {item['ultima_fecha']}</div>
                        </div>
                    """, unsafe_allow_html=True)
            st.write("---")
 
        # --- GRÁFICOS ---
        st.markdown("### 📊 Análisis Visual")
        g_col1, g_col2 = st.columns(2)
 
        with g_col1:
            if col_area and not df_mantenimiento[col_area].isnull().all():
                conteo_area = df_mantenimiento[col_area].value_counts().reset_index()
                conteo_area.columns = ['Área', 'Mantenimientos']
                fig_area = px.bar(conteo_area, x='Área', y='Mantenimientos', title="Mantenimientos por Área",
                                   color='Mantenimientos', color_continuous_scale='Blues')
                fig_area.update_layout(showlegend=False, height=350)
                st.plotly_chart(fig_area, use_container_width=True)
 
        with g_col2:
            if col_estado and not df_mantenimiento[col_estado].isnull().all():
                conteo_estado = df_mantenimiento[col_estado].value_counts().reset_index()
                conteo_estado.columns = ['Estado', 'Cantidad']
                colores_estado = {'Óptimo': '#4ade80', 'Requiere seguimiento': '#f59e0b', 'En falla': '#ef4444'}
                fig_estado = px.pie(conteo_estado, names='Estado', values='Cantidad', hole=0.5,
                                     title="Distribución del Estado de los Equipos",
                                     color='Estado', color_discrete_map=colores_estado)
                fig_estado.update_layout(height=350)
                st.plotly_chart(fig_estado, use_container_width=True)
 
        g_col3, g_col4 = st.columns(2)
 
        with g_col3:
            # Ranking de áreas con más incidencias (no-óptimo)
            if col_area and col_estado and not df_mantenimiento[col_area].isnull().all():
                df_incidencias = df_mantenimiento.copy()
                df_incidencias['es_incidencia'] = ~df_incidencias[col_estado].astype(str).str.contains('Óptimo|Optimo', case=False, na=False)
                ranking = df_incidencias.groupby(col_area)['es_incidencia'].agg(['sum', 'count']).reset_index()
                ranking.columns = ['Área', 'Incidencias', 'Total']
                ranking['% Incidencias'] = round(ranking['Incidencias'] / ranking['Total'] * 100, 1)
                ranking = ranking[ranking['Incidencias'] > 0].sort_values('% Incidencias', ascending=True).tail(10)
                if not ranking.empty:
                    fig_ranking = px.bar(ranking, x='% Incidencias', y='Área', orientation='h',
                                          title="Top Áreas con Más Incidencias (Requiere seguimiento / En falla)",
                                          color='% Incidencias', color_continuous_scale='OrRd',
                                          text='Incidencias')
                    fig_ranking.update_layout(showlegend=False, height=350)
                    st.plotly_chart(fig_ranking, use_container_width=True)
                else:
                    st.info("🎉 No hay áreas con incidencias registradas en el rango seleccionado.")
 
        with g_col4:
            # Hallazgos más frecuentes (a partir del multiselect de condiciones iniciales)
            if col_condiciones and not df_mantenimiento[col_condiciones].isnull().all():
                todos_items = df_mantenimiento[col_condiciones].dropna().astype(str).str.split(', ').explode()
                todos_items = todos_items[todos_items.str.strip() != ""]
                conteo_hallazgos = todos_items.value_counts().reset_index()
                conteo_hallazgos.columns = ['Hallazgo', 'Frecuencia']
                if not conteo_hallazgos.empty:
                    fig_hallazgos = px.bar(conteo_hallazgos.head(8), x='Frecuencia', y='Hallazgo', orientation='h',
                                            title="Hallazgos Más Frecuentes al Recibir Equipos",
                                            color='Frecuencia', color_continuous_scale='Purples')
                    fig_hallazgos.update_layout(showlegend=False, height=350, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_hallazgos, use_container_width=True)
 
        # Línea de tiempo mensual
        if 'FECHA_CLEAN' in df_mantenimiento.columns and df_mantenimiento['FECHA_CLEAN'].notna().any():
            df_tiempo = df_mantenimiento.dropna(subset=['FECHA_CLEAN']).copy()
            df_tiempo['MES'] = df_tiempo['FECHA_CLEAN'].dt.to_period('M').astype(str)
            conteo_mes = df_tiempo.groupby('MES').size().reset_index(name='Mantenimientos')
            fig_tiempo = px.line(conteo_mes, x='MES', y='Mantenimientos', markers=True,
                                  title="Evolución Mensual de Mantenimientos")
            fig_tiempo.update_layout(height=300)
            st.plotly_chart(fig_tiempo, use_container_width=True)
 
        # Equipos con más intervenciones (recurrentes)
        if col_equipo and not df_mantenimiento[col_equipo].isnull().all():
            conteo_equipo = df_mantenimiento[col_equipo].value_counts().reset_index()
            conteo_equipo.columns = ['Placa', 'Nº de Mantenimientos']
            recurrentes = conteo_equipo[conteo_equipo['Nº de Mantenimientos'] > 1]
            if not recurrentes.empty:
                st.markdown("### 🔁 Equipos con Más Intervenciones")
                st.caption("Equipos que han requerido más de un mantenimiento en el rango seleccionado — posibles candidatos a reemplazo.")
                st.dataframe(recurrentes.head(10), use_container_width=True, hide_index=True)
 
        st.write("---")
        st.markdown("### 📅 Registros Más Recientes")
        st.dataframe(df_mantenimiento.drop(columns=['FECHA_CLEAN'], errors='ignore').head(10), use_container_width=True)
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
    st.subheader("📄 Historial de Actas con Firma Verificada")
    st.info("Selecciona o despliega cualquier registro para consultar sus detalles completos y la firma de conformidad.")
    
    if not df_mantenimiento.empty:
        col_firma_col = next((c for c in df_mantenimiento.columns if 'FIRMA' in c), None)
        col_equipo_col = next((c for c in df_mantenimiento.columns if 'PLACAS' in c or 'PLACA' in c), None)
        col_usuario_col = next((c for c in df_mantenimiento.columns if 'USUARIO' in c), None)
        col_fecha_col = next((c for c in df_mantenimiento.columns if 'FECHA_MANTENIMIENTO' in c or 'FECHA' in c), None)
 
        # Búsqueda y paginación para no saturar la vista con muchos registros
        col_busq, col_pag = st.columns([2, 1])
        with col_busq:
            texto_busqueda = st.text_input("🔍 Buscar por placa o usuario:", "")
        with col_pag:
            registros_por_pagina = st.selectbox("Registros por página:", [10, 25, 50], index=0)
 
        df_firmas = df_mantenimiento.copy()
        if texto_busqueda:
            mascara_busqueda = pd.Series(False, index=df_firmas.index)
            if col_equipo_col:
                mascara_busqueda |= df_firmas[col_equipo_col].astype(str).str.contains(texto_busqueda, case=False, na=False)
            if col_usuario_col:
                mascara_busqueda |= df_firmas[col_usuario_col].astype(str).str.contains(texto_busqueda, case=False, na=False)
            df_firmas = df_firmas[mascara_busqueda]
 
        total_registros = len(df_firmas)
        total_paginas = max(1, (total_registros - 1) // registros_por_pagina + 1)
        pagina = st.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1)
        inicio = (pagina - 1) * registros_por_pagina
        fin = inicio + registros_por_pagina
        st.caption(f"Mostrando {min(inicio + 1, total_registros)}–{min(fin, total_registros)} de {total_registros} registros")
 
        for idx, row in df_firmas.iloc[inicio:fin].iterrows():
            placa_val = row[col_equipo_col] if col_equipo_col and pd.notna(row[col_equipo_col]) else "S/N"
            usuario_val = row[col_usuario_col] if col_usuario_col and pd.notna(row[col_usuario_col]) else "Desconocido"
            fecha_val = row[col_fecha_col] if col_fecha_col and pd.notna(row[col_fecha_col]) else "Fecha no registrada"
            
            with st.expander(f"📌 Acta Equipo Placas: {placa_val} — Responsable: {usuario_val} ({fecha_val})"):
                cols_det1, cols_det2 = st.columns([2, 1])
                
                with cols_det1:
                    st.markdown("#### Detalles del Mantenimiento")
                    for col in df_mantenimiento.columns:
                        if col not in ['FECHA_CLEAN', col_firma_col]:
                            val_celda = row[col]
                            if pd.notna(val_celda) and str(val_celda).strip() != "":
                                st.markdown(f"**{col.replace('_', ' ').title()}:** {val_celda}")
                
                with cols_det2:
                    st.markdown("#### Firma de Conformidad")
                    if col_firma_col and pd.notna(row[col_firma_col]):
                        firma_base64 = str(row[col_firma_col]).strip()
                        if firma_base64 != "":
                            try:
                                if "," in firma_base64:
                                    firma_base64 = firma_base64.split(",")[1]
                                image_bytes = base64.b64decode(firma_base64)
                                image = Image.open(io.BytesIO(image_bytes))
                                st.image(image, width=280)
                            except Exception as e:
                                st.warning("No se pudo procesar la imagen de la firma.")
                        else:
                            st.info("Sin firma registrada en este campo.")
                    else:
                        st.info("No hay datos de firma para este registro.")
    else:
        st.info("No hay registros disponibles para mostrar en el historial.")
 
st.markdown("<div class='footer'>SGA v2.0 · Sistemas e Infraestructura · Kenzo Jeans SAS</div>", unsafe_allow_html=True)
