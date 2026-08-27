import streamlit as st
import xmlrpc.client
import base64
from datetime import date
import qrcode
from io import BytesIO
from streamlit_qrcode_scanner import qrcode_scanner

# Configuración básica de la página
st.set_page_config(
    page_title="Gestión de Taller", 
    page_icon="⚡", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS SÚPER MODERNOS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp { background-color: #F4F6F9; }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border: none !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 24px rgba(149, 157, 165, 0.15) !important;
        padding: 5px;
    }

    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="textarea"] > div {
        background-color: #f8f9fa !important;
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within, div[data-baseweb="textarea"] > div:focus-within {
        border-color: #8e24aa !important;
        box-shadow: 0 0 0 2px rgba(142, 36, 170, 0.2) !important;
        background-color: #ffffff !important;
    }

    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6a1b9a 0%, #ab47bc 100%);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 12px 24px;
        font-size: 18px;
        font-weight: 600;
        width: 100%;
        box-shadow: 0 8px 16px rgba(106, 27, 154, 0.25);
        transition: all 0.3s ease;
    }
    
    div.stButton > button:first-child:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 20px rgba(106, 27, 154, 0.4);
    }
    
    h1, h2, h3 {
        font-family: 'Inter', -apple-system, sans-serif;
        color: #1e293b;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO ---
st.title("⚡ Gestión de Taller")

# --- LIMPIEZA AUTOMÁTICA DE URL ---
URL_CRUDA = st.secrets["ODOO_URL"]
URL = URL_CRUDA.split('/odoo')[0].rstrip('/')
DB = st.secrets["ODOO_DB"]
USER = st.secrets["ODOO_USER"]
PASSWORD = st.secrets["ODOO_PASSWORD"]

# --- FUNCIONES DE CONEXIÓN (Caché) ---
@st.cache_data(ttl=300)
def obtener_clientes():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        clientes_data = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search_read', 
            [[['active', '=', True]]], {'fields': ['name'], 'order': 'name asc'})
        return [c['name'] for c in clientes_data if c['name']]
    except Exception: return []

@st.cache_data(ttl=300)
def obtener_empleados():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        empleados_data = models.execute_kw(DB, uid, PASSWORD, 'hr.employee', 'search_read', 
            [], {'fields': ['name'], 'order': 'name asc'})
        return [e['name'] for e in empleados_data if e['name']]
    except Exception: return ["Nahuel De Titto", "Técnico 1", "Técnico 2"]

with st.spinner("Sincronizando base de datos..."):
    lista_clientes = obtener_clientes()
    lista_empleados = obtener_empleados()

opciones_clientes = ["Seleccionar...", "➕ CREAR NUEVO CLIENTE"] + lista_clientes
opciones_empleados = ["Seleccionar..."] + lista_empleados

# ==========================================
# CREACIÓN DE PESTAÑAS (MÓDULOS)
# ==========================================
tab1, tab2 = st.tabs(["📦 Ingreso de Material", "⏱️ Carga de Horas"])

