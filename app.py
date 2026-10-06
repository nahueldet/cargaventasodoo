import streamlit as st
import xmlrpc.client
import base64
from datetime import date
import qrcode
from io import BytesIO
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner
import pandas as pd

# Configuración básica de la página
st.set_page_config(page_title="Gestión de Taller", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

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
if 'articulos_temporales' not in st.session_state:
    st.session_state.articulos_temporales = [] 

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
    img[data-testid="stImage"] { border-radius: 15px; box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
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
            [], {'fields': ['id', 'name'], 'order': 'name asc'})
        return {e['name']: e['id'] for e in empleados_data}
    except Exception: return {"Nahuel de Titto": 1, "Taller 1": 2}

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
    dict_empleados = obtener_empleados()
    dict_productos = obtener_productos()

opciones_clientes = ["Seleccionar...", "➕ CREAR NUEVO CLIENTE"] + lista_clientes
opciones_empleados = ["Seleccionar..."] + list(dict_empleados.keys())

# ==========================================
# PESTAÑAS (MÓDULOS)
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📦 Ingreso", "⏱️ Horas General", "✏️ Editar", "⚡ Electroerosión", "💥 Corte Láser", "📅 Planificador"])

# ------------------------------------------
# MÓDULO 1: INGRESO DE MATERIAL 
# ------------------------------------------
with tab1:
    if not st.session_state.orden_exitosa:
        st.markdown("### 🏢 Datos Comerciales")
        with st.container(border=True):
            empleado = st.selectbox("Recepcionista (Técnico interno)", opciones_empleados, key="ingreso_emp")
            cliente_seleccionado = st.selectbox("Empresa / Cliente a facturar", opciones_clientes, key="ingreso_cli")
            
            cliente_final = ""
            telefono_final = ""
            es_cliente_nuevo = False
            
            if cliente_seleccionado == "➕ CREAR NUEVO CLIENTE":
                st.markdown("<p style='color:#8e24aa; font-weight:bold; font-size:14px;'>Nuevo Registro</p>", unsafe_allow_html=True)
                cliente_final = st.text_input("Razón Social", key="ingreso_rs")
                telefono_final = st.text_input("Teléfono (Opcional)", key="ingreso_tel")
                es_cliente_nuevo = True
            else:
                cliente_final = cliente_seleccionado

        st.markdown("### ⚙ Especificaciones")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1: persona_deja_trabajo = st.text_input("Traído por (Chofer)", key="ingreso_chofer")
            with col2: fecha_entrega = st.date_input("Fecha Prometida", value=date.today(), key="ingreso_fecha")
                
            trabajo = st.text_input("Descripción libre del trabajo a realizar", key="ingreso_desc")
            
            foto_adjunta = st.file_uploader("Evidencia fotográfica", type=['jpg', 'jpeg', 'png'])
            if foto_adjunta is not None:
                st.image(foto_adjunta, caption="Archivo listo", use_container_width=True)
        
        st.markdown("### 🛒 Artículos / Materiales (Opcional)")
        with st.container(border=True):
            if st.session_state.articulos_temporales:
                for idx, item in enumerate(st.session_state.articulos_temporales):
                    c1, c2, c3 = st.columns([5, 3, 2])
                    c1.markdown(f"🔹 **{item['nombre']}**")
                    c2.markdown(f"Cant: **{item['cant']}**")
                    if c3.button("❌ Quitar", key=f"del_art_{idx}"):
                        st.session_state.articulos_temporales.pop(idx)
                        st.rerun()
                st.markdown("---")
            
            c_prod, c_cant, c_btn = st.columns([5, 2, 3])
            with c_prod: prod_sel_ingreso = st.selectbox("Seleccionar producto", ["Seleccionar..."] + list(dict_productos.keys()), key="sel_nuevo_prod")
            with c_cant: cant_ingreso = st.number_input("Cant", min_value=0.25, step=1.0, value=1.0, key="cant_nuevo_prod")
            with c_btn:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ Añadir a la lista", use_container_width=True):
                    if prod_sel_ingreso != "Seleccionar...":
                        st.session_state.articulos_temporales.append({'nombre': prod_sel_ingreso, 'id': dict_productos[prod_sel_ingreso], 'cant': cant_ingreso})
                        st.rerun()
                    else: st.warning("Elija un producto primero.")

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
                            'partner_id': cliente_id_odoo, 'commitment_date': fecha_entrega.strftime("%Y-%m-%d"), 'note': observaciones
                        }])
                        
                        models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{'order_id': orden_id, 'display_type': 'line_section', 'name': trabajo}])
                        
                        if st.session_state.articulos_temporales:
                            for art in st.session_state.articulos_temporales:
                                models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{'order_id': orden_id, 'product_id': art['id'], 'product_uom_qty': art['cant']}])
                        
                        if foto_adjunta is not None:
                            foto_base64 = base64.b64encode(foto_adjunta.read()).decode('utf-8')
                            models.execute_kw(DB, uid, PASSWORD, 'ir.attachment', 'create', [{'name': f"Ingreso_{trabajo}.jpg", 'type': 'binary', 'datas': foto_base64, 'res_model': 'sale.order', 'res_id': orden_id}])

                        orden = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', [[orden_id]], {'fields': ['name']})
                        
                        qr = qrcode.QRCode(version=1, box_size=10, border=1) 
                        qr.add_data(orden[0]['name'])
                        qr.make(fit=True)
                        img_qr = qr.make_image(fill_color="black", back_color="white")
                        
                        buf = BytesIO()
                        img_qr.save(buf, format="PNG")
                        st.session_state.num_orden_generada = orden[0]['name']
                        st.session_state.qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                        st.session_state.nombre_cliente_etiqueta = (cliente_final[:15] + '...') if len(cliente_final) > 15 else cliente_final
                        st.session_state.desc_trabajo_etiqueta = (trabajo[:20] + '...') if len(trabajo) > 20 else trabajo
                        st.session_state.orden_exitosa = True
                        
                        if es_cliente_nuevo: obtener_clientes.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

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
            st.session_state.articulos_temporales = [] 
            keys_to_clear = ['ingreso_emp', 'ingreso_cli', 'ingreso_rs', 'ingreso_tel', 'ingreso_chofer', 'ingreso_desc', 'sel_nuevo_prod', 'cant_nuevo_prod']
            for k in keys_to_clear:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

