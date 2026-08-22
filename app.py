import streamlit as st
import xmlrpc.client
from datetime import date

# Configuración básica de la página
st.set_page_config(page_title="Carga de Órdenes", page_icon="⚙️")

st.title("Generador de Órdenes - Odoo")
st.write("Complete los datos para registrar la orden de venta en el sistema.")

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
        st.error(f"Error al conectar con Odoo (Clientes): {e}")
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
    except Exception as e:
        st.warning("No se pudo cargar la base de empleados de Odoo. Mostrando lista manual.")
        return ["Nahuel de Titto", "Taller 1", "Ventas"]

# Cargamos las listas
with st.spinner("Cargando bases de datos de Odoo..."):
    lista_clientes = obtener_clientes()
    lista_empleados = obtener_empleados()

opciones_clientes = ["Seleccionar...", "➕ CREAR NUEVO CLIENTE"] + lista_clientes
opciones_empleados = ["Seleccionar..."] + lista_empleados

# --- INTERFAZ VISUAL ---
st.subheader("Datos de la Orden")
empleado = st.selectbox("Empleado que carga la orden", opciones_empleados)

cliente_seleccionado = st.selectbox("Buscar Empresa/Cliente Facturación", opciones_clientes)

cliente_final = ""
telefono_final = ""
es_cliente_nuevo = False

if cliente_seleccionado == "➕ CREAR NUEVO CLIENTE":
    st.info("Complete los datos del nuevo cliente:")
    cliente_final = st.text_input("Nombre de la Empresa o Cliente")
    telefono_final = st.text_input("Teléfono de la empresa (Opcional)")
    es_cliente_nuevo = True
else:
    cliente_final = cliente_seleccionado

st.markdown("---")
st.subheader("Detalles del Trabajo")

persona_deja_trabajo = st.text_input("Nombre de la persona que trae el trabajo (Chofer/Cadete/Dueño)")

# Este campo ahora creará una SECCIÓN en la orden
trabajo = st.text_input("Trabajo a realizar (Ej: Corte EDM, matricería, etc.)")

fecha_entrega = st.date_input("Fecha estimada de entrega", value=date.today())

st.markdown("---") 

# --- BOTÓN DE ENVIAR ---
if st.button("Generar Orden en Odoo", type="primary"):
    
    if empleado == "Seleccionar...":
        st.warning("⚠️ Seleccione su nombre de empleado.")
    elif cliente_seleccionado == "Seleccionar...":
        st.warning("⚠️ Seleccione un cliente de la lista.")
    elif es_cliente_nuevo and not cliente_final:
        st.warning("⚠️ Escriba el nombre del nuevo cliente.")
    elif not trabajo:
        st.warning("⚠️ Escriba en qué consiste el trabajo.")
    else:
        with st.spinner("Conectando con el sistema y creando orden..."):
            try:
                common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                uid = common.authenticate(DB, USER, PASSWORD, {})
                models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                
                # 1. Crear o Buscar el ID del cliente
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
                     st.error("❌ Error interno: No se pudo verificar el cliente en Odoo.")
                     st.stop()
                     
                # 2. Armar las Observaciones Generales (Footer de la orden)
                observaciones = f"--- DETALLES DE RECEPCIÓN ---\n"
                observaciones += f"Recepcionado por: {empleado}\n"
                if persona_deja_trabajo:
                    observaciones += f"Persona que dejó las piezas: {persona_deja_trabajo}\n"
                else:
                    observaciones += f"Persona que dejó las piezas: (No especificado)\n"
                
                # 3. CREAR LA ORDEN DE VENTA (Cabecera)
                fecha_str = fecha_entrega.strftime("%Y-%m-%d")
                
                orden_id = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'create', [{
                    'partner_id': cliente_id_odoo,
                    'commitment_date': fecha_str,
                    'note': observaciones
                }])
                
                # 4. CREAR LA LÍNEA DE SECCIÓN
                # Cambiamos 'line_note' por 'line_section'
                linea_seccion = {
                    'order_id': orden_id,
                    'display_type': 'line_section', 
                    'name': trabajo              
                }
                
                models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [linea_seccion])
                
                # 5. Leer el número generado
                orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', 
                    [[orden_id]], {'fields': ['name']})
                
                num_orden = orden[0]['name']
                st.success(f"✅ ¡Éxito! Se generó la orden **{num_orden}** para {cliente_final}")
                
                if es_cliente_nuevo:
                    obtener_clientes.clear()
                        
            except Exception as e:
                st.error(f"Error al enviar la orden: {e}")
