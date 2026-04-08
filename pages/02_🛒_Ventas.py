import streamlit as st
from database import get_connection
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. Seguridad: Verificar sesión
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Por favor, inicia sesión en la página principal.")
    st.stop()

st.header("🛒 Terminal de Ventas")

# 2. Estados de sesión para el carrito y el ticket generado
if "cart" not in st.session_state:
    st.session_state.cart = []
if "last_ticket_bin" not in st.session_state:
    st.session_state.last_ticket_bin = None

# --- FUNCIÓN GENERADORA DE PDF (Formato Ticket 80mm) ---
def generar_ticket_pdf(items, total, n_ticket, medio_pago):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 200*mm), 
                            rightMargin=2*mm, leftMargin=2*mm, topMargin=5*mm, bottomMargin=5*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    estilo_t = ParagraphStyle('T', fontSize=12, alignment=1, spaceAfter=5, fontName="Helvetica-Bold")
    estilo_n = ParagraphStyle('N', fontSize=8, alignment=1)
    
    elements.append(Paragraph("<b>COMPROBANTE DE VENTA</b>", estilo_t))
    elements.append(Paragraph(f"Ticket N°: {n_ticket:05d}", estilo_n))
    elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_n))
    elements.append(Paragraph(f"Medio de Pago: {medio_pago}", estilo_n))
    elements.append(Spacer(1, 5))
    
    data = [["Cant", "Producto", "Total"]]
    for i in items:
        data.append([str(i["cantidad"]), i["nombre"][:15], f"${i['subtotal']:.2f}"])
    
    table = Table(data, colWidths=[10*mm, 40*mm, 20*mm])
    table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, (0,0,0)),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    elements.append(table)
    
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"<b>TOTAL: ${total:.2f}</b>", estilo_t))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph("¡Gracias por su compra!", estilo_n))
    
    doc.build(elements)
    return buffer.getvalue()

# --- INTERFAZ: SELECCIÓN DE PRODUCTOS ---
conn = get_connection()
df_p = pd.read_sql_query("SELECT id, nombre, precio_venta, stock FROM productos WHERE stock > 0 ORDER BY nombre", conn)
conn.close()

with st.expander("➕ Añadir Productos", expanded=True):
    with st.form("form_carrito"):
        col_prod, col_cant = st.columns([3, 1])
        with col_prod:
            lista_nombres = df_p["nombre"].tolist() if not df_p.empty else ["Sin stock"]
            nombre_sel = st.selectbox("Producto", lista_nombres)
        with col_cant:
            cantidad_sel = st.number_input("Cantidad", min_value=1, value=1)
        
        if st.form_submit_button("Agregar al Carrito"):
            if not df_p.empty:
                row = df_p[df_p["nombre"] == nombre_sel].iloc[0]
                # Convertir a tipos nativos de Python para evitar error np.float64
                p_id = int(row['id'])
                p_stk = int(row['stock'])
                p_pre = float(row['precio_venta'])
                
                if cantidad_sel <= p_stk:
                    st.session_state.cart.append({
                        "id": p_id, "nombre": str(nombre_sel), 
                        "cantidad": int(cantidad_sel), "precio": p_pre, 
                        "subtotal": float(cantidad_sel * p_pre)
                    })
                    st.rerun()
                else:
                    st.error(f"Solo hay {p_stk} unidades disponibles.")

# --- VISUALIZACIÓN Y CIERRE DE VENTA ---
if st.session_state.cart:
    st.subheader("🛒 Resumen del Carrito")
    df_car = pd.DataFrame(st.session_state.cart)
    st.table(df_car[["nombre", "cantidad", "precio", "subtotal"]])
    
    total_venta = sum(item["subtotal"] for item in st.session_state.cart)
    st.metric("Total a Pagar", f"${total_venta:,.2f}")

    # Selección de medio de pago
    metodo = st.selectbox("💳 Seleccione Medio de Pago", 
                          ["Efectivo", "Tarjeta de Débito", "Tarjeta de Crédito", "Transferencia", "Billetera Virtual"])

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Vaciar Carrito", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
            
    with col_btn2:
        if st.button("✅ Finalizar Venta", type="primary", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            try:
                for item in st.session_state.cart:
                    # Limpieza estricta de tipos de datos
                    id_limpio = int(item["id"])
                    cant_limpia = int(item["cantidad"])
                    pre_limpio = float(item["precio"])
                    sub_limpio = float(item["subtotal"])

                    # 1. Actualizar Stock
                    cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cant_limpia, id_limpio))
                    
                    # 2. Registrar Movimiento
                    cur.execute("""
                        INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) 
                        VALUES ('venta', %s, %s, %s, %s)
                    """, (id_limpio, cant_limpia, pre_limpio, sub_limpio))
                
                # 3. Registrar Venta con Medio de Pago
                cur.execute("""
                    INSERT INTO ventas (cajero, total, medio_pago, items) 
                    VALUES (%s, %s, %s, %s) RETURNING ticket_num
                """, (st.session_state.username, float(total_venta), metodo, str(st.session_state.cart)))
                
                n_ticket = cur.fetchone()[0]
                conn.commit()
                
                # 4. Generar binario del PDF
                st.session_state.last_ticket_bin = generar_ticket_pdf(st.session_state.cart, total_venta, n_ticket, metodo)
                st.session_state.cart = [] # Limpiar carrito
                st.success(f"¡Venta exitosa! Ticket #{n_ticket}")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error procesando la venta: {e}")
            finally:
                cur.close()
                conn.close()

# --- BOTÓN DE DESCARGA DEL TICKET ---
if st.session_state.last_ticket_bin:
    st.divider()
    st.download_button(
        label="📥 Descargar / Imprimir Ticket",
        data=st.session_state.last_ticket_bin,
        file_name=f"ticket_{datetime.now().strftime('%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )
    if st.button("🔄 Iniciar Nueva Venta"):
        st.session_state.last_ticket_bin = None
        st.rerun()
