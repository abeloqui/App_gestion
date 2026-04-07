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

# ===================== CONFIGURACIÓN DE PÁGINA =====================
st.set_page_config(page_title="Gestión Stock y Ventas", layout="wide")

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
    st.title("📦 Sistema de Gestión")
    st.subheader("🔐 Iniciar Sesión")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar", type="primary"):
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

# ===================== FUNCIONES LÓGICA =====================
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
    return True, "✅ Movimiento registrado"

def obtener_productos():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre", conn)
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
            "ticket_num": row[1],
            "fecha": row[2],
            "cajero": row[3],
            "total": row[4],
            "medio_pago": row[5],
            "items": eval(row[6])
        }
    return None

# ===================== TICKET PDF (XPRINTER 80mm) =====================
def export_ticket_pdf(items, total, pago=None, vuelto=None, medio_pago="Efectivo", ticket_num=None, fecha=None, cajero=None):
    buffer = BytesIO()
    EMPRESA = "MI NEGOCIO"
    DIRECCION = "Neuquén, Argentina"
    TELEFONO = "299-1234567"
    
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 200*mm), 
                            rightMargin=2*mm, leftMargin=2*mm, topMargin=5*mm, bottomMargin=5*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=12, alignment=1)
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=8, alignment=1)
    
    elements.append(Paragraph(f"<b>{EMPRESA}</b>", title_style))
    elements.append(Paragraph(DIRECCION, header_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"Ticket: #{ticket_num:05d}", header_style))
    elements.append(Paragraph(f"Fecha: {fecha if fecha else datetime.now().strftime('%Y-%m-%d')}", header_style))
    elements.append(Spacer(1, 5))
    
    data = [["Prod", "Cant", "Subt"]]
    for i in items:
        data.append([i["nombre"][:15], i["cantidad"], f"${i['subtotal']:.2f}"])
    
    table = Table(data, colWidths=[35*mm, 10*mm, 25*mm])
    table.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
    elements.append(table)
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"<b>TOTAL: ${total:.2f}</b>", title_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ===================== MENÚ LATERAL =====================
if st.session_state.role == "admin":
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "➕ Agregar Producto", "✏️ Editar/Eliminar",
                "📉 Registrar Venta", "🔄 Reimprimir Ticket", "📊 Reportes", "📜 Historial Movimientos"]
else:
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "📉 Registrar Venta"]

menu = st.sidebar.selectbox("Menú Principal", opciones)
st.sidebar.divider()
st.sidebar.write(f"👤 {st.session_state.username} ({st.session_state.role})")

# ===================== LÓGICA DE SECCIONES =====================

if menu == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    df_prod = obtener_productos()
    conn = get_connection()
    df_mov = pd.read_sql_query('SELECT * FROM movimientos', conn)
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Productos", len(df_prod))
    col2.metric("Valor Stock", f"${(df_prod['stock'] * df_prod['precio']).sum():,.2f}")
    
    hoy = datetime.now().strftime("%Y-%m-%d")
    ventas_hoy = df_mov[(df_mov["tipo"] == "venta") & (df_mov["fecha"].str.startswith(hoy))]["total"].sum() if not df_mov.empty else 0
    col3.metric("Ventas Hoy", f"${ventas_hoy:,.2f}")

elif menu == "📋 Ver Stock":
    st.header("📋 Stock Actual")
    df = obtener_productos()
    st.dataframe(df, use_container_width=True)
    
    bajos = df[df["stock"] <= df["stock_minimo"]]
    if not bajos.empty:
        st.error("⚠️ Alerta Stock Bajo")
        st.table(bajos[["nombre", "stock", "stock_minimo"]])

elif menu == "➕ Agregar Producto":
    st.header("➕ Agregar Nuevo Producto")
    with st.form("form_nuevo"):
        nombre = st.text_input("Nombre del Producto")
        categoria = st.selectbox("Categoría", ["Almacén", "Bebidas", "Comida", "Otros"])
        precio = st.number_input("Precio de Venta", min_value=0.0)
        stock_ini = st.number_input("Stock Inicial", min_value=0)
        s_min = st.number_input("Stock Mínimo Alerta", min_value=0, value=5)
        
        if st.form_submit_button("Guardar Producto"):
            if nombre:
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO productos (nombre, precio, stock, stock_minimo, categoria) VALUES (?,?,?,?,?)",
                              (nombre, precio, stock_ini, s_min, categoria))
                    conn.commit()
                    conn.close()
                    st.success("✅ Producto creado con éxito")
                except:
                    st.error("❌ El nombre ya existe")
            else:
                st.warning("Escriba un nombre")