# ------------------------------------------
# MÓDULO 2: CARGA DE HORAS GENERAL
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
                
                filtros_activos = [['invoice_status', '!=', 'invoiced'], ['locked', '=', False], ['state', '!=', 'cancel']]
                
                so_ids_name = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [[['name', 'ilike', busqueda]] + filtros_activos])
                partner_ids = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', 'ilike', busqueda]]])
                so_ids_partner = []
                if partner_ids:
                    so_ids_partner = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [[['partner_id', 'in', partner_ids]] + filtros_activos])
                
                lineas = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', [[['name', 'ilike', busqueda]]], {'fields': ['order_id']})
                line_so_ids_crudos = [line['order_id'][0] for line in lineas if line.get('order_id')]
                
                all_ids_crudos = list(set(so_ids_name + line_so_ids_crudos + so_ids_partner))
                
                if all_ids_crudos:
                    ordenes = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_read', 
                                                [[['id', 'in', all_ids_crudos]] + filtros_activos], 
                                                {'fields': ['id', 'name', 'partner_id'], 'order': 'id desc', 'limit': 50})
                    
                    if ordenes:
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
                                    
                        st.markdown("### ⏱ Registrar Avance")
                        with st.form("form_horas_gen", clear_on_submit=True):
                            tec = st.selectbox("Técnico", opciones_empleados, key="tec_horas")
                            colA, colB = st.columns(2)
                            with colA: dia_trabajo = st.date_input("Día del trabajo", value=date.today(), key="dia_horas")
                            with colB: horas_trabajadas = st.number_input("Horas utilizadas", min_value=0.0, step=0.25, value=1.0, key="num_horas")
                            notas_extra = st.text_area("Notas / Observaciones", key="notas_horas")
                            submit_horas = st.form_submit_button("Guardar Registro", type="primary")
                            
                            if submit_horas:
                                if tec == "Seleccionar...": st.error("⚠️ Seleccione al técnico.")
                                elif horas_trabajadas <= 0: st.error("⚠️️ Las horas deben ser mayor a 0.")
                                else:
                                    texto_registro = f"⏱️️ HORAS ({tec}): {horas_trabajadas} hs | Fecha: {dia_trabajo.strftime('%d/%m/%Y')}"
                                    texto_registro += f"\n👉 Trabajo realizado en: {trabajo_a_imputar}"
                                    if notas_extra: texto_registro += f"\n📝 Notas Técnicas: {notas_extra}"
                                        
                                    models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{'order_id': orden_id, 'display_type': 'line_note', 'name': texto_registro}])
                                    st.success("✅ ¡Horas anexadas exitosamente a la orden!")
                                    colX, colY, colZ = st.columns([1, 2, 1])
                                    with colY:
                                        try: st.image("exito.jpeg", caption="¡Trabajo Imputado!", use_container_width=True)
                                        except Exception: pass
                    else:
                        st.warning("No se encontraron órdenes abiertas (están facturadas, bloqueadas o canceladas).")
                else: st.warning("No se encontraron órdenes con esa búsqueda.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

# ------------------------------------------
# MÓDULO 3: EDICIÓN RÁPIDA 
# ------------------------------------------
with tab3:
    st.markdown("### 🔍 Buscar Cotización / Orden a Editar")
    busqueda_edit = st.text_input("Ingrese Cliente o Nro de Orden (Solo Activas)", key="input_busqueda_edit")
    
    if busqueda_edit:
        with st.spinner("Buscando órdenes pendientes..."):
            try:
                common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
                uid = common.authenticate(DB, USER, PASSWORD, {})
                models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
                
                filtros_activos = [['invoice_status', '!=', 'invoiced'], ['locked', '=', False], ['state', '!=', 'cancel']]
                
                partner_ids = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', 'ilike', busqueda_edit]]])
                
                domain_name = [['name', 'ilike', busqueda_edit]] + filtros_activos
                so_ids_name = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [domain_name])
                
                so_ids_partner = []
                if partner_ids:
                    domain_partner = [['partner_id', 'in', partner_ids]] + filtros_activos
                    so_ids_partner = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [domain_partner])
                
                all_ids = list(set(so_ids_name + so_ids_partner))
                
                if all_ids:
                    ordenes = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_read', 
                                                [[['id', 'in', all_ids]]], 
                                                {'fields': ['id', 'name', 'partner_id', 'date_order', 'amount_total', 'state'], 'order': 'id desc'})
                    
                    lineas_resumen = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                     [[['order_id', 'in', all_ids]]], 
                                                     {'fields': ['order_id', 'name', 'display_type']})
                    
                    dict_detalles = {}
                    for l in lineas_resumen:
                        o_id = l['order_id'][0]
                        if o_id not in dict_detalles: dict_detalles[o_id] = []
                        if l['display_type'] == 'line_section' and l['name']: dict_detalles[o_id].append(l['name'])
                        elif not l['display_type'] and l['name']: dict_detalles[o_id].append(l['name'].split('\n')[0]) 

                    st.markdown("#### 📋 Órdenes Pendientes")
                    datos_tabla = []
                    for o in ordenes:
                        estado_texto = "Borrador" if o['state'] in ['draft', 'sent'] else "Orden de Venta"
                        detalles_lista = dict_detalles.get(o['id'], [])
                        detalle_texto = " | ".join(detalles_lista) if detalles_lista else "Sin detalle"
                        if len(detalle_texto) > 60: detalle_texto = detalle_texto[:57] + "..."

                        datos_tabla.append({
                            "Nro. Orden": o['name'],
                            "Cliente": o['partner_id'][1] if o['partner_id'] else "Sin cliente",
                            "Detalle": detalle_texto,
                            "Fecha": str(o.get('date_order', ''))[:10],
                            "Estado": estado_texto,
                            "Monto": f"${o.get('amount_total', 0):.2f}"
                        })
                    
                    df_ordenes = pd.DataFrame(datos_tabla)
                    st.dataframe(df_ordenes, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    
                    opciones_ord_edit = {f"{o['name']} - Cliente: {o['partner_id'][1]}": o for o in ordenes}
                    
                    with st.container(border=True):
                        st.markdown("#### 🔧 Seleccione una orden de la lista para editarla")
                        orden_seleccionada = st.selectbox("Orden a editar:", list(opciones_ord_edit.keys()), key="sel_ord_edit")
                        orden_data = opciones_ord_edit[orden_seleccionada]
                        orden_id_edit = orden_data['id']
                        
                        st.markdown("---")
                        st.markdown("#### 📝 Editar Detalle de la Orden")
                        
                        lineas_completas = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                         [[['order_id', '=', orden_id_edit]]], 
                                                         {'fields': ['id', 'name', 'display_type', 'product_uom_qty']})
                        
                        with st.form("form_editar_lineas"):
                            lineas_modificadas = []
                            for linea in lineas_completas:
                                if linea['display_type'] == 'line_section': tipo_txt, color = "🔹 SECCIÓN / TRABAJO", "#6a1b9a"
                                elif linea['display_type'] == 'line_note': tipo_txt, color = "📝 NOTA / HORAS", "#e65100"
                                else: tipo_txt, color = "🛒 ARTÍCULO / REPUESTO", "#1565c0"

                                st.markdown(f"<p style='color:{color}; font-size:12px; font-weight:bold; margin-bottom:0;'>{tipo_txt}</p>", unsafe_allow_html=True)
                                col_desc, col_cant = st.columns([4, 1])
                                with col_desc: new_name = st.text_area("Descripción", value=linea['name'], key=f"desc_{linea['id']}", label_visibility="collapsed")
                                with col_cant:
                                    if not linea['display_type']: new_qty = st.number_input("Cant", value=float(linea['product_uom_qty']), key=f"cant_{linea['id']}", label_visibility="collapsed")
                                    else: new_qty = False
                                
                                st.markdown("<hr style='margin-top:5px; margin-bottom:15px;'>", unsafe_allow_html=True)
                                lineas_modificadas.append({
                                    'id': linea['id'], 'old_name': linea['name'], 'new_name': new_name,
                                    'is_product': not linea['display_type'], 'old_qty': float(linea['product_uom_qty']) if not linea['display_type'] else False, 'new_qty': new_qty
                                })

                            submit_lineas = st.form_submit_button("💾 Guardar Cambios", type="primary")
                            if submit_lineas:
                                cambios_realizados = 0
                                for mod in lineas_modificadas:
                                    valores_a_cambiar = {}
                                    if mod['old_name'] != mod['new_name']: valores_a_cambiar['name'] = mod['new_name']
                                    if mod['is_product'] and mod['old_qty'] != mod['new_qty']: valores_a_cambiar['product_uom_qty'] = mod['new_qty']
                                    
                                    if valores_a_cambiar:
                                        models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'write', [[mod['id']], valores_a_cambiar])
                                        cambios_realizados += 1
                                        
                                if cambios_realizados > 0:
                                    st.success(f"✅ ¡Se actualizaron {cambios_realizados} líneas con éxito!")
                                    st.rerun()

                        st.markdown("---")
                        st.markdown("#### 👤 Cambiar Cliente Facturación")
                        nuevo_cliente_nombre = st.selectbox("Seleccionar nuevo cliente", ["Seleccionar..."] + lista_clientes, key="edit_cli")
                        
                        if st.button("Actualizar Cliente", key="btn_act_cli"):
                            if nuevo_cliente_nombre == "Seleccionar...": st.warning("⚠️ Seleccione un cliente válido.")
                            else:
                                cliente_busqueda = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', '=', nuevo_cliente_nombre]]], {'limit': 1})
                                if cliente_busqueda:
                                    models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'write', [[orden_id_edit], {'partner_id': cliente_busqueda[0]}])
                                    st.success(f"✅ El cliente ahora es {nuevo_cliente_nombre}.")
                                    st.rerun()
                        
                        st.markdown("---")
                        st.markdown("#### 🛒 Sumar Nuevo Artículo a la Orden")
                        opciones_prod_edit = ["Seleccionar..."] + list(dict_productos.keys())
                        prod_sel_edit = st.selectbox("Producto / Artículo", opciones_prod_edit, key="sel_prod_edit")
                        col1_edit, col2_edit = st.columns(2)
                        with col1_edit: cant_edit = st.number_input("Cantidad", min_value=0.25, step=1.0, value=1.0, key="cant_prod_edit")
                        
                        if st.button("➕ Agregar Artículo", type="primary", key="btn_add_prod_edit"):
                            if prod_sel_edit == "Seleccionar...": st.warning("⚠️ Debe seleccionar un producto.")
                            else:
                                prod_id_edit = dict_productos[prod_sel_edit]
                                models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{
                                    'order_id': orden_id_edit, 'product_id': prod_id_edit, 'product_uom_qty': cant_edit
                                }])
                                st.success(f"✅ Se agregaron {cant_edit} unidades de '{prod_sel_edit}' a la orden.")
                                st.rerun()
                                
                else: st.warning("No se encontró ninguna orden pendiente con ese cliente o número.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

# ------------------------------------------
# MÓDULO 4: TABLERO DE ELECTROEROSIÓN
# ------------------------------------------
with tab4:
    st.markdown("### ⚡ Panel de Control - Corte por Hilo")
    st.write("Trabajos activos que requieren servicio de electroerosión y NO están marcados como hechos.")
    
    if st.button("🔄 Actualizar Tablero", key="btn_refresh_edm"):
        st.rerun()
        
    with st.spinner("Buscando trabajos pendientes en Odoo..."):
        try:
            common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
            uid = common.authenticate(DB, USER, PASSWORD, {})
            models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
            
            domain_lineas_hilo = [
                ['name', 'ilike', 'CORTE POR HILO'],
                ['name', 'not ilike', '[HECHO]']
            ]
            
            lineas_hilo = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                           [domain_lineas_hilo], 
                                           {'fields': ['order_id']})
            
            order_ids_hilo = list(set([l['order_id'][0] for l in lineas_hilo if l.get('order_id')]))
            
            if order_ids_hilo:
                filtros_activos = [['invoice_status', '!=', 'invoiced'], ['locked', '=', False], ['state', '!=', 'cancel']]
                domain_edm = [['id', 'in', order_ids_hilo]] + filtros_activos
                
                ordenes_edm = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_read', 
                                                [domain_edm], 
                                                {'fields': ['id', 'name', 'partner_id', 'date_order', 'amount_total', 'state'], 'order': 'date_order desc'})
                
                if ordenes_edm:
                    ordenes_ids = [o['id'] for o in ordenes_edm]
                    lineas_resumen = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                     [[['order_id', 'in', ordenes_ids]]], 
                                                     {'fields': ['order_id', 'name', 'display_type']})
                    
                    dict_detalles = {}
                    for l in lineas_resumen:
                        o_id = l['order_id'][0]
                        if o_id not in dict_detalles: dict_detalles[o_id] = []
                        if l['display_type'] == 'line_section' and l['name']: dict_detalles[o_id].append(l['name'])
                        elif not l['display_type'] and l['name']: dict_detalles[o_id].append(l['name'].split('\n')[0]) 

                    datos_tabla_edm = []
                    for o in ordenes_edm:
                        estado_texto = "Borrador" if o['state'] in ['draft', 'sent'] else "Orden de Venta"
                        detalles_lista = dict_detalles.get(o['id'], [])
                        detalle_texto = " | ".join(detalles_lista) if detalles_lista else "Sin detalle"

                        datos_tabla_edm.append({
                            "Nro. Orden": o['name'],
                            "Cliente": o['partner_id'][1] if o['partner_id'] else "Sin cliente",
                            "Detalle": detalle_texto,
                            "Fecha": str(o.get('date_order', ''))[:10],
                            "Estado": estado_texto
                        })
                    
                    df_edm = pd.DataFrame(datos_tabla_edm)
                    st.dataframe(df_edm, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    
                    st.markdown("#### 🔧 Gestión de Electroerosión")
                    opciones_ord_edm = {f"{o['name']} - Cliente: {o['partner_id'][1]}": o['id'] for o in ordenes_edm}
                    
                    with st.container(border=True):
                        orden_seleccionada_edm = st.selectbox("Seleccione la orden a gestionar:", list(opciones_ord_edm.keys()), key="sel_ord_edm")
                        orden_id_edm = opciones_ord_edm[orden_seleccionada_edm]
                        
                        st.markdown("---")
                        
                        col_horas, col_hecho = st.columns([2, 1])
                        
                        with col_horas:
                            st.markdown("##### ⏱️ Registrar Horas Parciales")
                            with st.form("form_horas_edm", clear_on_submit=True):
                                tec_edm = st.selectbox("Operario", opciones_empleados, key="tec_edm")
                                colA_edm, colB_edm = st.columns(2)
                                with colA_edm: dia_trabajo_edm = st.date_input("Día", value=date.today(), key="dia_edm")
                                with colB_edm: horas_trabajadas_edm = st.number_input("Tiempo (Hs)", min_value=0.0, step=0.25, value=1.0, key="num_horas_edm")
                                notas_extra_edm = st.text_area("Descripción / Notas", key="notas_edm")
                                
                                submit_horas_edm = st.form_submit_button("💾 Imputar Horas", type="primary")
                                
                                if submit_horas_edm:
                                    if tec_edm == "Seleccionar...": st.error("⚠️ Seleccione al operario.")
                                    elif horas_trabajadas_edm <= 0: st.error("⚠️ El tiempo debe ser mayor a 0.")
                                    else:
                                        try:
                                            linea_hilo = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                [[['order_id', '=', orden_id_edm], ['name', 'ilike', 'CORTE POR HILO'], ['name', 'not ilike', '[HECHO]']]], 
                                                {'fields': ['id', 'project_id', 'task_id'], 'limit': 1})
                                            
                                            if linea_hilo:
                                                l_id = linea_hilo[0]['id']
                                                empleado_id = dict_empleados[tec_edm]
                                                desc_ts = f"EDM: {notas_extra_edm}" if notas_extra_edm else "Trabajo de Electroerosión"
                                                
                                                ts_vals = {
                                                    'name': desc_ts, 'employee_id': empleado_id, 'unit_amount': horas_trabajadas_edm,
                                                    'so_line': l_id, 'date': dia_trabajo_edm.strftime("%Y-%m-%d")
                                                }
                                                
                                                if linea_hilo[0].get('project_id'): ts_vals['project_id'] = linea_hilo[0]['project_id'][0]
                                                if linea_hilo[0].get('task_id'): ts_vals['task_id'] = linea_hilo[0]['task_id'][0]
                                                    
                                                models.execute_kw(DB, uid, PASSWORD, 'account.analytic.line', 'create', [ts_vals])
                                                st.success("✅ ¡Horas imputadas en Odoo!")
                                            else:
                                                st.warning("⚠️ No se encontró la línea del servicio.")
                                        except Exception as e:
                                            texto_registro = f"⏱️ HORAS EDM ({tec_edm}): {horas_trabajadas_edm} hs | Fecha: {dia_trabajo_edm.strftime('%d/%m/%Y')}"
                                            if notas_extra_edm: texto_registro += f"\n📝 Notas: {notas_extra_edm}"
                                            models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{'order_id': orden_id_edm, 'display_type': 'line_note', 'name': texto_registro}])
                                            st.success("✅ ¡Horas anexadas como nota a la orden!")

                        with col_hecho:
                            st.markdown("##### ✅ Finalizar Trabajo")
                            st.info("Al marcarlo como terminado, dejará de listarse en este tablero para evitar confusiones.")
                            
                            if st.button("Marcar Servicio como HECHO", use_container_width=True, key="btn_hecho_edm"):
                                with st.spinner("Actualizando estado en Odoo..."):
                                    linea_hilo = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                [[['order_id', '=', orden_id_edm], ['name', 'ilike', 'CORTE POR HILO'], ['name', 'not ilike', '[HECHO]']]], 
                                                {'fields': ['id', 'name'], 'limit': 1})
                                    
                                    if linea_hilo:
                                        l_id = linea_hilo[0]['id']
                                        nuevo_nombre = linea_hilo[0]['name'] + "\n=== [HECHO] ==="
                                        models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'write', [[l_id], {'name': nuevo_nombre}])
                                        st.success("✅ ¡Trabajo Finalizado! Limpiando tablero...")
                                        st.rerun()
                                    else:
                                        st.warning("⚠️ El servicio ya fue marcado como hecho o no se encuentra.")
                                        
                else:
                    st.success("✅ Al día. No hay órdenes activas de corte por hilo pendientes en este momento.")
            else:
                st.success("✅ Al día. No hay órdenes activas de corte por hilo pendientes en este momento.")
                
        except Exception as e:
            st.error(f"Error de conexión: {e}")

