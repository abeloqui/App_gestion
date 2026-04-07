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
    usuario = st.text_input("Usuario", key="login_user")
    password = st.text_input("Contraseña", type="password", key="login_pass")
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
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tipo TEXT, 
        producto_id INTEGER, cantidad INTEGER, precio_unitario REAL, total REAL,
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_num INTEGER, fecha TEXT, 
        cajero TEXT, total REAL, medio_pago TEXT, items TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor INTEGER)''')
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
        return {"ticket_num": row[1], "fecha": row[2], "cajero": row[3], "total": row[4], "medio_pago": row[5], "items": eval(row[6])}
    return None

# ===================== TICKET PDF (80mm) =====================
def export_ticket_pdf(items, total, pago=None, vuelto=None, medio_pago="Efectivo", ticket_num=None, fecha=None, cajero=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 200*mm), rightMargin=2*mm, leftMargin=2*mm, topMargin=5*mm, bottomMargin=5*mm)
    elements = []
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle('T', fontSize=12, alignment=1, fontName="Helvetica-Bold")
    norm_s = ParagraphStyle('N', fontSize=8, alignment=1)
    
    elements.append(Paragraph("MI NEGOCIO", title_s))
    elements.append(Paragraph(f"Ticket: #{ticket_num:05d}", norm_s))
    elements.append(Paragraph(f"Fecha: {fecha if fecha else datetime.now().strftime('%d/%m/%Y %H:%M')}", norm_s))
    elements.append(Spacer(1, 5))
    
    data = [["Prod", "Cant", "Sub"]]
    for i in items: data.append([i["nombre"][:15], i["cantidad"], f"${i['subtotal']:.2f}"])
    
    t = Table(data, colWidths=[35*mm, 10*mm, 25*mm])
    t.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 7), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elements.append(t)
    elements.append(Paragraph(f"TOTAL: ${total:.2f}", title_s))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ===================== MENÚ =====================
if st.session_state.role == "admin":
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "➕ Agregar Producto", "✏️ Editar/Eliminar", "📉 Registrar Venta", "🔄 Reimprimir Ticket", "📊 Reportes", "📜 Historial"]
else:
    opciones = ["🏠 Dashboard", "📋 Ver Stock", "📉 Registrar Venta"]

menu = st.sidebar.selectbox("Menú Principal", opciones)

# ===================== SECCIONES =====================

if menu == "🏠 Dashboard":
    st.header("🏠 Resumen")
    df_prod = obtener_productos()
    conn = get_connection()
    df_mov = pd.read_sql_query('SELECT * FROM movimientos', conn)
    conn.close()
    c1, c2, c3 = st.columns(3)
    c1.metric("Productos", len(df_prod))
    c2.metric("Valor Inventario", f"${(df_prod['stock'] * df_prod['precio']).sum():,.2f}")
    hoy = datetime.now().strftime("%Y-%m-%d")
    v_hoy = df_mov[(df_mov["tipo"] == "venta") & (df_mov["fecha"].str.startswith(hoy))]["total"].sum() if not df_mov.empty else 0
    c3.metric("Ventas Hoy", f"${v_hoy:,.2f}")

elif menu == "📋 Ver Stock":
    st.header("📋 Stock Actual")
    st.dataframe(obtener_productos(), use_container_width=True)

elif menu == "➕ Agregar Producto":
    st.header("➕ Nuevo Producto")
    with st.form("add_p"):
        n = st.text_input("Nombre")
        cat = st.selectbox("Categoría", ["Almacén", "Bebidas", "Otros"])
        p = st.number_input("Precio", min_value=0.0)
        s = st.number_input("Stock", min_value=0)
        if st.form_submit_button("Guardar"):
            conn = get_connection()
            try:
                conn.execute("INSERT INTO productos (nombre, precio, stock, categoria) VALUES (?,?,?,?)", (n,p,s,cat))
                conn.commit()
                st.success("Guardado")
            except: st.error("Error: Nombre duplicado")
            finally: conn.close()

elif menu == "✏️ Editar/Eliminar":
    st.header("✏️ Editar Producto")
    df = obtener_productos()
    if df.empty:
        st.warning("No hay productos.")
    else:
        prod_list = df["nombre"].tolist()
        p_sel = st.selectbox("Seleccione producto", prod_list)
        # SEGURIDAD: Buscamos los datos solo si se seleccionó algo
        datos = df[df["nombre"] == p_sel].iloc[0]
        
        with st.container(border=True):
            n_nom = st.text_input("Nombre", value=datos["nombre"])
            n_pre = st.number_input("Precio", value=float(datos["precio"]))
            n_stk = st.number_input("Stock", value=int(datos["stock"]))
            
            c1, c2 = st.columns(2)
            if c1.button("Actualizar"):
                conn = get_connection()
                conn.execute("UPDATE productos SET nombre=?, precio=?, stock=? WHERE id=?", (n_nom, n_pre, n_stk, datos["id"]))
                conn.commit()
                conn.close()
                st.rerun()
            if c2.button("Eliminar", type="secondary"):
                conn = get_connection()
                conn.execute("DELETE FROM productos WHERE id=?", (datos["id"],))
                conn.commit()
                conn.close()
                st.rerun()

elif menu == "📉 Registrar Venta":
    st.header("📉 Venta")
    if "cart" not in st.session_state: st.session_state.cart = []
    df = obtener_productos()
    busc = st.text_input("Buscar...")
    f_df = df[df["nombre"].str.contains(busc, case=False)] if busc else df
    
    if not f_df.empty:
        p_v = st.selectbox("Producto", f_df["nombre"].tolist())
        r = f_df[f_df["nombre"] == p_v].iloc[0]
        can = st.number_input("Cant", 1, int(r["stock"]) if r["stock"] > 0 else 1)
        if st.button("Agregar"):
            st.session_state.cart.append({"id":int(r["id"]), "nombre":r["nombre"], "cantidad":can, "precio":r["precio"], "subtotal":can*r["precio"]})
            st.rerun()

    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        total = sum(x["subtotal"] for x in st.session_state.cart)
        st.subheader(f"Total: ${total}")
        if st.button("Finalizar"):
            t_n = get_next_ticket_number()
            for x in st.session_state.cart: registrar_movimiento("venta", x["id"], x["cantidad"], x["precio"])
            guardar_venta(t_n, st.session_state.cart, total, "Efectivo")
            st.session_state.cart = []
            st.success("Venta Exitosa")
            st.rerun()

elif menu == "🔄 Reimprimir Ticket":
    st.header("🔄 Reimprimir Ticket")
    conn = get_connection()
    df_v = pd.read_sql_query("SELECT ticket_num, fecha, total FROM ventas ORDER BY id DESC LIMIT 10", conn)
    conn.close()
    if df_v.empty: st.info("Sin ventas")
    else:
        op = [f"#{r['ticket_num']} - {r['fecha']} (${r['total']})" for _, r in df_v.iterrows()]
        sel = st.selectbox("Ticket", op)
        t_num = int(sel.split(" - ")[0].replace("#", ""))
        if st.button("Generar PDF"):
            v = obtener_venta_para_reimpresion(t_num)
            pdf = export_ticket_pdf(v['items'], v['total'], ticket_num=v['ticket_num'], fecha=v['fecha'])
            st.download_button("Descargar", pdf, f"ticket_{t_num}.pdf", "application/pdf")

elif menu == "📊 Reportes":
    st.header("📊 Reportes")
    conn = get_connection()
    df_v = pd.read_sql_query("SELECT fecha, total FROM ventas", conn)
    conn.close()
    if not df_v.empty:
        df_v["fecha"] = pd.to_datetime(df_v["fecha"])
        st.line_chart(df_v.set_index("fecha"))

elif menu == "📜 Historial":
    st.header("📜 Historial Movimientos")
    st.dataframe(pd.read_sql_query("SELECT * FROM movimientos ORDER BY id DESC", get_connection()))

# ===================== CIERRE =====================
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()
