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
from PIL import Image

# 1. Configuración de la página
st.set_page_config(page_title="Mantenimiento IT | Kenzo Jeans", layout="wide", page_icon="💻")

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
st.markdown("Dashboard de indicadores y validación de actas de mantenimiento IT.")

# 2. FUNCIÓN DE CARGA DE DATOS
@st.cache_data(ttl=60)
def cargar_datos_mantenimiento():
    ID_HOJA = "1hbXmOgYGoJ1vouSodHnh3nNB9kQQ6ST9EV8lIzd9-m4"
    nombre_encoded = urllib.parse.quote("Respuestas de formulario 1")
    url = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet={nombre_encoded}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            df = pd.read_csv(io.BytesIO(response.read()))

        # Normalizar nombres de columnas a mayúsculas y sin espacios innecesarios
        df.columns = df.columns.str.strip().str.upper()

        # Limpieza y conversión de fechas
        cols_fecha = [c for c in df.columns if 'FECHA' in c]
        if cols_fecha:
            df['FECHA_CLEAN'] = pd.to_datetime(df[cols_fecha[0]], errors='coerce')
        else:
            df['FECHA_CLEAN'] = pd.NaT

        return df, None
    except Exception as e:
        return pd.DataFrame(), f"Error al conectar con la hoja: {str(e)}"

df_mantenimiento_full, msj_error = cargar_datos_mantenimiento()

# 3. FUNCIONES PARA GESTIÓN DE FIRMAS
@st.cache_data(ttl=60)
def cargar_historico_firmas():
    """Carga el historial de firmas desde Google Sheets"""
    ID_HOJA = "1hbXmOgYGoJ1vouSodHnh3nNB9kQQ6ST9EV8lIzd9-m4"
    nombre_encoded = urllib.parse.quote("Firmas Validadas")
    url = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet={nombre_encoded}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            df_firmas = pd.read_csv(io.BytesIO(response.read()))
        return df_firmas
    except:
        return pd.DataFrame(columns=['PLACA', 'USUARIO', 'TIMESTAMP', 'CONFORMIDAD', 'OBSERVACIONES', 'FIRMA_BASE64'])

def convertir_imagen_a_base64(image_data):
    """Convierte la imagen del canvas a base64 para almacenamiento"""
    if image_data is None:
        return None
    img = Image.fromarray(image_data.astype('uint8'))
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    return img_base64

def decodificar_firma(firma_base64):
    """Convierte base64 de vuelta a imagen para mostrar"""
    if not firma_base64 or pd.isna(firma_base64):
        return None
    try:
        img_data = base64.b64decode(firma_base64)
        img = Image.open(io.BytesIO(img_data))
        return img
    except:
        return None

def guardar_firma(placa, usuario, conformidad, observaciones, firma_base64):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if 'firmas_guardadas' not in st.session_state:
        st.session_state.firmas_guardadas = []
    
    registro_firma = {
        'PLACA': placa,
        'USUARIO': usuario,
        'TIMESTAMP': timestamp,
        'CONFORMIDAD': conformidad,
        'OBSERVACIONES': observaciones,
        'FIRMA_BASE64': firma_base64
    }
    
    st.session_state.firmas_guardadas.append(registro_firma)
    return True

# 4. FILTROS EN SIDEBAR
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

# 5. FUNCIONES AUXILIARES
def calcular_sla_compliance(df):
    col_estado = next((c for c in df.columns if 'ESTADO FINAL' in c), None)
    if col_estado and not df[col_estado].isnull().all():
        total = len(df)
        operativos = len(df[df[col_estado].str.contains('Operativo', case=False, na=False)])
        return round((operativos / total * 100), 1) if total > 0 else 0
    return 0

def obtener_detalle_equipo(registro, col_placas):
    detalle = {}
    for col, val in registro.items():
        if pd.notna(val) and str(val).strip() and col not in ['FECHA_CLEAN', 'DISPLAY_NAME']:
            detalle[col] = val
    return detalle