# ------------------------------------------
# MÓDULO 1: INGRESO DE MATERIAL 
# ------------------------------------------
with tab1:
    st.markdown("### 🏢 Datos Comerciales")
    with st.container(border=True):
        empleado = st.selectbox("Recepcionista (Técnico interno)", opciones_empleados, key="recepcion_emp")
        cliente_seleccionado = st.selectbox("Empresa / Cliente a facturar", opciones_clientes)
        
        cliente_final = ""
        telefono_final = ""
        es_cliente_nuevo = False
        
        if cliente_seleccionado == "➕ CREAR NUEVO CLIENTE":
            st.markdown("<p style='color:#8e24aa; font-weight:bold; font-size:14px;'>Nuevo Registro Comercial</p>", unsafe_allow_html=True)
            cliente_final = st.text_input("Razón Social o Nombre Completo")
            telefono_final = st.text_input("Teléfono de Contacto (Opcional)")
            es_cliente_nuevo = True
        else:
            cliente_final = cliente_seleccionado

    st.markdown("### ⚙️ Especificaciones del Trabajo")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            persona_deja_trabajo = st.text_input("Traído por (Chofer/Dueño)")
        with col2:
            fecha_entrega = st.date_input("Fecha Prometida", value=date.today(), key="fecha_promesa")
            
        trabajo = st.text_input("Descripción del Trabajo (Ej: Corte EDM, Fresado)")
        foto_adjunta = st.file_uploader("Evidencia fotográfica", type=['jpg', 'jpeg', 'png'])
        
        if foto_adjunta is not None:
            st.image(foto_adjunta, caption="Archivo listo para adjuntar", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Enviar Orden al Taller", type="primary", key="btn_ingreso"):
        if empleado == "Seleccionar...": st.error("⚠️ Indique quién recibe el trabajo.")
        elif cliente_seleccionado == "Seleccionar...": st.error("⚠️ Seleccione un cliente.")
        elif not trabajo: st.error("⚠️ Describa el trabajo a realizar.")
        else:
            with st.spinner("Procesando en Odoo..."):
                try:
                    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                    uid = common.authenticate(DB, USER, PASSWORD, {})
                    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                    
                    if es_cliente_nuevo:
                        datos_nuevo = {'name': cliente_final, 'is_company': True}
                        if telefono_final: datos_nuevo['phone'] = telefono_final
                        cliente_id_odoo = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'create', [datos_nuevo])
                    else:
                        cliente_busqueda = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', '=', cliente_final]]], {'limit': 1})
                        cliente_id_odoo = cliente_busqueda[0] if cliente_busqueda else False
                         
                    observaciones = f"=== INGRESO DE MATERIAL ===\nRecepcionado por: {empleado}\nPersona que entrega: {persona_deja_trabajo if persona_deja_trabajo else 'No especificado'}\n"
                    
                    orden_id = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'create', [{
                        'partner_id': cliente_id_odoo,
                        'commitment_date': fecha_entrega.strftime("%Y-%m-%d"),
                        'note': observaciones
                    }])
                    
                    models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{
                        'order_id': orden_id, 'display_type': 'line_section', 'name': trabajo              
                    }])
                    
                    if foto_adjunta is not None:
                        foto_base64 = base64.b64encode(foto_adjunta.read()).decode('utf-8')
                        models.execute_kw(DB, uid, PASSWORD, 'ir.attachment', 'create', [{
                            'name': f"Ingreso_{trabajo}.jpg", 'type': 'binary', 'datas': foto_base64,
                            'res_model': 'sale.order', 'res_id': orden_id         
                        }])

                    orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', [[orden_id]], {'fields': ['name']})
                    num_orden = orden[0]['name']
                    
                    st.balloons()
                    st.success(f"📦 ¡Ingreso Registrado! Orden **{num_orden}** creada.")
                    
                    # --- GENERAR Y MOSTRAR CÓDIGO QR ---
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(num_orden) # El QR solo contiene el número de orden, ej: SO0045
                    qr.make(fit=True)

                    img_qr = qr.make_image(fill_color="black", back_color="white")
                    
                    # Mostrar el QR en la pantalla para que puedan imprimirlo o escanearlo
                    st.markdown("### 📷 Código QR de la Orden")
                    st.markdown("Este código identifica el trabajo ingresado. Guarde esta imagen o imprímala para adjuntar a las piezas.")
                    
                    buf = BytesIO()
                    img_qr.save(buf, format="PNG")
                    st.image(buf, caption=f"QR Orden: {num_orden}", width=250)

                    if es_cliente_nuevo: obtener_clientes.clear()
                            
                except Exception as e:
                    st.error(f"Falla de sincronización: {e}")

