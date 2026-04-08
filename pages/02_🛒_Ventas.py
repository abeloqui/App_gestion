import streamlit as st
from database import get_connection, get_engine
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. Validación de Sesión
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Por favor, inicia sesión en la página principal.")
    st.stop()

st.header("🛒 Terminal de Ventas")

# Inicializar estados de sesión
if "cart" not in st.session_state: st.session_state.cart = []
if "ticket_listo" not in st.session_state: st.session_state.ticket_listo = None

# --- FUNCIÓN GENERADORA DE PDF ---
def generar_ticket_pdf(items, total, n_ticket, metodo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 150*mm), 
                            rightMargin=2*mm, leftMargin=2*mm, topMargin=5*mm, bottomMargin=5*mm)
    elements = []
    styles = getSampleStyleSheet()
    estilo_t = ParagraphStyle('T', fontSize=12, alignment=1, spaceAfter=5, fontName="Helvetica-Bold")
    estilo_n = ParagraphStyle('N', fontSize=8, alignment=1)
    
    elements.append(Paragraph("<b>MI COMERCIO</b>", estilo_t))
    elements.append(Paragraph(f"Ticket N°: {n_ticket:05d}", estilo_n))
    elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_n))
    elements.append(Paragraph(f"Pago: {metodo}", estilo_n))
    elements.append(Spacer(1, 5))
    
    data = [["Cant", "Prod", "Subt"]]
    for i in items:
        data.append([str(i["cantidad"]), i["nombre"][:12], f"${i['subtotal']:.2f}"])
    
    t = Table(data, colWidths=[10*mm, 35*mm, 25*mm])
    t.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, (0,0,0))]))
    elements.append(t)
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"<b>TOTAL: ${total:.2f}</b>", estilo_t))
    doc.build(elements)
    return buffer.getvalue()

# --- SELECCIÓN DE PRODUCTOS ---
engine = get_engine()
df_p = pd.read_sql("SELECT id, nombre, precio_venta, stock FROM productos WHERE stock > 0 ORDER BY nombre", engine)

with st.expander("➕ Agregar al Carrito", expanded=True):
    col1, col2 = st.columns([3, 1])
    p_sel = col1.selectbox("Producto", df_p['nombre'].tolist() if not df_p.empty else ["Sin Stock"])
    cant = col2.number_input("Cantidad", min_value=1, value=1)
    
    if st.button("Añadir al Carrito ➕"):
        if not df_p.empty:
            row = df_p[df_p['nombre'] == p_sel].iloc[0]
            st.session_state.cart.append({
                "id": int(row['id']), "nombre": str(p_sel), 
                "cantidad": int(cant), "precio": float(row['precio_venta']), 
                "subtotal": float(cant * row['precio_venta'])
            })
            st.rerun()

# --- MOSTRAR CARRITO Y FINALIZAR ---
if st.session_state.cart:
    st.subheader("🛒 Items en Carrito")
    st.table(pd.DataFrame(st.session_state.cart)[["nombre", "cantidad", "subtotal"]])
    
    total_v = sum(i['subtotal'] for i in st.session_state.cart)
    metodo = st.selectbox("💳 Medio de Pago", ["Efectivo", "Tarjeta", "Transferencia", "QR"])
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("🗑️ Vaciar Carrito", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
            
    with col_c2:
        if st.button("✅ FINALIZAR VENTA", type="primary", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            try:
                items_ticket = list(st.session_state.cart)
                for i in st.session_state.cart:
                    # 1. Descontar Producto Principal
                    cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (int(i['cantidad']), int(i['id'])))
                    # 2. Descontar Insumos (Recetas) si existen
                    cur.execute("SELECT insumo_id, cantidad FROM recetas WHERE plato_id = %s", (int(i['id']),))
                    for ins_id, cant_r in cur.fetchall():
                        cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (float(cant_r * i['cantidad']), ins_id))
                    # 3. Registrar Movimiento
                    cur.execute("INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) VALUES ('venta',%s,%s,%s,%s)",
                              (int(i['id']), int(i['cantidad']), float(i['precio']), float(i['subtotal'])))
                
                # 4. Registrar Venta General
                cur.execute("INSERT INTO ventas (cajero, total, medio_pago, items) VALUES (%s,%s,%s,%s) RETURNING ticket_num",
                          (st.session_state.username, float(total_v), metodo, str(items_ticket)))
                n_ticket = cur.fetchone()[0]
                conn.commit()
                
                # Generar Ticket para descarga
                st.session_state.ticket_listo = generar_ticket_pdf(items_ticket, total_v, n_ticket, metodo)
                st.session_state.cart = [] 
                st.success(f"Venta registrada! Ticket #{n_ticket}")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                conn.close()

# --- SECCIÓN DE DESCARGA (Persistente) ---
if st.session_state.ticket_listo is not None:
    st.divider()
    st.balloons()
    st.subheader("📄 Ticket Generado")
    st.download_button(
        label="📥 DESCARGAR / IMPRIMIR TICKET",
        data=st.session_state.ticket_listo,
        file_name=f"ticket_{datetime.now().strftime('%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )
    if st.button("🔄 Preparar Nueva Venta", use_container_width=True):
        st.session_state.ticket_listo = None
        st.rerun()
