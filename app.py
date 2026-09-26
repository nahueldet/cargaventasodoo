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

# --- CONTROL DE ESTADO ---
if 'orden_exitosa' not in st.session_state:
    st.session_state.orden_exitosa = False
if 'num_orden_generada' not in st.session_state:
    st.session_state.num_orden_generada = ""
if 'qr_base64' not in st.session_state:
    st.session_state.qr_base64 = ""
if 'nombre_cliente_etiqueta' not in st.session_state:
    st.session_state.nombre_cliente_etiqueta = ""
if 'desc_trabajo_etiqueta' not in st.session_state:
    st.session_state.desc_trabajo_etiqueta = ""

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
    
    img[data-testid="stImage"] {
        border-radius: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
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

@st.cache_data(ttl=300)
def obtener_productos():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        productos_data = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'search_read', 
            [[['sale_ok', '=', True], ['active', '=', True]]], 
            {'fields': ['id', 'display_name'], 'order': 'name asc'})
        return {p['display_name']: p['id'] for p in productos_data}
    except Exception: return {}

with st.spinner("Sincronizando base de datos..."):
    lista_clientes = obtener_clientes()
    lista_empleados = obtener_empleados()
    dict_productos = obtener_productos()

opciones_clientes = ["Seleccionar...", "➕ CREAR NUEVO CLIENTE"] + lista_clientes
opciones_empleados = ["Seleccionar..."] + lista_empleados
opciones_prod = ["(Ninguno - Solo texto)"] + list(dict_productos.keys())

# ==========================================
# PESTAÑAS (MÓDULOS)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📦 Ingreso", "⏱️ Horas", "✏️ Editar Orden"])

# ------------------------------------------
# MÓDULO 1: INGRESO DE MATERIAL 
# ------------------------------------------
with tab1:
    if not st.session_state.orden_exitosa:
        st.markdown("### 🏢 Datos Comerciales")
        with st.container(border=True):
            empleado = st.selectbox("Recepcionista (Técnico interno)", opciones_empleados, key="recepcion_emp")
            cliente_seleccionado = st.selectbox("Empresa / Cliente a facturar", opciones_clientes, key="ingreso_cli")
            
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
                
            trabajo = st.text_input("Descripción libre del trabajo a realizar")
            
            with st.expander("🛒 Cargar Artículo/Servicio Odoo (Opcional)"):
                st.write("Seleccione si desea adjuntar un código de servicio al trabajo.")
                prod_sel_ingreso = st.selectbox("Producto o Servicio a facturar", opciones_prod, key="prod_ingreso")
                
                colA_prod, colB_prod = st.columns(2)
                with colA_prod: cant_ingreso = st.number_input("Cantidad", min_value=1.0, step=1.0, value=1.0, key="cant_ingreso")
            
            foto_adjunta = st.file_uploader("Evidencia fotográfica", type=['jpg', 'jpeg', 'png'])
            if foto_adjunta is not None:
                st.image(foto_adjunta, caption="Archivo listo", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Enviar Orden al Taller", type="primary", key="btn_ingreso"):
            if empleado == "Seleccionar...": st.error("⚠️ Faltan datos: Indique recepcionista.")
            elif cliente_seleccionado == "Seleccionar...": st.error("⚠️ Faltan datos: Seleccione cliente.")
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
                        
                        if prod_sel_ingreso != "(Ninguno - Solo texto)":
                            prod_id = dict_productos[prod_sel_ingreso]
                            models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{
                                'order_id': orden_id,
                                'product_id': prod_id,
                                'product_uom_qty': cant_ingreso
                            }])
                        
                        if foto_adjunta is not None:
                            foto_base64 = base64.b64encode(foto_adjunta.read()).decode('utf-8')
                            models.execute_kw(DB, uid, PASSWORD, 'ir.attachment', 'create', [{
                                'name': f"Ingreso_{trabajo}.jpg", 'type': 'binary', 'datas': foto_base64,
                                'res_model': 'sale.order', 'res_id': orden_id         
                            }])

                        orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', [[orden_id]], {'fields': ['name']})
                        
                        qr = qrcode.QRCode(version=1, box_size=10, border=1) 
                        qr.add_data(orden[0]['name'])
                        qr.make(fit=True)
                        img_qr = qr.make_image(fill_color="black", back_color="white")
                        
                        buf = BytesIO()
                        img_qr.save(buf, format="PNG")
                        qr_base64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                        
                        st.session_state.num_orden_generada = orden[0]['name']
                        st.session_state.qr_base64 = qr_base64_str
                        st.session_state.nombre_cliente_etiqueta = (cliente_final[:15] + '...') if len(cliente_final) > 15 else cliente_final
                        st.session_state.desc_trabajo_etiqueta = (trabajo[:20] + '...') if len(trabajo) > 20 else trabajo
                        st.session_state.orden_exitosa = True
                        
                        if es_cliente_nuevo: obtener_clientes.clear()
                        st.rerun()
                                
                    except Exception as e:
                        st.error(f"Error: {e}")

    # PANTALLA DE IMPRESIÓN 
    else:
        st.success(f"✅ ¡Ingreso Registrado! Orden **{st.session_state.num_orden_generada}**.")
        colA, colB, colC = st.columns([1, 2, 1])
        with colB:
            try: st.image("exito.jpeg", caption="¡Aprobado!", use_container_width=True)
            except Exception: pass
        
        st.info("La ventana de impresión debería abrirse automáticamente.")
        html_etiqueta = f"""
        <html>
            <head>
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{ font-family: 'Arial', sans-serif; text-align: center; background-color: white; color: black; width: 50mm; height: 40mm; overflow: hidden; }}
                    .etiqueta-container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 1mm; }}
                    h1 {{ font-size: 14px; margin-bottom: 0.5mm; letter-spacing: 0.5px; }}
                    .cliente-text {{ font-size: 9px; font-weight: bold; margin-bottom: 0.5mm; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 48mm; }}
                    .desc-text {{ font-size: 8px; margin-bottom: 0.5mm; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 48mm; color: #333; }}
                    img {{ width: 22mm; height: 22mm; }}
                    @media print {{
                        @page {{ size: 50mm 40mm; margin: 0mm; }}
                        body {{ width: 50mm; height: 40mm; max-height: 40mm; overflow: hidden; page-break-inside: avoid; }}
                        html, body {{ height: 40mm !important; }}
                    }}
                </style>
            </head>
            <body onload="setTimeout(() => {{ window.print(); }}, 800)">
                <div class="etiqueta-container">
                    <h1>{st.session_state.num_orden_generada}</h1>
                    <div class="cliente-text">{st.session_state.nombre_cliente_etiqueta}</div>
                    <div class="desc-text">{st.session_state.desc_trabajo_etiqueta}</div>
                    <img src="data:image/png;base64,{st.session_state.qr_base64}" />
                </div>
            </body>
        </html>
        """
        components.html(html_etiqueta, height=220)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Cargar un Nuevo Trabajo", type="primary", key="btn_reiniciar"):
            st.session_state.orden_exitosa = False
            st.session_state.num_orden_generada = ""
            st.session_state.qr_base64 = ""
            st.session_state.nombre_cliente_etiqueta = ""
            st.session_state.desc_trabajo_etiqueta = ""
            st.rerun()