# ------------------------------------------
# MÓDULO 5: TABLERO DE CORTE LÁSER CNC
# ------------------------------------------
with tab5:
    st.markdown("### 💥 Panel de Control - Corte Láser CNC")
    st.write("Trabajos activos que requieren servicio de corte láser y NO están marcados como hechos.")
    
    if st.button("🔄 Actualizar Tablero", key="btn_refresh_laser"):
        st.rerun()
        
    with st.spinner("Buscando trabajos pendientes en Odoo..."):
        try:
            common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
            uid = common.authenticate(DB, USER, PASSWORD, {})
            models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
            
            domain_lineas_laser = [
                ['name', 'ilike', 'CORTE LASER CNC'],
                ['name', 'not ilike', '[HECHO]']
            ]
            
            lineas_laser = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                           [domain_lineas_laser], 
                                           {'fields': ['order_id']})
            
            order_ids_laser = list(set([l['order_id'][0] for l in lineas_laser if l.get('order_id')]))
            
            if order_ids_laser:
                filtros_activos = [['invoice_status', '!=', 'invoiced'], ['locked', '=', False], ['state', '!=', 'cancel']]
                domain_laser = [['id', 'in', order_ids_laser]] + filtros_activos
                
                ordenes_laser = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_read', 
                                                [domain_laser], 
                                                {'fields': ['id', 'name', 'partner_id', 'date_order', 'amount_total', 'state'], 'order': 'date_order desc'})
                
                if ordenes_laser:
                    ordenes_ids = [o['id'] for o in ordenes_laser]
                    lineas_resumen = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                     [[['order_id', 'in', ordenes_ids]]], 
                                                     {'fields': ['order_id', 'name', 'display_type']})
                    
                    dict_detalles = {}
                    for l in lineas_resumen:
                        o_id = l['order_id'][0]
                        if o_id not in dict_detalles: dict_detalles[o_id] = []
                        if l['display_type'] == 'line_section' and l['name']: dict_detalles[o_id].append(l['name'])
                        elif not l['display_type'] and l['name']: dict_detalles[o_id].append(l['name'].split('\n')[0]) 

                    datos_tabla_laser = []
                    for o in ordenes_laser:
                        estado_texto = "Borrador" if o['state'] in ['draft', 'sent'] else "Orden de Venta"
                        detalles_lista = dict_detalles.get(o['id'], [])
                        detalle_texto = " | ".join(detalles_lista) if detalles_lista else "Sin detalle"

                        datos_tabla_laser.append({
                            "Nro. Orden": o['name'],
                            "Cliente": o['partner_id'][1] if o['partner_id'] else "Sin cliente",
                            "Detalle": detalle_texto,
                            "Fecha": str(o.get('date_order', ''))[:10],
                            "Estado": estado_texto
                        })
                    
                    df_laser = pd.DataFrame(datos_tabla_laser)
                    st.dataframe(df_laser, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    
                    st.markdown("#### 🔧 Gestión de Corte Láser CNC")
                    opciones_ord_laser = {f"{o['name']} - Cliente: {o['partner_id'][1]}": o['id'] for o in ordenes_laser}
                    
                    with st.container(border=True):
                        orden_seleccionada_laser = st.selectbox("Seleccione la orden a gestionar:", list(opciones_ord_laser.keys()), key="sel_ord_laser")
                        orden_id_laser = opciones_ord_laser[orden_seleccionada_laser]
                        
                        st.markdown("---")
                        
                        col_horas, col_hecho = st.columns([2, 1])
                        
                        with col_horas:
                            st.markdown("##### ⏱️ Registrar Horas Parciales")
                            with st.form("form_horas_laser", clear_on_submit=True):
                                tec_laser = st.selectbox("Operario", opciones_empleados, key="tec_laser")
                                colA_laser, colB_laser = st.columns(2)
                                with colA_laser: dia_trabajo_laser = st.date_input("Día", value=date.today(), key="dia_laser")
                                with colB_laser: horas_trabajadas_laser = st.number_input("Tiempo (Hs)", min_value=0.0, step=0.25, value=1.0, key="num_horas_laser")
                                notas_extra_laser = st.text_area("Descripción / Notas", key="notas_laser")
                                
                                submit_horas_laser = st.form_submit_button("💾 Imputar Horas", type="primary")
                                
                                if submit_horas_laser:
                                    if tec_laser == "Seleccionar...": st.error("⚠️️ Seleccione al operario.")
                                    elif horas_trabajadas_laser <= 0: st.error("⚠️ El tiempo debe ser mayor a 0.")
                                    else:
                                        try:
                                            linea_laser = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                [[['order_id', '=', orden_id_laser], ['name', 'ilike', 'CORTE LASER CNC'], ['name', 'not ilike', '[HECHO]']]], 
                                                {'fields': ['id', 'project_id', 'task_id'], 'limit': 1})
                                            
                                            if linea_laser:
                                                l_id = linea_laser[0]['id']
                                                empleado_id = dict_empleados[tec_laser]
                                                desc_ts = f"LÁSER: {notas_extra_laser}" if notas_extra_laser else "Trabajo de Corte Láser"
                                                
                                                ts_vals = {
                                                    'name': desc_ts, 'employee_id': empleado_id, 'unit_amount': horas_trabajadas_laser,
                                                    'so_line': l_id, 'date': dia_trabajo_laser.strftime("%Y-%m-%d")
                                                }
                                                
                                                if linea_laser[0].get('project_id'): ts_vals['project_id'] = linea_laser[0]['project_id'][0]
                                                if linea_laser[0].get('task_id'): ts_vals['task_id'] = linea_laser[0]['task_id'][0]
                                                    
                                                models.execute_kw(DB, uid, PASSWORD, 'account.analytic.line', 'create', [ts_vals])
                                                st.success("✅ ¡Horas imputadas en Odoo!")
                                            else:
                                                st.warning("⚠️ No se encontró la línea del servicio.")
                                        except Exception as e:
                                            texto_registro = f"⏱️ HORAS LÁSER ({tec_laser}): {horas_trabajadas_laser} hs | Fecha: {dia_trabajo_laser.strftime('%d/%m/%Y')}"
                                            if notas_extra_laser: texto_registro += f"\n📝 Notas: {notas_extra_laser}"
                                            models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'create', [{'order_id': orden_id_laser, 'display_type': 'line_note', 'name': texto_registro}])
                                            st.success("✅ ¡Horas anexadas como nota a la orden!")

                        with col_hecho:
                            st.markdown("##### ✅ Finalizar Trabajo")
                            st.info("Al marcarlo como terminado, dejará de listarse en este tablero para evitar confusiones.")
                            
                            if st.button("Marcar Servicio como HECHO", use_container_width=True, key="btn_hecho_laser"):
                                with st.spinner("Actualizando estado en Odoo..."):
                                    linea_laser = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                [[['order_id', '=', orden_id_laser], ['name', 'ilike', 'CORTE LASER CNC'], ['name', 'not ilike', '[HECHO]']]], 
                                                {'fields': ['id', 'name'], 'limit': 1})
                                    
                                    if linea_laser:
                                        l_id = linea_laser[0]['id']
                                        nuevo_nombre = linea_laser[0]['name'] + "\n=== [HECHO] ==="
                                        models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'write', [[l_id], {'name': nuevo_nombre}])
                                        st.success("✅ ¡Trabajo Finalizado! Limpiando tablero...")
                                        st.rerun()
                                    else:
                                        st.warning("⚠️ El servicio ya fue marcado como hecho o no se encuentra.")
                                        
                else:
                    st.success("✅ Al día. No hay órdenes activas de corte láser pendientes en este momento.")
            else:
                st.success("✅ Al día. No hay órdenes activas de corte láser pendientes en este momento.")
                
        except Exception as e:
            st.error(f"Error de conexión: {e}")

