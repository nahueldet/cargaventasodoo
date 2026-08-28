import streamlit as st
import xmlrpc.client
import base64
from datetime import date
import qrcode
from io import BytesIO
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner

# Configuración básica de la página
st.set_page_config(page_title="Gestión de Taller", page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")

# --- CONTROL DE ESTADO (Para reiniciar la app después de cargar) ---
if 'orden_exitosa' not in st.session_state:
    st.session_state.orden_exitosa = False
if 'num_orden_generada' not in st.session_state:
    st.session_state.num_orden_generada = ""
if 'qr_base64' not in st.session_state:
    st.session_state.qr_base64 = ""

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
    div.stButton > button:first-child:hover { transform: translateY(-3px); box-shadow: 0 12px 20px rgba(106, 27, 154, 0.4); }
    h1, h2, h3 { font-family: 'Inter', sans-serif; color: #1e293b; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO ---
st.title("⚡ Gestión de Taller")

# --- CREDENCIALES ---
URL_CRUDA = st.secrets["ODOO_URL"]
URL = URL_CRUDA.split('/odoo')[0].rstrip('/')
DB = st.secrets["ODOO_DB"]
USER = st.secrets["ODOO_USER"]
PASSWORD = st.secrets["ODOO_PASSWORD"]

# --- FUNCIONES DE CONEXIÓN ---
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
    except Exception: return ["Nahuel de Titto", "Taller 1"]

with st.spinner("Sincronizando base de datos..."):
    lista_clientes = obtener_clientes()
    lista_empleados = obtener_empleados()

opciones_clientes = ["Seleccionar...", "➕ CREAR NUEVO CLIENTE"] + lista_clientes
opciones_empleados = ["Seleccionar..."] + lista_empleados

# ==========================================
# PESTAÑAS (MÓDULOS)
# ==========================================
tab1, tab2 = st.tabs(["📦 Ingreso de Material", "⏱️ Carga de Horas"])

# ------------------------------------------
# MÓDULO 1: INGRESO DE MATERIAL 
# ------------------------------------------
with tab1:
    if not st.session_state.orden_exitosa:
        st.markdown("### 🏢 Datos Comerciales")
        with st.container(border=True):
            empleado = st.selectbox("Recepcionista (Técnico interno)", opciones_empleados, key="recepcion_emp")
            cliente_seleccionado = st.selectbox("Empresa / Cliente a facturar", opciones_clientes)
            
            cliente_final = ""
            telefono_final = ""
            es_cliente_nuevo = False
            
            if cliente_seleccionado == "➕ CREAR NUEVO CLIENTE":
                st.markdown("<p style='color:#8e24aa; font-weight:bold; font-size:14px;'>Nuevo Registro</p>", unsafe_allow_html=True)
                cliente_final = st.text_input("Razón Social")
                telefono_final = st.text_input("Teléfono (Opcional)")
                es_cliente_nuevo = True
            else:
                cliente_final = cliente_seleccionado

        st.markdown("### ⚙️ Especificaciones")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1: persona_deja_trabajo = st.text_input("Traído por (Chofer)")
            with col2: fecha_entrega = st.date_input("Fecha Prometida", value=date.today())
                
            trabajo = st.text_input("Descripción (Ej: Corte EDM)")
            foto_adjunta = st.file_uploader("Evidencia fotográfica", type=['jpg', 'jpeg', 'png'])
            if foto_adjunta is not None:
                st.image(foto_adjunta, caption="Archivo listo", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Enviar Orden al Taller", type="primary"):
            if empleado == "Seleccionar...": st.error("⚠️ Faltan datos.")
            elif cliente_seleccionado == "Seleccionar...": st.error("⚠️ Faltan datos.")
            elif not trabajo: st.error("⚠️ Describa el trabajo.")
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
                             
                        observaciones = f"=== INGRESO DE MATERIAL ===\nRecepcionado por: {empleado}\nTraído por: {persona_deja_trabajo if persona_deja_trabajo else 'No especificado'}\n"
                        
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
                        
                        # --- GENERAR QR OPTIMIZADO PARA ETIQUETA ---
                        qr = qrcode.QRCode(version=1, box_size=10, border=1) # Borde reducido a 1 para maximizar tamaño
                        qr.add_data(orden[0]['name'])
                        qr.make(fit=True)
                        img_qr = qr.make_image(fill_color="black", back_color="white")
                        
                        buf = BytesIO()
                        img_qr.save(buf, format="PNG")
                        qr_base64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                        
                        st.session_state.num_orden_generada = orden[0]['name']
                        st.session_state.qr_base64 = qr_base64_str
                        st.session_state.orden_exitosa = True
                        
                        if es_cliente_nuevo: obtener_clientes.clear()
                        st.rerun()
                                
                    except Exception as e:
                        st.error(f"Error: {e}")

    # PANTALLA DE IMPRESIÓN (50x40mm)
    else:
        st.balloons()
        st.success(f"✅ ¡Ingreso Registrado! Orden **{st.session_state.num_orden_generada}**.")
        
        st.info("La ventana de impresión debería abrirse automáticamente. Pegue esta etiqueta en las piezas.")
        
        # HTML INYECTADO ESTRICTO PARA 50mm x 40mm
        html_etiqueta = f"""
        <html>
            <head>
                <style>
                    /* Reset general para evitar márgenes fantasmas */
                    body {{ 
                        font-family: 'Arial', sans-serif; 
                        text-align: center; 
                        margin: 0; 
                        padding: 0; 
                        background-color: white; 
                        color: black;
                    }}
                    
                    /* Tamaños relativos al lienzo de 50x40 */
                    h1 {{ 
                        font-size: 16px; 
                        margin: 2mm 0 0 0; 
                        letter-spacing: 1px; 
                    }}
                    p {{ 
                        font-size: 10px; 
                        margin: 0 0 1mm 0; 
                        font-weight: bold; 
                    }}
                    img {{ 
                        width: 25mm; /* Tamaño físico del QR */
                        height: 25mm; 
                        display: block; 
                        margin: 0 auto; 
                    }}

                    /* MAGIA NEGRA PARA LA IMPRESORA TÉRMICA */
                    @media print {{
                        @page {{
                            size: 50mm 40mm; /* Fuerza al navegador a usar este papel */
                            margin: 0mm;     /* Elimina márgenes blancos del navegador */
                        }}
                        body {{
                            width: 50mm;
                            height: 40mm;
                            overflow: hidden; /* Evita que imprima hojas en blanco extra */
                        }}
                    }}
                </style>
            </head>
            <body onload="setTimeout(() => {{ window.print(); }}, 800)">
                <h1>{st.session_state.num_orden_generada}</h1>
                <p>TALLER</p>
                <img src="data:image/png;base64,{st.session_state.qr_base64}" />
            </body>
        </html>
        """
        # Renderiza el marco visual. Mantenemos el height para que se vea en la web
        components.html(html_etiqueta, height=200)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Cargar un Nuevo Trabajo", type="primary"):
            st.session_state.orden_exitosa = False
            st.session_state.num_orden_generada = ""
            st.session_state.qr_base64 = ""
            st.rerun()

# ------------------------------------------
# MÓDULO 2: CARGA DE HORAS Y NOTAS
# ------------------------------------------
with tab2:
    st.markdown("### 🔍 Buscar Orden")
    qr_code_scanned = qrcode_scanner(key='scanner')
    texto_busqueda_inicial = qr_code_scanned if qr_code_scanned else ""

    busqueda = st.text_input("Ingrese Nro de Orden (Ej: SO0045) o descripción", value=texto_busqueda_inicial, key="input_busqueda")
    
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
                                                [[['id', 'in', all_ids]]], {'fields': ['id', 'name', 'partner_id']})
                    
                    opciones_ord = {f"{o['name']} - Cliente: {o['partner_id'][1]}": o['id'] for o in ordenes}
                    
                    with st.container(border=True):
                        orden_seleccionada = st.selectbox("Seleccione la orden:", list(opciones_ord.keys()))
                        orden_id = opciones_ord[orden_seleccionada]
                        
                        lineas_orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                         [[['order_id', '=', orden_id]]], {'fields': ['name', 'display_type']})
                        
                        trabajos_disponibles = []
                        for linea in lineas_orden:
                             if linea.get('display_type') == 'line_section' or not linea.get('display_type'):
                                 if linea.get('name'): trabajos_disponibles.append(linea['name'])
                        
                        if not trabajos_disponibles: trabajos_disponibles = ["Trabajo General de la Orden"]
                        trabajo_a_imputar = st.selectbox("¿A qué trabajo o pieza le cargará las horas?", trabajos_disponibles)
                                
                    st.markdown("### ⏱️ Registrar Avance")
                    with st.form("form_horas", clear_on_submit=True):
                        tec = st.selectbox("Técnico", opciones_empleados)
                        colA, colB = st.columns(2)
                        with colA: dia_trabajo = st.date_input("Día del trabajo", value=date.today())
                        with colB: horas_trabajadas = st.number_input("Horas utilizadas", min_value=0.0, step=0.25, value=1.0)
                            
                        notas_extra = st.text_area("Notas / Observaciones de lo que se hizo")
                        submit_horas = st.form_submit_button("Guardar Registro", type="primary")
                        
                        if submit_horas:
                            if tec == "Seleccionar...": st.error("⚠️ Seleccione al técnico.")
                            elif horas_trabajadas <= 0: st.error("⚠️ Las horas deben ser mayor a 0.")
                            else:
                                texto_registro = f"⏱️ HORAS ({tec}): {horas_trabajadas} hs | Fecha: {dia_trabajo.strftime('%d/%m/%Y')}"
                                texto_registro += f"\n👉 Trabajo realizado en: {trabajo_a_imputar}"
                                if notas_extra: texto_registro += f"\n📝 Notas Técnicas: {notas_extra}"
                                    
                                models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{
                                    'order_id': orden_id, 'display_type': 'line_note', 'name': texto_registro              
                                }])
                                st.success("✅ ¡Horas anexadas exitosamente a la orden!")
                else:
                    st.warning("No se encontraron órdenes ni trabajos con esa búsqueda.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
