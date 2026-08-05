# 2. FUNCIÓN DE CARGA DE DATOS (Ya vinculada a tu hoja real)
@st.cache_data(ttl=60)
def cargar_datos_mantenimiento():
    # ID exacto extraído de tu enlace
    ID_HOJA = "1hbXmOgYGoJ1vouSodHnh3nNB9kQQ6ST9EV8lIzd9-m4" 
    
    # IMPORTANTE: Revisa que la pestaña en tu Excel se llame exactamente así. 
    # Si le cambiaste el nombre (ej. "Mantenimientos"), cámbialo también aquí adentro:
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
        # Mensaje de error real en caso de que la hoja sea privada o cambie de nombre
        return pd.DataFrame(), f"Error al conectar con la hoja: {str(e)}"