# ------------------------------------------
# MÓDULO 6: PLANIFICADOR DIARIO Y TARJETAS (NUEVO)
# ------------------------------------------
with tab6:
    st.markdown("### 📅 Planificador Diario (Tarjetas de Producción)")
    st.write("Configura las 10 órdenes clave del día para que los técnicos sepan exactamente con qué continuar.")
    
    if st.button("🔄 Actualizar Planificador", key="btn_refresh_plan"):
        st.rerun()
        
    with st.spinner("Cargando órdenes activas..."):
        try:
            common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
            uid = common.authenticate(DB, USER, PASSWORD, {})
            models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
            
            filtros_activos = [['invoice_status', '!=', 'invoiced'], ['locked', '=', False], ['state', '!=', 'cancel']]
            ordenes_plan = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search_read', 
                                            [filtros_activos], 
                                            {'fields': ['id', 'name', 'partner_id', 'commitment_date', 'amount_total'], 'order': 'id desc'})
            
            if ordenes_plan:
                opciones_dict = {f"{o['name']} - {o['partner_id'][1] if o['partner_id'] else 'Sin cliente'}": o['id'] for o in ordenes_plan}
                nombres_opciones = list(opciones_dict.keys())
                ids_opciones = list(opciones_dict.values())
                
                # Inicializar session state para las 10 órdenes del día
                if 'config_10_ordenes' not in st.session_state:
                    st.session_state.config_10_ordenes = ids_opciones[:10]
                
                # Configuración matutina
                with st.container(border=True):
                    st.markdown("#### ⚙️ Configuración Matutina (Selección de Órdenes)")
                    nombres_seleccionados = st.multiselect(
                        "Selecciona las órdenes de la jornada (máximo 10):",
                        options=nombres_opciones,
                        default=[k for k, v in opciones_dict.items() if v in st.session_state.config_10_ordenes],
                        max_selections=10,
                        key="multiselect_10_ordenes"
                    )
                    st.session_state.config_10_ordenes = [opciones_dict[nombre] for nombre in nombres_seleccionados]
                
                st.markdown("---")
                st.markdown("#### 🚀 Cola de Trabajo Activa (Vista en Tarjetas para el Taller)")
                
                if st.session_state.config_10_ordenes:
                    ordenes_filtradas = [o for o in ordenes_plan if o['id'] in st.session_state.config_10_ordenes]
                    
                    # Obtener descripciones (líneas)
                    ordenes_ids = [o['id'] for o in ordenes_filtradas]
                    lineas_resumen = models.execute_kw(DB, uid, PASSWORD, 'sale.order.line', 'search_read', 
                                                     [[['order_id', 'in', ordenes_ids]]], 
                                                     {'fields': ['order_id', 'name', 'display_type']})
                    
                    dict_detalles = {}
                    for l in lineas_resumen:
                        o_id = l['order_id'][0]
                        if o_id not in dict_detalles: dict_detalles[o_id] = []
                        if l['display_type'] == 'line_section' and l['name']: dict_detalles[o_id].append(l['name'])
                        elif not l['display_type'] and l['name']: dict_detalles[o_id].append(l['name'].split('\n')[0]) 

                    # Renderizar tarjetas en columnas (2 columnas)
                    cols = st.columns(2)
                    for idx, o in enumerate(ordenes_filtradas):
                        col_actual = cols[idx % 2]
                        cliente_nombre = o['partner_id'][1] if o['partner_id'] else "Sin cliente"
                        nro_orden = o['name']
                        detalles_lista = dict_detalles.get(o['id'], [])
                        desc_trabajo = " | ".join(detalles_lista) if detalles_lista else "Sin descripción de trabajo"
                        
                        with col_actual:
                            st.markdown(f"""
                            <div style="background-color: white; border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); border-left: 6px solid #6a1b9a;">
                                <h3 style="margin: 0 0 8px 0; color: #1e293b; font-size: 20px;">🏷️ {nro_orden}</h3>
                                <p style="margin: 0 0 6px 0; font-size: 15px; color: #475569;"><strong>Cliente:</strong> {cliente_nombre}</p>
                                <p style="margin: 0; font-size: 14px; color: #334155;"><strong>Trabajo:</strong> {desc_trabajo}</p>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("ℹ️ No hay órdenes seleccionadas en la configuración superior.")
            else:
                st.success("✅ No hay órdenes activas en este momento.")
        except Exception as e:
            st.error(f"Error de conexión con Odoo: {e}")