# 6. INTERFAZ DE PESTAÑAS
tab_dashboard, tab_firma, tab_datos, tab_firmas = st.tabs([
    "📊 Dashboard de Gestión", 
    "✍️ Validación y Firma de Actas", 
    "📋 Datos Completos", 
    "📄 Historial de Firmas"
])

# --- PESTAÑA 1: DASHBOARD ---
with tab_dashboard:
    if msj_error:
        st.error(msj_error)

    if not df_mantenimiento.empty:
        col1, col2, col3, col4 = st.columns(4)

        total_mantenimientos = len(df_mantenimiento)
        areas_atendidas = df_mantenimiento[col_area].nunique() if col_area else 0
        sla_compliance = calcular_sla_compliance(df_mantenimiento)

        col_equipo = next((c for c in df_mantenimiento.columns if 'EQUIPO' in c or 'DISPOSITIVO' in c), None)
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
                fig_area = px.bar(
                    resumen_area, x='Cantidad', y='Área', orientation='h',
                    title="<b>Mantenimientos por Área / Depto</b>",
                    template="plotly_dark", color_discrete_sequence=['#38bdf8']
                )
                fig_area.update_layout(height=400)
                st.plotly_chart(fig_area, use_container_width=True)
            else:
                st.info("Aún no hay datos de Áreas para graficar.")

        with c_graf2:
            col_estado = next((c for c in df_mantenimiento.columns if 'ESTADO FINAL' in c), None)
            if col_estado and not df_mantenimiento[col_estado].isnull().all():
                resumen_estado = df_mantenimiento[col_estado].value_counts().reset_index()
                resumen_estado.columns = ['Estado', 'Cantidad']
                fig_estado = px.pie(
                    resumen_estado, values='Cantidad', names='Estado',
                    title="<b>Distribución de Estado Final del Equipo</b>",
                    template="plotly_dark", hole=0.4
                )
                fig_estado.update_layout(height=400)
                st.plotly_chart(fig_estado, use_container_width=True)
            else:
                st.info("Aún no hay datos de Estado Final para graficar.")

        st.write("---")
        st.markdown("### 📅 Registros Más Recientes")
        df_resumen = df_mantenimiento.drop(columns=['FECHA_CLEAN', 'DISPLAY_NAME'], errors='ignore').head(10)
        st.dataframe(df_resumen, use_container_width=True)

    else:
        if not msj_error:
            st.info("No hay registros en la hoja de cálculo todavía. Esperando respuestas del formulario...")

