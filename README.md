# Gestión y Control de Mantenimiento de Equipos de Sistemas (SGTI) – Kenzo Jeans

Aplicación para registrar, consultar y hacer seguimiento a los mantenimientos preventivos y correctivos de los equipos de tecnología de la información (computadores y periféricos) de Kenzo Jeans, tanto en almacenes como en áreas administrativas.

## Propósito

- Reemplazar el acta de mantenimiento en papel por un registro digital con soporte fotográfico.
- Llevar el historial de cada equipo y de cada área o almacén.
- Alertar sobre los mantenimientos próximos o vencidos.
- Generar el acta en PDF y exportar los datos a Excel o CSV.

## Cómo funciona

```
Aplicación (formulario)  →  Google Apps Script (webhook)  →  Hoja de cálculo "Form_Responses"  →  Aplicación (dashboard)
```

1. El analista diligencia el formulario dentro de la aplicación (pestaña **Nuevo Mantenimiento**) y adjunta la foto del acta firmada.
2. La aplicación envía el registro a un **webhook** (Google Apps Script), que lo guarda en la hoja de cálculo.
3. El dashboard lee esa misma hoja (pestaña `Form_Responses`) y se actualiza solo cada 60 segundos.

> **Pieza fuera de este repositorio:** el código del Apps Script que recibe y guarda los registros no está aquí. Debe documentarse en otro lugar: `[completar: dónde está, en qué cuenta de Google, quién puede editarlo y cómo se vuelve a desplegar]`.

## Pestañas de la aplicación

| Pestaña | Qué hace |
|---|---|
| 📝 **Nuevo Mantenimiento** | Formulario de registro en 7 secciones, con foto del soporte |
| 📊 **Dashboard de Gestión** | Indicadores, alertas de próximo mantenimiento, resumen por área y gráficas |
| 📋 **Datos Completos** | Tabla completa con descarga en CSV y Excel (sin la foto) |
| 📄 **Historial de Soportes** | Cada acta con su detalle, la foto del soporte y descarga en PDF; con búsqueda y paginación |

### Formulario de registro

1. **Información general del equipo:** fecha, usuario responsable, cargo, tipo de área (almacén o administrativo), área, placas, marca/modelo y número de serie.
2. **Condiciones iniciales del equipo** (lista de ítems revisados al recibirlo).
3. **Actividades realizadas:** limpieza, pruebas de funcionamiento, respaldo y seguridad, revisión eléctrica y electrónica, optimización.
4. **Hallazgos.**
5. **Repuestos y materiales.**
6. **Recomendaciones.**
7. **Validación:** estado posterior (`Óptimo`, `Requiere seguimiento`, `En falla`), analista responsable y fecha del próximo mantenimiento (por defecto, 180 días).

Campos obligatorios: placas, usuario responsable, área, analista y foto del soporte. Los textos se guardan en mayúsculas.

### Foto del soporte

Se puede tomar con la cámara o subir desde el computador. La foto se endereza y se **comprime** hasta que, convertida a texto (base64), quepa en una celda de Google Sheets (límite de 50.000 caracteres; el código usa 45.000, constante `MAX_B64_CHARS`).

> Por compatibilidad con el Apps Script y la hoja, la foto se envía en el campo `firma_base64` (nombre heredado de cuando se usaba un pad de firma). No renombrar sin actualizar también el Apps Script y la columna de la hoja.

### Dashboard

- **Indicadores:** mantenimientos realizados, equipos diferentes, áreas atendidas y % de equipos óptimos (estados que contienen `Óptimo`, `Optimo` u `Operativo`).
- **Alertas de próximo mantenimiento por área o almacén:** para cada área se toma la **última visita** (fecha de mantenimiento más reciente) y, de esa visita, la fecha de próximo mantenimiento más cercana. Se clasifica así:

| Estado | Condición |
|---|---|
| 🔴 Vencido | Fecha ya pasada |
| 🟠 Próximo | 15 días o menos |
| 🟡 Próximo | Entre 16 y 30 días |
| 🟢 Al día | Más de 30 días |

  Las alertas respetan el filtro de área, pero **no** el de fechas.
