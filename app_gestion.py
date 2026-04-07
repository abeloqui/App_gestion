import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# Para PDF y Reportes
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
    "cajero1": {"password": "1234", "role": "cajero"}
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
    
    # Verificar columna categoria
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_num INTEGER,
        fecha TEXT,
        cajero TEXT,
        total REAL,
        medio_pago TEXT,
        items TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        clave TEXT PRIMARY KEY,
        valor INTEGER
    )''')
    c.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES ('ultimo_ticket', 0)")
    conn.commit()
    conn.close()

init_db()

# ===================== FUNCIONES DE LÓGICA Y REPORTES =====================

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
    return True, "✅ Operación exitosa"

def obtener_productos():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, nombre, categoria, precio, stock, stock_minimo FROM productos ORDER BY nombre", conn)
    conn.close()
    return df

def guardar_venta(ticket_num, items, total, medio_pago):
    conn = get_connection()
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO ventas (ticket_num, fecha, cajero, total, medio_pago, items)
                 VALUES (?, ?, ?, ?, ?, ?)''', 
              (ticket_num, fecha, st.session_state.username, total, medio_pago, str(items)))
    conn.commit()
    conn.close()

def obtener_venta_para_reimpresion(ticket_num):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM ventas WHERE ticket_num = ? ORDER BY id DESC LIMIT 1", (ticket_num,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "ticket_num": row[1], "fecha": row[2], "cajero": row[3],
            "total": row[4], "medio_pago": row[5], "items": eval(row[6])
        }
    return None

# --- GENERACIÓN DE PDF: STOCK ---
def export_stock_to_pdf(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("<b>REPORTE DE STOCK ACTUAL</b>", styles['Title']))
    elements.append(Paragraph(f"Fecha de reporte: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    data = [["Producto", "Categoría", "Precio", "Stock", "Mínimo"]]
    for _, row in df.iterrows():
        data.append([row['nombre'], row['categoria'], f"${row['precio']:.2f}", str(row['stock']), str(row['stock_minimo'])])
    
    table = Table(data, colWidths=[65*mm, 40*mm, 25*mm, 20*mm, 25*mm])
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ])
    
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        if row['stock'] <= row['stock_minimo']:
            style.add('TEXTCOLOR', (3, i), (3, i), colors.red)
            style.add('FONTNAME', (3, i), (3, i), 'Helvetica-Bold')

    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- GENERACIÓN DE PDF: TICKET ---
def export_ticket_pdf(items, total, pago=None, vuelto=None, medio_pago="Efectivo", ticket_num=None, fecha=None, cajero=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 297*mm), rightMargin=4*mm, leftMargin=4*mm, topMargin=5*mm, bottomMargin=5*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T', fontSize=13, alignment=1, spaceAfter=6)
    header_style = ParagraphStyle('H', fontSize=8.5, alignment=1)
    
    elements.append(Paragraph("<b>MI NEGOCIO</b>", title_style))
    elements.append(Paragraph(f"Ticket #{ticket_num:05d}", header_style))
    elements.append(Paragraph(f"Fecha: {fecha if fecha else datetime.now().strftime('%d/%m/%Y %H:%M')}", header_style))
    elements.append(Spacer(1, 5))
    
    data = [["Prod", "Cant", "Subt"]]
    for item in items:
        data.append([item["nombre"][:15], str(item["cantidad"]), f"${item['subtotal']:.2f}"])
    
    table = Table(data, colWidths=[35*mm, 12*mm, 20*mm])
    table.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
    elements.append(table)
    
    elements.append(Paragraph(f"<b>TOTAL: ${total:.2f}</b>", title_style))
    elements.append(Paragraph(f"Pago: {medio_pago}", header_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ===================== MENÚ Y NAVEGACIÓN =====================
if st.session_state.role == "admin":
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "📉 Registrar Venta", "🔄 Reimprimir Ticket", "📜 Historial"]
else:
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "📉 Registrar Venta"]

menu = st.sidebar.selectbox("Menú Principal", opciones)
st.sidebar.write(f"👤 {st.session_state.username}")

