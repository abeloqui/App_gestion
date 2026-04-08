import streamlit as st
from database import get_connection
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("🛒 Registrar Venta")

# Inicializar estados
if "cart" not in st.session_state: st.session_state.cart = []
if "last_ticket_bin" not in st.session_state: st.session_state.last_ticket_bin = None

def generar_ticket_pdf(items, total, n_ticket):
    buffer = BytesIO()
    # Tamaño típico 80mm
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 200*mm), 
                            rightMargin=2*mm, leftMargin=2*mm, topMargin=5*mm, bottomMargin=5*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    estilo_t = ParagraphStyle('T', fontSize=12, alignment=1, spaceAfter=5)
    estilo_n = ParagraphStyle('N', fontSize=8, alignment=1)
    
    elements.append(Paragraph("<b>MI NEGOCIO</b>", estilo_t))
    elements.append(Paragraph(f"Ticket N°: {n_ticket:05d}", estilo_n))
    elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_n))
    elements.append(Spacer(1, 5))
    
    # Tabla de productos
    data = [["Cant", "Prod", "Total"]]
    for i in items:
        data.append([str(i["cantidad"]), i["nombre"][:12], f"${i['subtotal']:.2f}"])
    
    table = Table(data, colWidths=[10*mm, 35*mm, 25*mm])
    table.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, (0,0,0))]))
    elements.append(table)
    
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"<b>TOTAL: ${total:.2f}</b>", estilo_t))
    elements.append(Paragraph("¡Gracias por su compra!", estilo_n))
    
    doc.build(elements)
    return buffer.getvalue()

# --- Interfaz de Selección ---
conn = get_connection()
df = pd.read_sql_query("SELECT id, nombre, precio_venta, stock FROM productos WHERE stock > 0", conn)
conn.close()

with st.form("venta_form"):
    col1, col2 = st.columns(2)
    with col1:
        prod_sel = st.selectbox("Producto", df["nombre"].tolist() if not df.empty else [])
    with col2:
        cant = st.number_input("Cantidad", min_value=1, value=1)
    
    if st.form_submit_button("➕ Añadir"):
        if not df.empty:
            row = df[df["nombre"] == prod_sel].iloc[0]
            if cant <= row['stock']:
                st.session_state.cart.append({
                    "id": int(row['id']), "nombre": row['nombre'], 
                    "cantidad": cant, "precio": row['precio_venta'], 
                    "subtotal": cant * row['precio_venta']
                })
                st.rerun()
            else: st.error("Stock insuficiente.")

if st.session_state.cart:
    total_venta = sum(i["subtotal"] for i in st.session_state.cart)
    st.table(st.session_state.cart)
    st.subheader(f"Total: ${total_venta:.2f}")
    
    if st.button("✅ Finalizar y Generar Ticket"):
        conn = get_connection()
        cur = conn.cursor()
        try:
            # Obtener número de ticket (usando serial de BD o lógica manual)
            for i in st.session_state.cart:
                cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (i["cantidad"], i["id"]))
                cur.execute("INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) VALUES ('venta', %s, %s, %s, %s)",
                          (i["id"], i["cantidad"], i["precio"], i["subtotal"]))
            
            cur.execute("INSERT INTO ventas (cajero, total, items) VALUES (%s, %s, %s) RETURNING ticket_num",
                      (st.session_state.username, total_venta, str(st.session_state.cart)))
            n_ticket = cur.fetchone()[0]
            conn.commit()
            
            # Generar PDF
            st.session_state.last_ticket_bin = generar_ticket_pdf(st.session_state.cart, total_venta, n_ticket)
            st.session_state.cart = [] # Vaciar carrito
            st.success("Venta realizada con éxito.")
            st.rerun()
        finally:
            conn.close()

# Botón de descarga persistente si hay un ticket generado
if st.session_state.last_ticket_bin:
    st.download_button(
        label="📥 Descargar/Imprimir Ticket",
        data=st.session_state.last_ticket_bin,
        file_name=f"ticket_{datetime.now().strftime('%H%M%S')}.pdf",
        mime="application/pdf",
        type="primary"
    )