# --- PESTAÑA 2: FIRMA DE VALIDACIÓN ---
with tab_firma:
    st.subheader("Validación de Servicios de Mantenimiento")
    st.markdown("Seleccione un registro para verificar los hallazgos y registrar la firma de conformidad del usuario responsable.")

    if not df_mantenimiento.empty:
        col_placas = next((c for c in df_mantenimiento.columns if 'PLACA' in c), None)
        col_usuario = next((c for c in df_mantenimiento.columns if 'USUARIO' in c), None)

        if col_placas and col_usuario:
            st.markdown("#### 🔍 Búsqueda del Equipo")
            col_busqueda_placa, col_busqueda_usuario = st.columns(2)

            with col_busqueda_placa:
                placas_disponibles = sorted(df_mantenimiento[col_placas].dropna().unique().tolist())
                placa_selec = st.selectbox("Seleccionar Placa:", placas_disponibles, key="placa_select")

            with col_busqueda_usuario:
                usuarios_con_placa = df_mantenimiento[df_mantenimiento[col_placas] == placa_selec][col_usuario].unique().tolist()
                usuario_selec = st.selectbox("Seleccionar Usuario:", usuarios_con_placa, key="usuario_select")

            registro_actual = df_mantenimiento[
                (df_mantenimiento[col_placas] == placa_selec) &
                (df_mantenimiento[col_usuario] == usuario_selec)
            ]

            if not registro_actual.empty:
                registro_actual = registro_actual.iloc[0]

                st.write("---")
                st.markdown("### 📋 Detalles del Mantenimiento")

                detalle_cols = st.columns(2)
                with detalle_cols[0]:
                    st.info(f"**Placa/Serial:** {registro_actual.get(col_placas, 'N/A')}")

                with detalle_cols[1]:
                    col_estado = next((c for c in df_mantenimiento.columns if 'ESTADO FINAL' in c), None)
                    estado_equipo = registro_actual.get(col_estado, 'N/A') if col_estado else 'N/A'
                    color_estado = "#4ade80" if "Operativo" in str(estado_equipo) else "#f59e0b"
                    st.markdown(f"<div style='background-color: #1e2430; padding: 10px; border-radius: 5px; border-left: 4px solid {color_estado};'><b>Estado Final:</b> {estado_equipo}</div>", unsafe_allow_html=True)

                detalle_dict = obtener_detalle_equipo(registro_actual, col_placas)
                st.json(detalle_dict)

                historico_equipo = df_mantenimiento_full[df_mantenimiento_full[col_placas] == placa_selec]
                if len(historico_equipo) > 1:
                    st.write("---")
                    st.markdown("### 📊 Histórico de Mantenimientos para Este Equipo")
                    st.dataframe(
                        historico_equipo.drop(columns=['FECHA_CLEAN', 'DISPLAY_NAME'], errors='ignore').sort_values(
                            by='FECHA_CLEAN' if 'FECHA_CLEAN' in historico_equipo.columns else [col for col in historico_equipo.columns][0],
                            ascending=False
                        ),
                        use_container_width=True
                    )

                st.write("---")
                st.markdown("### ✍️ Firma del Usuario Responsable")
                st.markdown("Por favor, firme en el recuadro blanco a continuación para validar la recepción y conformidad del mantenimiento.")

                firma_canvas = st_canvas(
                    stroke_width=3,
                    stroke_color="#000000",
                    background_color="#f8fafc",
                    height=200,
                    width=600,
                    drawing_mode="freedraw",
                    key="firma_usuario",
                )

                col_obs1, col_obs2 = st.columns(2)
                with col_obs1:
                    observaciones = st.text_area(
                        "Observaciones o Notas (Opcional):",
                        placeholder="Ej: Equipo con mejora notable...",
                        height=100
                    )

                with col_obs2:
                    conformidad = st.radio(
                        "¿Conforme con el mantenimiento?",
                        options=["✅ Sí", "⚠️ Parcialmente", "❌ No"],
                        index=0
                    )

                if firma_canvas.image_data is not None:
                    if st.button("💾 Guardar Validación de Mantenimiento", type="primary"):
                        firma_b64 = convertir_imagen_a_base64(firma_canvas.image_data)
                        guardar_firma(placa_selec, usuario_selec, conformidad, observaciones, firma_b64)
                        
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.success(
                            f"""
                            ✅ **Firma capturada exitosamente**
                            
                            - **Equipo:** {registro_actual.get(col_placas, '')}
                            - **Usuario:** {usuario_selec}
                            - **Conformidad:** {conformidad}
                            - **Timestamp:** {timestamp}
                            
                            El acta ha sido registrada en el sistema. Puedes ver el historial en la pestaña "Historial de Firmas".
                            """
                        )
                        st.balloons()
                else:
                    st.warning("⚠️ Por favor, firme en el canvas antes de guardar.")

            else:
                st.warning("No se encontró registro con esa combinación. Intenta nuevamente.")

        else:
            st.error("No se encontraron las columnas 'PLACA' o 'USUARIO'. Verifica los nombres en tu formulario.")

    else:
        st.info("No hay registros disponibles para firmar.")

