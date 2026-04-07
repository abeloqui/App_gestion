import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# Para PDF (ticket y reporte de stock)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

st.set_page_config(page_title="Gestión Stock y Ventas", layout="wide")
st.title("📦 Sistema de Gestión de Stock y Ventas")

# ===================== SESIÓN =====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

USUARIOS = {
    "admin": {"password": "1234", "role": "admin"},
    "cajero1": {"password": "1234", "role": "cajero"},
    "cajero2": {"password": "1234", "role": "cajero"}
}

def login():
    st.subheader("🔐 Iniciar Sesión")
    usuario = st.text_input("Usuario", value="admin")
    password = st.text_input("Contraseña", type="password", value="1234")
    if st.button("Entrar"):
        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = usuario
            st.session_state.role = USUARIOS[usuario]["role"]
            st.success(f"✅ Bienvenido, {usuario}")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

if not st.session_state.logged_in:
    login()
    st.stop()

# ===================== BASE DE DATOS =====================
def get_connection():
    return sqlite3.connect('gestion.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        precio REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        stock_minimo INTEGER DEFAULT 5,
        categoria TEXT DEFAULT 'Otros'
    )''')
    
    c.execute("PRAGMA table_info(productos)")
    columns = [info[1] for info in c.fetchall()]
    if "categoria" not in columns:
        c.execute("ALTER TABLE productos ADD COLUMN categoria TEXT DEFAULT 'Otros'")
    
    c.execute('''CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        tipo TEXT,
        producto_id INTEGER,
        cantidad INTEGER,
        precio_unitario REAL,
        total REAL,
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        clave TEXT PRIMARY KEY,
        valor INTEGER
    )''')
    c.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES ('ultimo_ticket', 0)")
    
    conn.commit()
    conn.close()

init_db()

# ===================== FUNCIONES =====================
def get_next_ticket_number():
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE config SET valor = valor + 1 WHERE clave = 'ultimo_ticket'")
    c.execute("SELECT valor FROM config WHERE clave = 'ultimo_ticket'")
    ticket_num = c.fetchone()[0]
    conn.commit()
    conn.close()
    return ticket_num

def registrar_movimiento(tipo, producto_id, cantidad, precio_unitario):
    conn = get_connection()
    c = conn.cursor()
    if tipo == "venta":
        c.execute("SELECT stock FROM productos WHERE id=?", (producto_id,))
        result = c.fetchone()
        if result is None or cantidad > result[0]:
            conn.close()
            return False, "❌ Stock insuficiente."
        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, producto_id))
    else:
        c.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (cantidad, producto_id))
    
    total = cantidad * precio_unitario
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO movimientos (fecha, tipo, producto_id, cantidad, precio_unitario, total)
                 VALUES (?, ?, ?, ?, ?, ?)''', (fecha, tipo, producto_id, cantidad, precio_unitario, total))
    conn.commit()
    conn.close()
    return True, "✅ Venta registrada correctamente"

def obtener_productos():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, nombre, categoria, precio, stock, stock_minimo FROM productos ORDER BY nombre", conn)
    conn.close()
    return df