elif menu == "✏️ Editar/Eliminar":
    st.header("✏️ Gestionar Productos")
    df = obtener_productos()
    if not df.empty:
        prod_sel = st.selectbox("Seleccione Producto", df["nombre"].tolist())
        datos = df[df["nombre"] == prod_sel].iloc[0]
        
        with st.container(border=True):
            nuevo_nombre = st.text_input("Nombre", value=datos["nombre"])
            nuevo_precio = st.number_input("Precio", value=float(datos["precio"]))
            nuevo_stock = st.number_input("Stock actual", value=int(datos["stock"]))
            
            col1, col2 = st.columns(2)
            if col1.button("💾 Actualizar"):
                conn = get_connection()
                c = conn.cursor()
                c.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", 
                          (nuevo_nombre, nuevo_precio, nuevo_stock, datos["id"]))
                conn.commit()
                conn.close()
                st.success("Actualizado")
                st.rerun()
            
            if col2.button("🗑️ Eliminar", type="secondary"):
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM productos WHERE id=?", (datos["id"],))
                conn.commit()
                conn.close()
                st.warning("Eliminado")
                st.rerun()

elif menu == "📉 Registrar Venta":
    st.header("📉 Punto de Venta")
    if "cart" not in st.session_state: st.session_state.cart = []
    
    df = obtener_productos()
    buscar = st.text_input("🔍 Buscar Producto")
    opc = df[df["nombre"].str.contains(buscar, case=False)]["nombre"].tolist() if buscar else df["nombre"].tolist()
    
    if opc:
        p_sel = st.selectbox("Producto", opc)
        row = df[df["nombre"] == p_sel].iloc[0]
        cant = st.number_input("Cantidad", min_value=1, max_value=int(row["stock"]))
        
        if st.button("➕ Agregar"):
            st.session_state.cart.append({
                "id": int(row["id"]), "nombre": row["nombre"], "cantidad": cant,
                "precio": float(row["precio"]), "subtotal": cant * float(row["precio"])
            })
            st.rerun()
            
    if st.session_state.cart:
        st.subheader("🛒 Carrito")
        for i, it in enumerate(st.session_state.cart):
            st.write(f"{it['nombre']} x{it['cantidad']} - ${it['subtotal']}")
        
        total = sum(i["subtotal"] for i in st.session_state.cart)
        st.title(f"TOTAL: ${total:.2f}")
        
        medio = st.selectbox("Pago", ["Efectivo", "Transferencia", "Tarjeta"])
        
        if st.button("✅ Finalizar Venta"):
            ticket = get_next_ticket_number()
            for it in st.session_state.cart:
                registrar_movimiento("venta", it["id"], it["cantidad"], it["precio"])
            guardar_venta(ticket, st.session_state.cart, total, medio)
            st.session_state.cart = []
            st.success("Venta realizada")
            st.rerun()

elif menu == "📊 Reportes":
    st.header("📊 Resumen de Ventas")
    conn = get_connection()
    df_v = pd.read_sql_query("SELECT fecha, total FROM ventas", conn)
    conn.close()
    if not df_v.empty:
        df_v["fecha"] = pd.to_datetime(df_v["fecha"])
        st.line_chart(df_v.set_index("fecha"))
    else:
        st.info("No hay datos")

elif menu == "📜 Historial Movimientos":
    st.header("📜 Historial Completo")
    conn = get_connection()
    df_m = pd.read_sql_query("SELECT * FROM movimientos ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(df_m)

elif menu == "🔄 Reimprimir Ticket":
    st.header("🔄 Reimprimir")
    # ... (Lógica de reimpresión de tu código original)

# ===================== CERRAR SESIÓN =====================
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()