# ------------------------------------------
# MÓDULO 2: CARGA DE HORAS Y NOTAS
# ------------------------------------------
with tab2:
    st.markdown("### 🔍 Buscar Orden")
    st.markdown("Puede buscar ingresando texto, o usar la cámara para escanear el QR generado al ingreso.")
    
    # Opción para escanear QR usando la cámara web/celular
    qr_code_scanned = qrcode_scanner(key='scanner')
    
    # Si se escaneó un código QR, el buscador se autocompleta. Si no, queda vacío para escribir.
    texto_busqueda_inicial = qr_code_scanned if qr_code_scanned else ""

    busqueda = st.text_input("Ingrese Nro de Orden (Ej: S0045) o descripción", value=texto_busqueda_inicial, key="input_busqueda")
    
    if busqueda:
        with st.spinner("Buscando en el sistema..."):
            try:
                common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                uid = common.authenticate(DB, USER, PASSWORD, {})
                models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                
                so_ids = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [[['name', 'ilike', busqueda]]])
                lineas = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', [[['name', 'ilike', busqueda]]], {'fields': ['order_id']})
                line_so_ids = [line['order_id'][0] for line in lineas if line.get('order_id')]
                
                all_ids = list(set(so_ids + line_so_ids))
                
                if all_ids:
                    ordenes = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_read', 
                                                [[['id', 'in', all_ids]]], 
                                                {'fields': ['id', 'name', 'partner_id']})
                    
                    opciones_ord = {f"{o['name']} - Cliente: {o['partner_id'][1]}": o['id'] for o in ordenes}
                    
                    with st.container(border=True):
                        orden_seleccionada = st.selectbox("Seleccione la orden:", list(opciones_ord.keys()))
                        orden_id = opciones_ord[orden_seleccionada]
                        
                        lineas_orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                         [[['order_id', '=', orden_id]]], 
                                                         {'fields': ['name', 'display_type']})
                        
                        trabajos_disponibles = []
                        for linea in lineas_orden:
                             if linea.get('display_type') == 'line_section' or not linea.get('display_type'):
                                 if linea.get('name'):
                                     trabajos_disponibles.append(linea['name'])
                        
                        if not trabajos_disponibles:
                            trabajos_disponibles = ["Trabajo General de la Orden"]
                            
                        trabajo_a_imputar = st.selectbox("¿A qué trabajo o pieza le cargará las horas?", trabajos_disponibles)
                                
                    # Formulario para registrar las horas
                    st.markdown("### ⏱️ Registrar Avance")
                    with st.form("form_horas"):
                        tec = st.selectbox("Técnico", opciones_empleados, key="tec_horas")
                        
                        colA, colB = st.columns(2)
                        with colA:
                            dia_trabajo = st.date_input("Día del trabajo", value=date.today())
                        with colB:
                            horas_trabajadas = st.number_input("Horas utilizadas", min_value=0.0, step=0.25, value=1.0)
                            
                        notas_extra = st.text_area("Notas / Observaciones de lo que se hizo")
                        
                        submit_horas = st.form_submit_button("Guardar Registro", type="primary")
                        
                        if submit_horas:
                            if tec == "Seleccionar...":
                                st.error("⚠️ Seleccione al técnico.")
                            elif horas_trabajadas <= 0:
                                st.error("⚠️ Las horas deben ser mayor a 0.")
                            else:
                                texto_registro = f"⏱️ HORAS ({tec}): {horas_trabajadas} hs | Fecha: {dia_trabajo.strftime('%d/%m/%Y')}"
                                texto_registro += f"\n👉 Trabajo realizado en: {trabajo_a_imputar}"
                                if notas_extra:
                                    texto_registro += f"\n📝 Notas Técnicas: {notas_extra}"
                                    
                                models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{
                                    'order_id': orden_id,
                                    'display_type': 'line_note', 
                                    'name': texto_registro              
                                }])
                                
                                st.success("✅ ¡Horas anexadas exitosamente a la orden!")
                else:
                    st.warning("No se encontraron órdenes ni trabajos con esa búsqueda.")
                    
            except Exception as e:
                st.error(f"Error de conexión: {e}")
                    
            except Exception as e:
                st.error(f"Error de conexión: {e}")