- **Resumen por área:** total de mantenimientos, % óptimo y fecha del último.
- **Gráficas:** mantenimientos por área, distribución del estado de los equipos, áreas con más incidencias (cualquier estado distinto de óptimo), ítems más frecuentes de las condiciones iniciales y evolución mensual.
- **Equipos con más de una intervención** (posibles candidatos a reemplazo).

Filtros en la barra lateral: rango de fechas y área o departamento.

## Datos que envía el formulario

Campos que recibe el webhook (en formato JSON): `fecha_mantenimiento`, `usuario`, `cargo`, `area`, `placas`, `marca_modelo`, `num_serie`, `condiciones_iniciales`, `act_limpieza`, `act_revision_elec`, `act_pruebas`, `act_optimizacion`, `act_respaldo`, `hallazgos`, `repuestos`, `recomendaciones`, `validacion_estado`, `analista`, `proximo_mantenimiento` y `firma_base64`. El registro se considera guardado si la respuesta del webhook contiene la palabra `success`.

## Cómo se leen las columnas de la hoja

Los encabezados se pasan a mayúsculas y se identifican por palabra clave: `FECHA` (la primera columna que la contenga), `ÁREA`/`AREA`, `PLACA`, `ESTADO`, `CONDICIONES_INICIALES`, `PROXIMO`/`PRÓXIMO`, `USUARIO` y `FIRMA`. Si se renombran columnas en la hoja, hay que verificar que conserven esas palabras.

## Datos que se editan en el código

- `AREAS_ALMACENES`: lista cerrada de almacenes y sedes. El analista solo puede elegir de la lista, para evitar nombres duplicados o mal escritos.
- `AREAS_ADMINISTRATIVOS`: lista cerrada de áreas administrativas.
- Lista de **analistas responsables** (con la opción "Otro"), en la sección 7 del formulario.
- **Al abrir o cerrar un almacén, o renombrar un área, hay que actualizar la lista correspondiente.** Un nombre que no esté en la lista no se puede registrar.

## Limitaciones conocidas

- **`PLACAS` es texto libre.** Se escribe distinto en cada visita (varios equipos, distinto orden o formato), por eso "Equipos diferentes" y "Equipos con más intervenciones" son aproximados.
- La gráfica "Hallazgos más frecuentes" cuenta los ítems marcados en **condiciones iniciales** (lo que se revisó al recibir el equipo), no lo escrito en la sección de hallazgos.
- La foto en base64 hace que la hoja crezca rápido; si el volumen aumenta, conviene guardar las fotos en Drive y dejar solo el enlace en la hoja.

## Tecnologías y dependencias

Python con Streamlit, Pandas, Plotly, Requests, Pillow, ReportLab (acta en PDF) y openpyxl (Excel).

> Completar: confirmar que `requirements.txt` incluya `streamlit`, `pandas`, `plotly`, `requests`, `pillow`, `reportlab` y `openpyxl`.

## Configuración y despliegue

La dirección del webhook se lee del secreto `webhook_url` (en `.streamlit/secrets.toml` en local, o en *Secrets* de Streamlit Cloud).

> Completar:

- **Archivo principal:** `[nombre del archivo, p. ej. app.py]`
- **Ejecutar en local:** `streamlit run [archivo].py`
- **Despliegue:** Streamlit Cloud, cuenta `[completar]`, URL `[completar]`
- **Hoja de cálculo (nombre y ubicación en Drive):** `[completar]`
- **Apps Script (nombre, cuenta propietaria y despliegue vigente):** `[completar]`

## Responsables

- **Dueño del proceso (Sistemas / Mesa de ayuda):** `[área / cargo]`
- **Mantenimiento técnico de la aplicación:** `[nombre / cargo]`
- **Cuentas (GitHub, Streamlit, Google):** `[a nombre de quién]`
