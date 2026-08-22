import streamlit as st
import xmlrpc.client
import base64
from datetime import date

# Configuración básica de la página
st.set_page_config(
    page_title="Recepción de Trabajos", 
    page_icon="🔧", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    /* Ocultar el menú de Streamlit arriba a la derecha y el footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Cambiar el color de fondo principal de la aplicación (opcional, gris muy claro) */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Estilizar el botón principal (Fondo violeta, texto blanco, bordes redondeados) */
    div.stButton > button:first-child {
        background-color: #6a1b9a; /* Violeta */
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 24px;
        font-size: 18px;
        font-weight: bold;
        width: 100%; /* Botón ancho para pantallas táctiles */
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        transition: 0.3s;
    }
    
    /* Efecto al pasar el mouse por encima del botón */
    div.stButton > button:first-child:hover {
        background-color: #8e24aa; /* Violeta más claro */
        box-shadow: 0px 6px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Estilo para las cajas de entrada de texto (sombra sutil) */
    .stTextInput > div > div > input, .stSelectbox > div > div > select {
        border-radius: 5px;
        border: 1px solid #ced4da;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.075);
    }
    
    /* Titulo principal de la app */
    h1 {
        color: #333333;
        text-align: center;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Subtitulos */
    h3 {
        color: #6a1b9a; /* Violeta */
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 5px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO ---
st.title("🔧 Recepción de Trabajos")
st.markdown("<p style='text-align: center; color: #666; margin-bottom: 30px;'>Carga rápida de órdenes para Odoo</p>", unsafe_allow_html=True)

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
            [[['active', '=', True]]], 
            {'fields': ['name'], 'order': 'name asc'})
        
        return [c['name'] for c in clientes_data if c['name']]
    except Exception as e:
        st.error(f"Error de conexión (Clientes): {e}")
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

# Cargamos las listas
with st.spinner("Sincronizando con Odoo..."):
    lista_clientes = obtener_clientes()
    lista_empleados = obtener_empleados()

opciones_clientes = ["Seleccionar...", "➕ CREAR NUEVO CLIENTE"] + lista_clientes
opciones_empleados = ["Seleccionar..."] + lista_empleados

# --- INTERFAZ VISUAL ---
st.subheader("1. Datos Comerciales")
empleado = st.selectbox("Recepcionista (Empleado interno)", opciones_empleados)

cliente_seleccionado = st.selectbox("Empresa / Cliente a facturar", opciones_clientes)

cliente_final = ""
telefono_final = ""
es_cliente_nuevo = False

if cliente_seleccionado == "➕ CREAR NUEVO CLIENTE":
    with st.container(border=True): # Agrega un recuadro alrededor de la creación de cliente
        st.markdown("**Nuevo Registro Comercial**")
        cliente_final = st.text_input("Razón Social o Nombre Completo")
        telefono_final = st.text_input("Teléfono de Contacto (Opcional)")
        es_cliente_nuevo = True
else:
    cliente_final = cliente_seleccionado


st.subheader("2. Especificaciones Técnicas")

# Agrupamos campos relacionados en columnas para ahorrar espacio en la pantalla
col1, col2 = st.columns(2)
with col1:
    persona_deja_trabajo = st.text_input("Entregado por (Chofer/Cadete)")
with col2:
    fecha_entrega = st.date_input("Fecha Prometida", value=date.today())

trabajo = st.text_input("Descripción del Trabajo (Ej: Torneado de piezas, Corte EDM)")

foto_adjunta = st.file_uploader("Evidencia fotográfica (Estado de ingreso)", type=['jpg', 'jpeg', 'png'])

if foto_adjunta is not None:
    st.image(foto_adjunta, caption="Archivo listo para adjuntar", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True) # Espacio en blanco antes del botón

# --- BOTÓN DE ENVIAR ---
if st.button("Enviar Orden al Taller", type="primary"):
    
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
                
                st.balloons() # Animación festiva de Streamlit
                st.success(f"📦 ¡Ingreso Registrado con Éxito! Número de Orden: **{num_orden}**")
                
                if es_cliente_nuevo:
                    obtener_clientes.clear()
                        
            except Exception as e:
                st.error(f"Falla de sincronización: {e}")