# ===================== TICKET DE VENTA =====================
def export_ticket_pdf(items, total, pago=None, vuelto=None, medio_pago="Efectivo"):
    buffer = BytesIO()
    EMPRESA = "MI NEGOCIO"           
    DIRECCION = "Neuquén, Argentina" 
    TELEFONO = "299-1234567"         
    
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 297*mm), rightMargin=4*mm, leftMargin=4*mm, topMargin=4*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=14, alignment=1, spaceAfter=6)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=4)
    bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontSize=10, alignment=1, spaceAfter=6)
    
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ticket_num = get_next_ticket_number()
    
    elements.append(Paragraph(f"<b>{EMPRESA}</b>", title_style))
    elements.append(Paragraph(DIRECCION, normal_style))
    elements.append(Paragraph(f"Tel: {TELEFONO}", normal_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"<b>Ticket #{ticket_num:05d}</b>", bold_style))
    elements.append(Paragraph(f"Fecha: {now}", normal_style))
    elements.append(Paragraph(f"Cajero: {st.session_state.username}", normal_style))
    elements.append(Spacer(1, 8))
    
    elements.append(Paragraph("─" * 32, normal_style))
    elements.append(Spacer(1, 8))
    
    data = [["Producto", "Cant.", "P.Unit", "Subtotal"]]
    for item in items:
        data.append([item["nombre"][:20], str(item["cantidad"]), f"${item['precio']:.2f}", f"${item['subtotal']:.2f}"])
    
    table = Table(data, colWidths=[30*mm, 9*mm, 16*mm, 18*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(table)
    
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>TOTAL: ${total:.2f}</b>", ParagraphStyle('TotalStyle', parent=styles['Title'], fontSize=13, alignment=1)))
    
    if pago is not None and vuelto is not None:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"Pagado: ${pago:.2f}", normal_style))
        elements.append(Paragraph(f"<b>Vuelto: ${vuelto:.2f}</b>", bold_style))
    
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"<b>Medio de Pago:</b> {medio_pago}", bold_style))
    
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("¡Gracias por su compra!", ParagraphStyle('Thanks', parent=styles['Normal'], fontSize=10, alignment=1)))
    elements.append(Paragraph("Esperamos verte pronto ❤️", normal_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("─" * 32, normal_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ===================== EXPORTAR STOCK A PDF =====================
# ===================== EXPORTAR STOCK A PDF (VERSIÓN MEJORADA) =====================
def export_stock_to_pdf(df):
    buffer = BytesIO()
    
    # Datos de tu negocio (cambiá a los tuyos)
    EMPRESA = "MI NEGOCIO"
    DIRECCION = "Neuquén, Argentina"
    
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        alignment=1,  # Centrado
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1,
        spaceAfter=25
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        spaceAfter=10
    )
    
    # Header
    elements.append(Paragraph(f"<b>{EMPRESA}</b>", title_style))
    elements.append(Paragraph(DIRECCION, subtitle_style))
    elements.append(Paragraph(f"<b>Reporte de Stock</b>", subtitle_style))
    elements.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}", normal_style))
    elements.append(Spacer(1, 20))
    
    # Preparar datos de la tabla
    data = [["Producto", "Categoría", "Precio Unit.", "Stock Actual", "Stock Mínimo", "Estado"]]
    
    for _, row in df.iterrows():
        estado = "Normal"
        estado_color = colors.black
        
        if row['stock'] <= row['stock_minimo']:
            estado = "¡STOCK BAJO!"
            estado_color = colors.red
        
        data.append([
            Paragraph(row['nombre'], ParagraphStyle('name', parent=styles['Normal'], fontSize=9, alignment=0)),  # Izquierda
            row['categoria'],
            f"${row['precio']:.2f}",
            str(row['stock']),
            str(row['stock_minimo']),
            Paragraph(estado, ParagraphStyle('estado', parent=styles['Normal'], fontSize=9, textColor=estado_color, alignment=1))
        ])
    
    # Crear tabla con mejor estilo
    col_widths = [140, 70, 55, 50, 55, 70]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        
        # Cuerpo de la tabla
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('ALIGN', (2,1), (4,-1), 'RIGHT'),      # Precios y stocks a la derecha
        ('ALIGN', (0,1), (1,-1), 'LEFT'),       # Nombre y categoría a la izquierda
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
        
        # Bordes más suaves
        ('BOX', (0,0), (-1,-1), 2, colors.darkblue),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Pie de página
    elements.append(Paragraph("Este reporte fue generado automáticamente por el Sistema de Gestión de Stock.", 
                             ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=1, textColor=colors.grey)))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ===================== MENÚ =====================
if st.session_state.role == "admin":
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "➕ Agregar Producto", "✏️ Editar/Eliminar",
                "📉 Registrar Venta", "📈 Registrar Compra", "📊 Reportes", "📜 Historial"]
else:
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "📉 Registrar Venta"]

menu = st.sidebar.selectbox("Menú Principal", opciones)
st.sidebar.success(f"👤 {st.session_state.username} ({st.session_state.role})")

