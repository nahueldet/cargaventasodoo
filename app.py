import streamlit as st
import xmlrpc.client
from datetime import date # Necesario para manejar fechas

# Configuración básica de la página
st.set_page_config(page_title="Carga de Órdenes", page_icon="⚙️")

st.title("Generador de Órdenes - Odoo")
st.write("Complete los datos para registrar la orden de venta en el sistema.")

# Las credenciales se llaman desde los "Secretos"
URL = st.secrets["ODOO_URL"]
DB = st.secrets["ODOO_DB"]
USER = st.secrets["ODOO_USER"]
PASSWORD = st.secrets["ODOO_PASSWORD"]

# Creación del formulario visual
with st.form("orden_form"):
    st.subheader("Datos de la Orden")
    empleado = st.selectbox("Seleccione su nombre", ["Seleccionar...", "Juan", "Pedro", "María", "Nahuel de Titto"])
    cliente = st.text_input("Nombre del Cliente")
    referencia = st.text_input("Referencia del Trabajo (Ej: Corte EDM, matricería, etc.)")
    
    # Nuevo campo: Fecha de entrega
    fecha_entrega = st.date_input("Fecha estimada de entrega", value=date.today())
    
    st.markdown("---") # Una línea divisoria visual
    
    st.subheader("Opciones de Cliente Nuevo")
    crear_si_no_existe = st.checkbox("Si el cliente no existe, crearlo automáticamente")
    
    # Nuevo campo: Teléfono (solo es relevante si vamos a crear el cliente o guardarlo en la orden)
    telefono = st.text_input("Teléfono (Opcional - Para avisos al cliente)")
    
    submit_button = st.form_submit_button(label="Generar Orden en Odoo")

# Lógica al apretar el botón
if submit_button:
    if empleado == "Seleccionar..." or not cliente or not referencia:
        st.warning("⚠️ Por favor, complete al menos Empleado, Cliente y Referencia.")
    else:
        with st.spinner("Conectando con el sistema..."):
            try:
                # 1. Autenticación en Odoo
                common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                uid = common.authenticate(DB, USER, PASSWORD, {})
                models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                
                # 2. Búsqueda del cliente
                cliente_ids = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', 
                    [[['name', 'ilike', cliente]]], {'limit': 1})
                
                # 3. Lógica si el cliente no se encuentra
                if not cliente_ids:
                    if crear_si_no_existe:
                        st.info("ℹ️ Cliente no encontrado. Creando nuevo cliente...")
                        # Datos para crear el nuevo cliente
                        datos_nuevo_cliente = {
                            'name': cliente,
                            'is_company': True # Asumimos que son empresas, cambia a False si son consumidores finales
                        }
                        
                        # Si completaron el teléfono, lo agregamos al perfil del cliente
                        if telefono:
                            datos_nuevo_cliente['phone'] = telefono
                            
                        nuevo_cliente_id = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'create', [datos_nuevo_cliente])
                        cliente_ids = [nuevo_cliente_id] 
                        st.success(f"✅ Nuevo cliente '{cliente}' creado en Odoo.")
                    else:
                        st.error("❌ No se encontró el cliente. Verifique el nombre o marque la casilla para crearlo.")
                        st.stop() 

                # 4. Creación de la orden
                # Si el cliente ya existía pero igual ingresaron un teléfono en la app, 
                # lo agregamos a la referencia para no perderlo.
                ref_completa = f"[{empleado}] - {referencia}"
                if telefono and not crear_si_no_existe:
                     ref_completa += f" | Tel: {telefono}"

                # Formateamos la fecha a texto (YYYY-MM-DD) que es como la lee Odoo
                fecha_str = fecha_entrega.strftime("%Y-%m-%d")

                orden_id = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'create', [{
                    'partner_id': cliente_ids[0],
                    'client_order_ref': ref_completa,
                    'commitment_date': fecha_str # Campo de fecha de entrega prometida en Odoo
                }])
                
                # 5. Recuperar el número generado
                orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', 
                    [[orden_id]], {'fields': ['name']})
                
                num_orden = orden[0]['name']
                st.success(f"✅ ¡Éxito! Se generó la orden de venta: **{num_orden}**")
        
            except Exception as e:
                st.error(f"Error de conexión: Verifica las credenciales o tu internet. Detalles: {e}")