# ===================== DASHBOARD =====================
if menu == "🏠 Dashboard":
    st.header("🏠 Dashboard")
    df_prod = obtener_productos()
    conn = get_connection()
    df_mov = pd.read_sql_query('SELECT * FROM movimientos ORDER BY fecha DESC', conn)
    conn.close()

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Productos", len(df_prod))
    with col2: st.metric("Inventario", f"${(df_prod['stock'] * df_prod['precio']).sum():,.2f}")
    with col3:
        hoy = datetime.now().strftime("%Y-%m-%d")
        ventas_hoy = df_mov[(df_mov["tipo"] == "venta") & (df_mov["fecha"].str.startswith(hoy))]["total"].sum() if not df_mov.empty else 0
        st.metric("Ventas Hoy", f"${ventas_hoy:,.2f}")
    with col4:
        hace_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        ventas_sem = df_mov[(df_mov["tipo"] == "venta") & (df_mov["fecha"] >= hace_7)]["total"].sum() if not df_mov.empty else 0
        st.metric("Ventas Semana", f"${ventas_sem:,.2f}")

# ===================== VER STOCK =====================
elif menu == "📋 Ver Stock":
    st.header("📋 Stock Actual")
    df = obtener_productos()
    
    if df.empty:
        st.warning("No hay productos.")
    else:
        categoria = st.selectbox("Categoría", ["Todas"] + sorted(df["categoria"].unique().tolist()))
        df_f = df[df["categoria"] == categoria] if categoria != "Todas" else df
        st.dataframe(df_f, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 Exportar a PDF", type="primary"):
                pdf_data = export_stock_to_pdf(df_f)
                st.download_button("Descargar PDF", pdf_data, "stock.pdf", "application/pdf")
        with col2:
            if st.button("📊 Exportar a Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_f.to_excel(writer, index=False)
                st.download_button("Descargar Excel", output.getvalue(), "stock.xlsx")

# ===================== REGISTRAR VENTA =====================
elif menu == "📉 Registrar Venta":
    st.header("📉 Venta Nueva")
    if "cart" not in st.session_state: st.session_state.cart = []
    if "last_ticket" not in st.session_state: st.session_state.last_ticket = None

    df = obtener_productos()
    producto_sel = st.selectbox("Producto", df["nombre"].tolist())
    row = df[df["nombre"] == producto_sel].iloc[0]
    
    col_c, col_b = st.columns([2,1])
    with col_c:
        cant = st.number_input("Cantidad", min_value=1, max_value=int(row['stock']), value=1)
    with col_b:
        if st.button("➕ Añadir"):
            st.session_state.cart.append({"id": int(row["id"]), "nombre": row["nombre"], "cantidad": cant, "precio": row["precio"], "subtotal": cant * row["precio"]})
            st.rerun()

    if st.session_state.cart:
        total = sum(i["subtotal"] for i in st.session_state.cart)
        st.write(st.session_state.cart)
        st.metric("TOTAL", f"${total:.2f}")
        
        medio = st.selectbox("Pago", ["Efectivo", "Transferencia"])
        if st.button("Finalizar Venta"):
            tk = get_next_ticket_number()
            for i in st.session_state.cart:
                registrar_movimiento("venta", i["id"], i["cantidad"], i["precio"])
            guardar_venta(tk, st.session_state.cart, total, medio)
            st.session_state.last_ticket = export_ticket_pdf(st.session_state.cart, total, ticket_num=tk, medio_pago=medio)
            st.session_state.cart = []
            st.rerun()
    
    if st.session_state.last_ticket:
        st.download_button("Descargar Ticket", st.session_state.last_ticket, "ticket.pdf", "application/pdf")

# ===================== REIMPRIMIR TICKET =====================
elif menu == "🔄 Reimprimir Ticket":
    st.header("🔄 Reimpresión")
    conn = get_connection()
    df_v = pd.read_sql_query("SELECT ticket_num, fecha, total FROM ventas ORDER BY id DESC LIMIT 10", conn)
    conn.close()
    
    if not df_v.empty:
        sel = st.selectbox("Ticket", df_v["ticket_num"].tolist())
        if st.button("Generar PDF"):
            v = obtener_venta_para_reimpresion(sel)
            pdf = export_ticket_pdf(v['items'], v['total'], ticket_num=v['ticket_num'], medio_pago=v['medio_pago'], fecha=v['fecha'], cajero=v['cajero'])
            st.download_button("Descargar", pdf, f"ticket_{sel}.pdf", "application/pdf")

# ===================== CERRAR SESIÓN =====================
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()