# ===================== DASHBOARD =====================
if menu == "🏠 Dashboard":
    st.header("🏠 Dashboard - Resumen")
    df_prod = obtener_productos()
    df_mov = pd.read_sql_query('SELECT * FROM movimientos ORDER BY fecha DESC', get_connection())
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Productos", len(df_prod))
    with col2: st.metric("Valor Inventario", f"${(df_prod['stock'] * df_prod['precio']).sum():,.2f}")
    with col3:
        hoy = datetime.now().strftime("%Y-%m-%d")
        ventas_hoy = df_mov[(df_mov["tipo"] == "venta") & (df_mov["fecha"].str.startswith(hoy))]["total"].sum() if not df_mov.empty else 0
        st.metric("Ventas Hoy", f"${ventas_hoy:,.2f}")
    with col4:
        hace_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        ventas_sem = df_mov[(df_mov["tipo"] == "venta") & (df_mov["fecha"] >= hace_7)]["total"].sum() if not df_mov.empty else 0
        st.metric("Ventas Semana", f"${ventas_sem:,.2f}")

# ===================== VER STOCK - CON EXPORTACIONES =====================
elif menu == "📋 Ver Stock":
    st.header("📋 Stock Actual")
    df = obtener_productos()
    
    if df.empty:
        st.warning("No hay productos registrados aún.")
    else:
        categoria_filtro = st.selectbox("Filtrar por categoría", ["Todas"] + sorted(df["categoria"].unique().tolist()))
        df_filtrado = df[df["categoria"] == categoria_filtro] if categoria_filtro != "Todas" else df.copy()
        
        st.dataframe(df_filtrado[["nombre", "categoria", "precio", "stock", "stock_minimo"]], use_container_width=True)
        
        bajos = df_filtrado[df_filtrado["stock"] <= df_filtrado["stock_minimo"]]
        if not bajos.empty:
            st.error(f"⚠️ {len(bajos)} producto(s) con stock bajo:")
            st.dataframe(bajos[["nombre", "stock", "stock_minimo"]])
        
        # Exportaciones
        st.subheader("📤 Exportar Stock")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 Exportar a PDF", type="primary"):
                pdf_bytes = export_stock_to_pdf(df_filtrado)
                st.download_button(
                    label="Descargar Reporte de Stock PDF",
                    data=pdf_bytes,
                    file_name=f"stock_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )
        with col2:
            if st.button("📊 Exportar a Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtrado.to_excel(writer, sheet_name='Stock', index=False)
                output.seek(0)
                st.download_button(
                    label="Descargar Stock Excel (.xlsx)",
                    data=output,
                    file_name=f"stock_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ===================== REGISTRAR VENTA =====================
elif menu == "📉 Registrar Venta":
    st.header("📉 Registrar Venta")
    
    if "cart" not in st.session_state:
        st.session_state.cart = []
    if "last_ticket" not in st.session_state:
        st.session_state.last_ticket = None
    
    df = obtener_productos()
    
    if df.empty:
        st.warning("Primero agrega productos desde '➕ Agregar Producto'")
    else:
        buscar = st.text_input("🔍 Buscar producto", key="buscar_venta")
        opciones = df["nombre"].tolist()
        if buscar:
            opciones = [p for p in opciones if buscar.lower() in p.lower()]
        
        if opciones:
            producto_sel = st.selectbox("Seleccionar Producto", opciones, key="sel_producto")
            row = df[df["nombre"] == producto_sel].iloc[0]
            
            stock_actual = int(row['stock'])
            
            st.info(f"**Stock actual:** {stock_actual} unidades | Precio: **${row['precio']:.2f}**")
            
            # Evitamos el error cuando stock = 0
            if stock_actual <= 0:
                st.error("❌ Este producto no tiene stock disponible.")
            else:
                col1, col2 = st.columns([3,1])
                with col1:
                    cantidad = st.number_input(
                        "Cantidad", 
                        min_value=1, 
                        max_value=stock_actual, 
                        value=1, 
                        key="cant_venta"
                    )
                with col2:
                    if st.button("➕ Agregar al carrito"):
                        st.session_state.cart.append({
                            "id": int(row["id"]),
                            "nombre": row["nombre"],
                            "cantidad": cantidad,
                            "precio": float(row["precio"]),
                            "subtotal": cantidad * float(row["precio"])
                        })
                        st.success(f"✅ {row['nombre']} agregado")
                        st.rerun()
        
        st.subheader("🛒 Carrito")
        if st.session_state.cart:
            for i, item in enumerate(st.session_state.cart):
                col_a, col_b = st.columns([5,1])
                with col_a:
                    st.write(f"• **{item['nombre']}** ×{item['cantidad']} → **${item['subtotal']:.2f}**")
                with col_b:
                    if st.button("🗑️", key=f"del_{i}"):
                        del st.session_state.cart[i]
                        st.rerun()
            
            total = sum(item["subtotal"] for item in st.session_state.cart)
            st.divider()
            st.metric("TOTAL A PAGAR", f"${total:,.2f}")
            
            medio_pago = st.selectbox(
                "💳 Medio de Pago",
                ["Efectivo", "Transferencia", "Tarjeta Débito", "Tarjeta Crédito", "Otro"],
                index=0
            )
            
            pago = st.number_input("💵 Monto recibido", min_value=total, value=total, format="%.2f")
            vuelto = pago - total
            
            if st.button("✅ Finalizar Venta y Generar Ticket", type="primary"):
                todo_ok = True
                for item in st.session_state.cart:
                    exito, msg = registrar_movimiento("venta", item["id"], item["cantidad"], item["precio"])
                    if not exito:
                        st.error(msg)
                        todo_ok = False
                        break
                
                if todo_ok:
                    st.success("🎉 ¡Venta registrada correctamente!")
                    
                    pdf_bytes = export_ticket_pdf(
                        items=st.session_state.cart,
                        total=total,
                        pago=pago,
                        vuelto=vuelto,
                        medio_pago=medio_pago
                    )
                    
                    st.session_state.last_ticket = {
                        "pdf": pdf_bytes,
                        "filename": f"ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    }
                    
                    st.session_state.cart = []
                    st.rerun()
        
        else:
            st.info("Agregá productos al carrito para vender")
        
        if st.session_state.last_ticket is not None:
            st.subheader("🧾 Ticket generado")
            st.download_button(
                label="📄 Descargar Ticket PDF",
                data=st.session_state.last_ticket["pdf"],
                file_name=st.session_state.last_ticket["filename"],
                mime="application/pdf",
                type="primary"
            )
            if st.button("Nueva venta (limpiar)"):
                st.session_state.last_ticket = None
                st.rerun()

# ===================== AGREGAR PRODUCTO =====================
elif menu == "➕ Agregar Producto":
    st.header("➕ Agregar Nuevo Producto")
    with st.form(key="agregar_form"):
        nombre = st.text_input("Nombre del producto *")
        precio = st.number_input("Precio de venta", min_value=0.01, format="%.2f")
        stock_inicial = st.number_input("Stock inicial", min_value=0, value=0, step=1)
        stock_min = st.number_input("Stock mínimo", min_value=0, value=5, step=1)
        categoria = st.text_input("Categoría", "Otros")
        if st.form_submit_button("➕ Agregar Producto"):
            if nombre.strip():
                conn = get_connection()
                c = conn.cursor()
                try:
                    c.execute(
                        "INSERT INTO productos (nombre, precio, stock, stock_minimo, categoria) VALUES (?, ?, ?, ?, ?)",
                        (nombre.strip(), precio, stock_inicial, stock_min, categoria)
                    )
                    conn.commit()
                    st.success(f"✅ {nombre} agregado correctamente!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Ya existe un producto con ese nombre.")
                finally:
                    conn.close()
            else:
                st.error("El nombre es obligatorio.")

# ===================== EDITAR / ELIMINAR =====================
elif menu == "✏️ Editar/Eliminar":
    st.header("✏️ Editar / Eliminar Productos")
    df = obtener_productos()
    if df.empty:
        st.info("No hay productos.")
    else:
        prod_sel = st.selectbox("Seleccionar producto", df["nombre"].tolist())
        row = df[df["nombre"] == prod_sel].iloc[0]
        
        nuevo_nombre = st.text_input("Nombre", row["nombre"])
        nuevo_precio = st.number_input("Precio", value=float(row["precio"]), format="%.2f")
        nuevo_stock = st.number_input("Stock", value=int(row["stock"]), step=1)
        nuevo_min = st.number_input("Stock Mínimo", value=int(row["stock_minimo"]), step=1)
        nueva_cat = st.text_input("Categoría", row["categoria"])
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Guardar Cambios", type="primary"):
                conn = get_connection()
                c = conn.cursor()
                try:
                    c.execute("""UPDATE productos SET nombre=?, precio=?, stock=?, stock_minimo=?, categoria=? WHERE id=?""",
                              (nuevo_nombre, nuevo_precio, nuevo_stock, nuevo_min, nueva_cat, int(row["id"])))
                    conn.commit()
                    st.success("✅ Producto actualizado!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Nombre ya existe.")
                conn.close()
        with col2:
            if st.button("🗑️ Eliminar Producto", type="secondary"):
                if st.checkbox("Confirmar eliminación definitiva"):
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM movimientos WHERE producto_id=?", (int(row["id"]),))
                    c.execute("DELETE FROM productos WHERE id=?", (int(row["id"]),))
                    conn.commit()
                    conn.close()
                    st.success("Producto eliminado")
                    st.rerun()

# ===================== REGISTRAR COMPRA =====================
elif menu == "📈 Registrar Compra":
    st.header("📈 Registrar Compra")
    df = obtener_productos()
    if df.empty:
        st.warning("Agrega productos primero")
    else:
        buscar = st.text_input("🔍 Buscar producto", key="buscar_compra")
        opciones = df["nombre"].tolist()
        if buscar:
            opciones = [p for p in opciones if buscar.lower() in p.lower()]
        
        if opciones:
            producto_sel = st.selectbox("Seleccionar Producto", opciones, key="sel_compra")
            row = df[df["nombre"] == producto_sel].iloc[0]
            
            cantidad = st.number_input("Cantidad a comprar", min_value=1, value=1)
            precio_compra = st.number_input("Precio unitario", value=float(row["precio"]), format="%.2f")
            
            if st.button("✅ Registrar Compra"):
                exito, mensaje = registrar_movimiento("compra", int(row["id"]), cantidad, precio_compra)
                if exito:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.error(mensaje)

# ===================== REPORTES =====================
elif menu == "📊 Reportes":
    st.header("📊 Reportes")
    df_prod = obtener_productos()
    df_mov = pd.read_sql_query("SELECT * FROM movimientos ORDER BY fecha DESC", get_connection())
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Total Productos", len(df_prod))
    with col2: st.metric("Valor Stock", f"${(df_prod['stock']*df_prod['precio']).sum():,.2f}")
    with col3: 
        total_ventas = df_mov[df_mov["tipo"]=="venta"]["total"].sum() if not df_mov.empty else 0
        st.metric("Total Ventas", f"${total_ventas:,.2f}")

# ===================== HISTORIAL =====================
elif menu == "📜 Historial":
    st.header("📜 Historial de Movimientos")
    conn = get_connection()
    df_hist = pd.read_sql_query("""
        SELECT m.fecha, m.tipo, p.nombre as producto, m.cantidad, m.precio_unitario, m.total
        FROM movimientos m 
        JOIN productos p ON m.producto_id = p.id
        ORDER BY m.fecha DESC
    """, conn)
    conn.close()
    
    if df_hist.empty:
        st.info("Aún no hay movimientos")
    else:
        st.dataframe(df_hist, use_container_width=True)

# ===================== CERRAR SESIÓN =====================
if st.sidebar.button("Cerrar Sesión"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.caption("✅ Sistema con Exportación Stock PDF + Excel")