# ------------------------------------------
# MÓDULO 2: CARGA DE HORAS Y NOTAS
# ------------------------------------------
with tab2:
    st.markdown("### 🔍 Buscar Orden")
    qr_code_scanned = qrcode_scanner(key='scanner_horas')
    texto_busqueda_inicial = qr_code_scanned if qr_code_scanned else ""

    busqueda = st.text_input("Buscar por Cliente, Nro de Orden o Descripción", value=texto_busqueda_inicial, key="input_busqueda_horas")
    
    if busqueda:
        with st.spinner("Buscando en el sistema..."):
            try:
                common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                uid = common.authenticate(DB, USER, PASSWORD, {})
                models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                
                # 1. Búsqueda por Número de Orden
                so_ids_name = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [[['name', 'ilike', busqueda]]])
                
                # 2. Búsqueda por Descripción del Trabajo (Líneas)
                lineas = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', [[['name', 'ilike', busqueda]]], {'fields': ['order_id']})
                line_so_ids = [line['order_id'][0] for line in lineas if line.get('order_id')]
                
                # 3. NUEVO: Búsqueda por Nombre de Cliente
                partner_ids = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', 'ilike', busqueda]]])
                so_ids_partner = []
                if partner_ids:
                    so_ids_partner = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [[['partner_id', 'in', partner_ids]]])
                
                # Juntamos todos los resultados encontrados sin repetir (usando set)
                all_ids = list(set(so_ids_name + line_so_ids + so_ids_partner))
                
                if all_ids:
                    # Traemos las órdenes. El "order": "id desc" asegura que las más recientes salgan primero, limitamos a 50 para velocidad.
                    ordenes = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_read', 
                                                [[['id', 'in', all_ids]]], 
                                                {'fields': ['id', 'name', 'partner_id'], 'order': 'id desc', 'limit': 50})
                    
                    opciones_ord = {f"{o['name']} - Cliente: {o['partner_id'][1]}": o['id'] for o in ordenes}
                    
                    with st.container(border=True):
                        orden_seleccionada = st.selectbox("Seleccione la orden:", list(opciones_ord.keys()), key="sel_ord_horas")
                        orden_id = opciones_ord[orden_seleccionada]
                        
                        lineas_orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                         [[['order_id', '=', orden_id]]], {'fields': ['name', 'display_type']})
                        
                        trabajos_disponibles = []
                        for linea in lineas_orden:
                             if linea.get('display_type') == 'line_section' or not linea.get('display_type'):
                                 if linea.get('name'): trabajos_disponibles.append(linea['name'])
                        
                        if not trabajos_disponibles: trabajos_disponibles = ["Trabajo General de la Orden"]
                        trabajo_a_imputar = st.selectbox("¿A qué trabajo le cargará las horas?", trabajos_disponibles, key="sel_trab_horas")
                                
                    st.markdown("### ⏱️ Registrar Avance")
                    with st.form("form_horas", clear_on_submit=True):
                        tec = st.selectbox("Técnico", opciones_empleados, key="tec_horas")
                        colA, colB = st.columns(2)
                        with colA: dia_trabajo = st.date_input("Día del trabajo", value=date.today(), key="dia_horas")
                        with colB: horas_trabajadas = st.number_input("Horas utilizadas", min_value=0.0, step=0.25, value=1.0, key="num_horas")
                            
                        notas_extra = st.text_area("Notas / Observaciones", key="notas_horas")
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
                                colX, colY, colZ = st.columns([1, 2, 1])
                                with colY:
                                    try: st.image("exito.jpeg", caption="¡Trabajo Imputado!", use_container_width=True)
                                    except Exception: pass
                else:
                    st.warning("No se encontraron órdenes con esa búsqueda.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

# ------------------------------------------
# MÓDULO 3: EDICIÓN RÁPIDA 
# ------------------------------------------
with tab3:
    st.markdown("### 🔍 Buscar Orden a Editar")
    busqueda_edit = st.text_input("Ingrese Nro de Orden (Ej: S0045)", key="input_busqueda_edit")
    
    if busqueda_edit:
        with st.spinner("Buscando orden..."):
            try:
                common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                uid = common.authenticate(DB, USER, PASSWORD, {})
                models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                
                so_ids = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [[['name', 'ilike', busqueda_edit]]])
                
                if so_ids:
                    ordenes = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_read', 
                                                [[['id', 'in', so_ids]]], {'fields': ['id', 'name', 'partner_id']})
                    
                    opciones_ord_edit = {f"{o['name']} - Cliente Actual: {o['partner_id'][1]}": o for o in ordenes}
                    
                    with st.container(border=True):
                        orden_seleccionada = st.selectbox("Seleccione la orden a editar:", list(opciones_ord_edit.keys()), key="sel_ord_edit")
                        orden_data = opciones_ord_edit[orden_seleccionada]
                        orden_id_edit = orden_data['id']
                        
                        st.markdown("---")
                        
                        # --- SECCIÓN A: CAMBIAR CLIENTE ---
                        st.markdown("#### 👤 Cambiar Cliente")
                        nuevo_cliente_nombre = st.selectbox("Seleccionar nuevo cliente para esta orden", ["Seleccionar..."] + lista_clientes, key="edit_cli")
                        
                        if st.button("Actualizar Cliente", key="btn_act_cli"):
                            if nuevo_cliente_nombre == "Seleccionar...":
                                st.warning("⚠️ Seleccione un cliente válido de la lista.")
                            else:
                                cliente_busqueda = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', '=', nuevo_cliente_nombre]]], {'limit': 1})
                                if cliente_busqueda:
                                    models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'write', [[orden_id_edit], {'partner_id': cliente_busqueda[0]}])
                                    st.success(f"✅ El cliente de la orden {orden_data['name']} ahora es {nuevo_cliente_nombre}.")
                                    st.rerun()
                        
                        st.markdown("---")
                        
                        # --- SECCIÓN B: AGREGAR ARTÍCULOS ---
                        st.markdown("#### 🛒 Agregar Artículo a la Orden")
                        st.write("Seleccione repuestos o artículos del catálogo de Odoo para sumarlos a este trabajo.")
                        
                        opciones_prod_edit = ["Seleccionar..."] + list(dict_productos.keys())
                        prod_sel_edit = st.selectbox("Producto / Artículo", opciones_prod_edit, key="sel_prod_edit")
                        
                        col1_edit, col2_edit = st.columns(2)
                        with col1_edit:
                            cant_edit = st.number_input("Cantidad", min_value=1.0, step=1.0, value=1.0, key="cant_prod_edit")
                        
                        if st.button("➕ Agregar Artículo", type="primary", key="btn_add_prod_edit"):
                            if prod_sel_edit == "Seleccionar...":
                                st.warning("⚠️ Debe seleccionar un producto del catálogo.")
                            else:
                                prod_id_edit = dict_productos[prod_sel_edit]
                                models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{
                                    'order_id': orden_id_edit,
                                    'product_id': prod_id_edit,
                                    'product_uom_qty': cant_edit
                                }])
                                st.success(f"✅ Se agregaron {cant_edit} unidades de '{prod_sel_edit}' a la orden.")
                                
                else:
                    st.warning("No se encontró ninguna orden con ese número.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