# --- PESTAÑA 3: DATOS COMPLETOS ---
with tab_datos:
    st.subheader("Tabla Completa de Mantenimientos")
    st.markdown("Vista completa de todos los registros con opción de descarga.")

    if not df_mantenimiento.empty:
        col_desc1, col_desc2 = st.columns(2)

        with col_desc1:
            csv_data = df_mantenimiento.drop(columns=['FECHA_CLEAN', 'DISPLAY_NAME'], errors='ignore').to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "⬇️ Descargar como CSV",
                data=csv_data,
                file_name=f"mantenimientos_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        with col_desc2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_mantenimiento.drop(columns=['FECHA_CLEAN', 'DISPLAY_NAME'], errors='ignore').to_excel(writer, sheet_name='Mantenimientos', index=False)
            excel_buffer.seek(0)
            st.download_button(
                "⬇️ Descargar como Excel",
                data=excel_buffer.getvalue(),
                file_name=f"mantenimientos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.write("---")
        st.dataframe(
            df_mantenimiento.drop(columns=['FECHA_CLEAN', 'DISPLAY_NAME'], errors='ignore'),
            use_container_width=True,
            height=500
        )
    else:
        st.info("No hay registros para mostrar.")

# --- PESTAÑA 4: HISTORIAL DE FIRMAS ---
with tab_firmas:
    st.subheader("📄 Historial de Firmas Validadas")
    st.markdown("Consulta todas las firmas capturadas, organizadas por equipo.")

    if 'firmas_guardadas' in st.session_state and st.session_state.firmas_guardadas:
        df_firmas = pd.DataFrame(st.session_state.firmas_guardadas)
        
        col_filt1, col_filt2 = st.columns(2)
        with col_filt1:
            placas_unicas = sorted(df_firmas['PLACA'].unique().tolist())
            placa_filter = st.selectbox("Filtrar por Placa:", ["Todas"] + placas_unicas)
        
        with col_filt2:
            conformidad_filter = st.selectbox("Filtrar por Conformidad:", ["Todas", "✅ Sí", "⚠️ Parcialmente", "❌ No"])
        
        df_firmas_filtrado = df_firmas.copy()
        if placa_filter != "Todas":
            df_firmas_filtrado = df_firmas_filtrado[df_firmas_filtrado['PLACA'] == placa_filter]
        if conformidad_filter != "Todas":
            df_firmas_filtrado = df_firmas_filtrado[df_firmas_filtrado['CONFORMIDAD'] == conformidad_filter]
        
        st.write(f"**Total de firmas:** {len(df_firmas_filtrado)}")
        st.write("---")
        
        for placa in df_firmas_filtrado['PLACA'].unique():
            firmas_placa = df_firmas_filtrado[df_firmas_filtrado['PLACA'] == placa].sort_values('TIMESTAMP', ascending=False)
            
            with st.expander(f"📱 **{placa}** — {len(firmas_placa)} firma(s)"):
                for idx, firma in firmas_placa.iterrows():
                    st.markdown(f"""
                    **Timestamp:** {firma['TIMESTAMP']}  
                    **Usuario:** {firma['USUARIO']}  
                    **Conformidad:** {firma['CONFORMIDAD']}  
                    **Observaciones:** {firma['OBSERVACIONES'] if firma['OBSERVACIONES'] else 'Sin observaciones'}
                    """)
                    
                    if firma['FIRMA_BASE64']:
                        img_firma = decodificar_firma(firma['FIRMA_BASE64'])
                        if img_firma:
                            st.image(img_firma, caption=f"Firma de {firma['USUARIO']}", width=300)
                    
                    st.markdown("---")
        
        st.write("---")
        csv_firmas = df_firmas_filtrado.drop(columns=['FIRMA_BASE64']).to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "⬇️ Descargar Historial Completo (Sin imágenes)",
            data=csv_firmas,
            file_name=f"firmas_historial_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    else:
        st.info("📭 Aún no hay firmas registradas. Dirígete a la pestaña 'Validación y Firma de Actas' para capturar una.")

st.markdown("<div class='footer'>Sistemas e Infraestructura · Kenzo Jeans SAS</div>", unsafe_allow_html=True)
