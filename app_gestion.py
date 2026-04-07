import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# Para PDF
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
    c.execute('''CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT, tipo TEXT, producto_id INTEGER, cantidad INTEGER, precio_unitario REAL, total REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_num INTEGER, fecha TEXT, cajero TEXT, total REAL, medio_pago TEXT, items TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor INTEGER)''')
    c.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES ('ultimo_ticket', 0)")
    conn.commit()
    conn.close()

init_db()

# ===================== FUNCIONES PDF =====================
def export_stock_to_pdf(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("REPORTE DE STOCK", styles['Title']))
    data = [["Producto", "Categoría", "Precio", "Stock"]]
    for _, r in df.iterrows():
        data.append([r['nombre'], r['categoria'], f"${r['precio']:.2f}", str(r['stock'])])
    t = Table(data, colWidths=[70*mm, 40*mm, 30*mm, 30*mm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.grey),('GRID',(0,0),(-1,-1),0.5,colors.black)]))
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

def export_ticket_pdf(items, total, ticket_num, medio_pago, fecha=None, cajero=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 200*mm), margin=2*mm)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"<b>TICKET #{ticket_num:05d}</b>", styles['Title']))
    elements.append(Paragraph(f"Fecha: {fecha if fecha else datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    data = [["Prod", "Cant", "Subt"]]
    for i in items: data.append([i["nombre"][:15], str(i["cantidad"]), f"${i['subtotal']:.2f}"])
    t = Table(data, colWidths=[35*mm, 10*mm, 20*mm])
    elements.append(t)
    elements.append(Paragraph(f"TOTAL: ${total:.2f}", styles['Title']))
    doc.build(elements)
    return buffer.getvalue()

# ===================== FUNCIONES LÓGICA =====================
def obtener_productos():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre", conn)
    conn.close()
    return df

def get_next_ticket_number():
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE config SET valor = valor + 1 WHERE clave = 'ultimo_ticket'")
    c.execute("SELECT valor FROM config WHERE clave = 'ultimo_ticket'")
    res = c.fetchone()[0]
    conn.commit()
    conn.close()
    return res

# ===================== MENÚ =====================
if st.session_state.role == "admin":
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "➕ Agregar Producto", "📉 Registrar Venta", "🔄 Reimprimir Ticket"]
else:
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "📉 Registrar Venta"]

menu = st.sidebar.selectbox("Menú", opciones)

# ===================== DASHBOARD =====================
if menu == "🏠 Dashboard":
    st.header("🏠 Dashboard")
    df_prod = obtener_productos()
    conn = get_connection()
    df_mov = pd.read_sql_query('SELECT * FROM movimientos', conn)
    conn.close()
    col1, col2 = st.columns(2)
    col1.metric("Productos", len(df_prod))
    col2.metric("Ventas Totales", f"${df_mov[df_mov['tipo']=='venta']['total'].sum():,.2f}")

# ===================== VER STOCK =====================
elif menu == "📋 Ver Stock":
    st.header("📋 Stock Actual")
    df = obtener_productos()
    st.dataframe(df, use_container_width=True)
    if st.button("📄 Exportar PDF"):
        pdf = export_stock_to_pdf(df)
        st.download_button("Descargar PDF", pdf, "stock.pdf", "application/pdf")

# ===================== AGREGAR PRODUCTO (NUEVO) =====================
elif menu == "➕ Agregar Producto":
    st.header("➕ Nuevo Producto")
    with st.form("form_add"):
        nombre = st.text_input("Nombre del producto")
        cat = st.text_input("Categoría", value="General")
        precio = st.number_input("Precio", min_value=0.0, step=0.1)
        stock = st.number_input("Stock Inicial", min_value=0, step=1)
        minimo = st.number_input("Stock Mínimo", min_value=0, value=5)
        if st.form_submit_button("Guardar Producto"):
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("INSERT INTO productos (nombre, categoria, precio, stock, stock_minimo) VALUES (?,?,?,?,?)",
                          (nombre, cat, precio, stock, minimo))
                conn.commit()
                conn.close()
                st.success("Producto agregado!")
            except:
                st.error("El nombre ya existe.")

# ===================== REGISTRAR VENTA =====================
elif menu == "📉 Registrar Venta":
    st.header("📉 Venta")
    if "cart" not in st.session_state: st.session_state.cart = []
    if "last_ticket_pdf" not in st.session_state: st.session_state.last_ticket_pdf = None

    df = obtener_productos()
    prod_nom = st.selectbox("Producto", df["nombre"].tolist())
    row = df[df["nombre"] == prod_nom].iloc[0]
    cant = st.number_input("Cantidad", 1, int(row['stock']))
    
    if st.button("➕ Añadir"):
        st.session_state.cart.append({"id": int(row["id"]), "nombre": row["nombre"], "cantidad": cant, "precio": row["precio"], "subtotal": cant * row["precio"]})
    
    if st.session_state.cart:
        total = sum(i["subtotal"] for i in st.session_state.cart)
        st.table(st.session_state.cart)
        st.subheader(f"Total: ${total:.2f}")
        if st.button("✅ Finalizar"):
            tk = get_next_ticket_number()
            conn = get_connection()
            c = conn.cursor()
            for i in st.session_state.cart:
                c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (i["cantidad"], i["id"]))
                c.execute("INSERT INTO movimientos (fecha, tipo, producto_id, cantidad, precio_unitario, total) VALUES (?,?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d"), "venta", i["id"], i["cantidad"], i["precio"], i["subtotal"]))
            
            # Guardar en tabla ventas
            c.execute("INSERT INTO ventas (ticket_num, fecha, cajero, total, medio_pago, items) VALUES (?,?,?,?,?,?)",
                      (tk, datetime.now().strftime("%Y-%m-%d %H:%M"), st.session_state.username, total, "Efectivo", str(st.session_state.cart)))
            conn.commit()
            conn.close()
            
            # GENERAR PDF Y GUARDAR SOLO LOS BYTES
            st.session_state.last_ticket_pdf = export_ticket_pdf(st.session_state.cart, total, tk, "Efectivo")
            st.session_state.cart = []
            st.success("Venta realizada!")
            st.rerun()

    if st.session_state.last_ticket_pdf:
        st.download_button("📥 Descargar Ticket", st.session_state.last_ticket_pdf, "ticket.pdf", "application/pdf")

# ===================== REIMPRIMIR TICKET =====================
elif menu == "🔄 Reimprimir Ticket":
    st.header("🔄 Reimpresión")
    conn = get_connection()
    df_v = pd.read_sql_query("SELECT ticket_num, fecha, total, items, medio_pago, cajero FROM ventas ORDER BY id DESC LIMIT 10", conn)
    conn.close()
    if not df_v.empty:
        sel = st.selectbox("Seleccione Ticket", df_v["ticket_num"].tolist())
        if st.button("Generar PDF"):
            v = df_v[df_v["ticket_num"] == sel].iloc[0]
            pdf = export_ticket_pdf(eval(v['items']), v['total'], v['ticket_num'], v['medio_pago'], v['fecha'], v['cajero'])
            st.download_button("Descargar Reimpresión", pdf, f"ticket_{sel}.pdf", "application/pdf")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()
