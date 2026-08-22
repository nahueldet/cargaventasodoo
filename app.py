import streamlit as st
import xmlrpc.client
import base64
from datetime import date

# Configuración básica de la página
st.set_page_config(
    page_title="Recepción de Trabajos", 
    page_icon="⚡", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS SÚPER MODERNOS ---
st.markdown("""
<style>
    /* 1. Ocultar elementos de Streamlit para efecto de App Nativa */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 2. Fondo general de la aplicación (Gris azulado muy suave) */
    .stApp {
        background-color: #F4F6F9;
    }
    
    /* 3. Estilo de las "Tarjetas" (Contenedores con borde) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border: none !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 24px rgba(149, 157, 165, 0.15) !important; /* Sombra suave elegante */
        padding: 5px;
        transition: transform 0.2s ease-in-out;
    }

    /* 4. Estilo moderno para Cajas de Texto y Selectores */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #f8f9fa !important;
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
        transition: all 0.3s ease;
    }
    
    /* Efecto "Glow" (Brillo) violeta al tocar una caja para escribir */
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within {
        border-color: #8e24aa !important;
        box-shadow: 0 0 0 2px rgba(142, 36, 170, 0.2) !important;
        background-color: #ffffff !important;
    }

    /* 5. Botón principal: Degradado moderno y animación 3D flotante */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6a1b9a 0%, #ab47bc 100%); /* Degradado violeta */
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
    
    /* Al pasar el mouse / dedo por el botón (se levanta) */
    div.stButton > button:first-child:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 20px rgba(106, 27, 154, 0.4);
    }
    
    /* Al hacer click (se hunde) */
    div.stButton > button:first-child:active {
        transform: translateY(1px);
        box-shadow: 0 4px 8px rgba(106, 27, 154, 0.2);
    }

    /* 6. Tipografías más limpias */
    h1, h2, h3 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1e293b;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO ---
st.title("⚡ Recepción Taller")
st.markdown("<p style='text-align: left; color: #64748b; margin-top: -15px; margin-bottom: 30px;'>Carga de órdenes de trabajo para Odoo</p>", unsafe_allow_html=True)

# --- LIMPIEZA AUTOMÁTICA DE URL ---
URL_CRUDA = st.secrets["ODOO_URL"]
URL = URL_CRUDA.split('/odoo')[0].rstrip('/')

DB = st.secrets["ODOO_DB"]
USER = st.secrets["ODOO_USER"]
PASSWORD = st.secrets["ODOO_PASSWORD"]

# --- FUNCIONES DE CONEXIÓN CON ODOO ---
@st.cache_data(ttl=300)
def obtener_clientes():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        clientes_data = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search_read', 
            [[['active', '=', True]]], {'fields': ['name'], 'order': 'name asc'})
        return [c['name'] for c in clientes_data if c['name']]
    except Exception:
        return []

@st.cache_data(ttl=300)
def obtener_empleados():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        empleados_data = models.execute_kw(DB, uid, PASSWORD, 'hr.employee', 'search_read', 
            [], {'fields': ['name'], 'order': 'name asc'})
        return [e['name'] for e in empleados_data if e['name']]
    except Exception:
        return ["Nahuel de Titto", "Taller 1", "Ventas"]

with st.spinner("Sincronizando base de datos..."):
    lista_clientes = obtener_clientes()
    lista_empleados = obtener_empleados()

opciones_clientes = ["Seleccionar...", "➕ CREAR NUEVO CLIENTE"] + lista_clientes
opciones_empleados = ["Seleccionar..."] + lista_empleados

# --- INTERFAZ VISUAL (AHORA CON TARJETAS BLANCAS) ---

st.markdown("### 🏢 Datos Comerciales")
with st.container(border=True): # ESTO CREA LA TARJETA 1
    empleado = st.selectbox("Recepcionista (Técnico interno)", opciones_empleados)
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

st.markdown("<br>", unsafe_allow_html=True) # Espaciador

st.markdown("### ⚙️ Especificaciones del Trabajo")
with st.container(border=True): # ESTO CREA LA TARJETA 2
    col1, col2 = st.columns(2)
    with col1:
        persona_deja_trabajo = st.text_input("Traído por (Chofer/Dueño)")
    with col2:
        fecha_entrega = st.date_input("Fecha Prometida", value=date.today())
        
    trabajo = st.text_input("Descripción del Trabajo (Ej: Corte EDM, Fresado)")
    foto_adjunta = st.file_uploader("Evidencia fotográfica del ingreso", type=['jpg', 'jpeg', 'png'])
    
    if foto_adjunta is not None:
        st.image(foto_adjunta, caption="Archivo listo para adjuntar", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True) # Espacio antes del botón

# --- BOTÓN DE ENVIAR ---
if st.button("🚀 Enviar Orden al Taller", type="primary"):
    
    if empleado == "Seleccionar...":
        st.error("⚠️ Faltan datos: Indique quién está recibiendo el trabajo.")
    elif cliente_seleccionado == "Seleccionar...":
        st.error("⚠️ Faltan datos: Seleccione o cree un cliente.")
    elif es_cliente_nuevo and not cliente_final:
        st.error("⚠️ Faltan datos: El nombre del nuevo cliente no puede estar vacío.")
    elif not trabajo:
        st.error("⚠️ Faltan datos: Describa brevemente el trabajo a realizar.")
    else:
        with st.spinner("Procesando y conectando con Odoo..."):
            try:
                common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                uid = common.authenticate(DB, USER, PASSWORD, {})
                models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                
                # 1. Crear o Buscar Cliente
                if es_cliente_nuevo:
                    datos_nuevo = {'name': cliente_final, 'is_company': True}
                    if telefono_final:
                        datos_nuevo['phone'] = telefono_final
                    cliente_id_odoo = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'create', [datos_nuevo])
                else:
                    cliente_busqueda = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', 
                        [[['name', '=', cliente_final]]], {'limit': 1})
                    cliente_id_odoo = cliente_busqueda[0] if cliente_busqueda else False
                    
                if not cliente_id_odoo:
                     st.error("Error crítico: Imposible verificar la ficha del cliente en el ERP.")
                     st.stop()
                     
                # 2. Armar Observaciones
                observaciones = f"=== INGRESO DE MATERIAL ===\n"
                observaciones += f"Recepcionado por: {empleado}\n"
                observaciones += f"Persona que entrega: {persona_deja_trabajo if persona_deja_trabajo else 'No especificado'}\n"
                
                # 3. CREAR ORDEN DE VENTA
                fecha_str = fecha_entrega.strftime("%Y-%m-%d")
                orden_id = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'create', [{
                    'partner_id': cliente_id_odoo,
                    'commitment_date': fecha_str,
                    'note': observaciones
                }])
                
                # 4. CREAR SECCIÓN
                linea_seccion = {
                    'order_id': orden_id,
                    'display_type': 'line_section', 
                    'name': trabajo              
                }
                models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [linea_seccion])
                
                # 5. SUBIR FOTO ADJUNTA
                if foto_adjunta is not None:
                    foto_bytes = foto_adjunta.read()
                    foto_base64 = base64.b64encode(foto_bytes).decode('utf-8')
                    adjunto_data = {
                        'name': f"Ingreso_{trabajo}.jpg",
                        'type': 'binary',
                        'datas': foto_base64,
                        'res_model': 'sale.order', 
                        'res_id': orden_id         
                    }
                    models.execute_kw(DB, uid, PASSWORD, 'ir.attachment', 'create', [adjunto_data])

                # 6. ÉXITO FINAL
                orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', 
                    [[orden_id]], {'fields': ['name']})
                num_orden = orden[0]['name']
                
                st.balloons()
                st.success(f"📦 ¡Ingreso Registrado con Éxito! Orden **{num_orden}** creada.")
                
                if es_cliente_nuevo:
                    obtener_clientes.clear()
                        
            except Exception as e:
                st.error(f"Falla de sincronización: {e}")
