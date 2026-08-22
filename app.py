import streamlit as st
import xmlrpc.client
from datetime import date

# Configuración básica de la página
st.set_page_config(page_title="Carga de Órdenes", page_icon="⚙️")

st.title("Generador de Órdenes - Odoo")
st.write("Complete los datos para registrar la orden de venta en el sistema.")

# Las credenciales se llaman desde los "Secretos"
URL = st.secrets["ODOO_URL"]
DB = st.secrets["ODOO_DB"]
USER = st.secrets["ODOO_USER"]
PASSWORD = st.secrets["ODOO_PASSWORD"]

# --- NUEVA FUNCIÓN: Obtener clientes de Odoo ---
# El decorador cache_data guarda la lista por 5 minutos (300 segundos) para que la app no sea lenta
@st.cache_data(ttl=300)
def obtener_clientes():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        
        # Busca todos los contactos activos ordenados alfabéticamente
        clientes_data = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search_read', 
            [[['active', '=', True]]], 
            {'fields': ['name'], 'order': 'name asc'})
        
        # Extraemos solo los nombres, ignorando los que estén vacíos
        nombres = [c['name'] for c in clientes_data if c['name']]
        return nombres
    except Exception as e:
        st.error(f"Error al conectar con Odoo para cargar la lista de clientes: {e}")
        return []

# Cargamos la lista antes de mostrar la interfaz
with st.spinner("Cargando base de datos de clientes..."):
    lista_clientes = obtener_clientes()

# Preparamos las opciones del menú desplegable (Buscador)
opciones_desplegable = ["Seleccionar...", "➕ CREAR NUEVO CLIENTE"] + lista_clientes

# --- INTERFAZ VISUAL ---
st.subheader("Datos de la Orden")
empleado = st.selectbox("Seleccione su nombre", ["Seleccionar...", "Juan", "Pedro", "María", "Nahuel de Titto"])

# El selectbox de Streamlit permite hacer clic y tipear para buscar en la lista
cliente_seleccionado = st.selectbox("Buscar Cliente en Base de Datos", opciones_desplegable)

# Variables que usaremos para enviar a Odoo
cliente_final = ""
telefono_final = ""
es_cliente_nuevo = False

# LÓGICA DINÁMICA: Si elige crear nuevo, mostramos los campos extra de inmediato
if cliente_seleccionado == "➕ CREAR NUEVO CLIENTE":
    st.info("Complete los datos del nuevo cliente:")
    cliente_final = st.text_input("Nombre de la Empresa o Cliente")
    telefono_final = st.text_input("Teléfono (Opcional - Para avisos)")
    es_cliente_nuevo = True
else:
    # Si eligió un cliente existente de la lista
    cliente_final = cliente_seleccionado

referencia = st.text_input("Referencia del Trabajo (Ej: Corte EDM, matricería, etc.)")
fecha_entrega = st.date_input("Fecha estimada de entrega", value=date.today())

st.markdown("---") 

# --- BOTÓN DE ENVIAR Y LÓGICA DE ODOO ---
if st.button("Generar Orden en Odoo", type="primary"):
    
    # Validaciones para que no envíen campos vacíos
    if empleado == "Seleccionar...":
        st.warning("⚠️ Seleccione su nombre de empleado.")
    elif cliente_seleccionado == "Seleccionar...":
        st.warning("⚠️ Seleccione un cliente de la lista.")
    elif es_cliente_nuevo and not cliente_final:
        st.warning("⚠️ Escriba el nombre del nuevo cliente.")
    elif not referencia:
        st.warning("⚠️ Escriba una referencia para el trabajo.")
    else:
        with st.spinner("Conectando con el sistema y creando orden..."):
            try:
                common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                uid = common.authenticate(DB, USER, PASSWORD, {})
                models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                
                # PASO 1: Resolver el ID del cliente
                if es_cliente_nuevo:
                    # Lo creamos en Odoo
                    datos_nuevo = {'name': cliente_final, 'is_company': True}
                    if telefono_final:
                        datos_nuevo['phone'] = telefono_final
                        
                    cliente_id_odoo = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'create', [datos_nuevo])
                    ref_completa = f"[{empleado}] - {referencia}"
                    
                else:
                    # Como ya existe en la lista, buscamos su ID numérico interno en Odoo
                    cliente_busqueda = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', 
                        [[['name', '=', cliente_final]]], {'limit': 1})
                    cliente_id_odoo = cliente_busqueda[0] if cliente_busqueda else False
                    ref_completa = f"[{empleado}] - {referencia}"
                    
                # PASO 2: Crear la Orden de Venta
                if not cliente_id_odoo:
                     st.error("❌ Error interno: No se pudo verificar el cliente en Odoo.")
                else:
                    fecha_str = fecha_entrega.strftime("%Y-%m-%d")
                    orden_id = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'create', [{
                        'partner_id': cliente_id_odoo,
                        'client_order_ref': ref_completa,
                        'commitment_date': fecha_str
                    }])
                    
                    # Leemos qué número SO-XXX le asignó Odoo
                    orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', 
                        [[orden_id]], {'fields': ['name']})
                    
                    num_orden = orden[0]['name']
                    st.success(f"✅ ¡Éxito! Se generó la orden de venta: **{num_orden}** para {cliente_final}")
                    
                    # LIMPIEZA DE CACHÉ: Si creamos un cliente nuevo, borramos la memoria
                    # para que la próxima vez que alguien abra la app, Odoo descargue la lista 
                    # actualizada y el nuevo cliente ya aparezca en el buscador.
                    if es_cliente_nuevo:
                        obtener_clientes.clear()
                        
            except Exception as e:
                st.error(f"Error de conexión o de Odoo: {e}")
