import streamlit as st
from database import get_connection
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. Verificación de Seguridad
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Por favor, inicia sesión en la página principal.")
    st.stop()

st.header("🛒 Terminal de Ventas")

# 2. Inicialización de estados de sesión
if "cart" not in st.session_state:
    st.session_state.cart = []
if "last_ticket_bin" not in st.session_state:
    st.session_state.last_ticket_bin = None

# --- FUNCIÓN PARA GENERAR EL PDF DEL TICKET ---
def generar_ticket_pdf(items, total, n_ticket):
    buffer = BytesIO()
    # Formato térmico 80mm
    doc = SimpleDocTemplate(buffer, pagesize=(80*mm, 200*mm), 
                            rightMargin=2*mm, leftMargin=2*mm, topMargin=5*mm, bottomMargin=5*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle('T', fontSize=12, alignment=1, spaceAfter=5, fontName="Helvetica-Bold")
    estilo_texto = ParagraphStyle('N', fontSize=8, alignment=1)
    
    elements.append(Paragraph("<b>MI SISTEMA DE GESTIÓN</b>", estilo_titulo))
    elements.append(Paragraph(f"Ticket N°: {n_ticket:05d}", estilo_texto))
    elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_texto))
    elements.append(Paragraph(f"Atendido por: {st.session_state.username}", estilo_texto))
    elements.append(Spacer(1, 5))
    
    # Tabla de productos
    data = [["Cant", "Producto", "Subtotal"]]
    for i in items:
        # Limpieza de nombres largos para que no rompan la tabla
        nombre_corto = i["nombre"][:15]
        data.append([str(i["cantidad"]), nombre_corto, f"${i['subtotal']:.2f}"])
    
    table = Table(data, colWidths=[10*mm, 40*mm, 20*mm])
    table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, (0,0,0)),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    elements.append(table)
    
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"<b>TOTAL A PAGAR: ${total:.2f}</b>", estilo_titulo))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph("¡Gracias por su preferencia!", estilo_texto))
    # ... (Código anterior igual hasta llegar a la sección del total)

if st.session_state.cart:
    total_final = sum(item["subtotal"] for item in st.session_state.cart)
    st.metric("TOTAL VENTA", f"${total_final:,.2f}")

    # --- NUEVO: Selección de Medio de Pago ---
    medio_pago = st.selectbox("💳 Medio de Pago", ["Efectivo", "Tarjeta de Débito", "Tarjeta de Crédito", "Transferencia", "QR / Billetera Virtual"])
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if st.button("🗑️ Vaciar Carrito", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
            
    with col_v2:
        if st.button("✅ Confirmar Venta", type="primary", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            try:
                for item in st.session_state.cart:
                    c_id = int(item["id"])
                    c_cant = int(item["cantidad"])
                    c_pre = float(item["precio"])
                    c_sub = float(item["subtotal"])

                    cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (c_cant, c_id))
                    cur.execute("""
                        INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) 
                        VALUES ('venta', %s, %s, %s, %s)
                    """, (c_id, c_cant, c_pre, c_sub))
                
                # --- ACTUALIZADO: Guardamos el medio de pago en la BD ---
                cur.execute("""
                    INSERT INTO ventas (cajero, total, medio_pago, items) 
                    VALUES (%s, %s, %s, %s) RETURNING ticket_num
                """, (st.session_state.username, float(total_final), medio_pago, str(st.session_state.cart)))
                
                n_ticket_generado = cur.fetchone()[0]
                conn.commit()
                
                st.session_state.last_ticket_bin = generar_ticket_pdf(st.session_state.cart, total_final, n_ticket_generado)
                st.session_state.cart = [] 
                st.success(f"Venta registrada ({medio_pago}). Ticket N° {n_ticket_generado}")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                conn.close()
    doc.build(elements)
    return buffer.getvalue()

# --- INTERFAZ DE CARGA DE PRODUCTOS ---
conn = get_connection()
# Obtenemos productos disponibles
df_p = pd.read_sql_query("SELECT id, nombre, precio_venta, stock FROM productos WHERE stock > 0 ORDER BY nombre", conn)
conn.close()

with st.expander("➕ Añadir Productos al Carrito", expanded=True):
    with st.form("form_add_cart"):
        col_p, col_c = st.columns([3, 1])
        with col_p:
            opciones = df_p["nombre"].tolist() if not df_p.empty else ["Sin stock disponible"]
            prod_nombre = st.selectbox("Seleccione Producto", opciones)
        with col_c:
            cantidad_v = st.number_input("Cantidad", min_value=1, value=1, step=1)
        
        btn_add = st.form_submit_button("Añadir al Carrito")
        
        if btn_add and not df_p.empty:
            row = df_p[df_p["nombre"] == prod_nombre].iloc[0]
            # IMPORTANTE: Convertimos a tipos nativos para evitar errores de NumPy
            p_id = int(row['id'])
            p_nom = str(row['nombre'])
            p_pre = float(row['precio_venta'])
            p_stk = int(row['stock'])
            
            if cantidad_v <= p_stk:
                st.session_state.cart.append({
                    "id": p_id, 
                    "nombre": p_nom, 
                    "cantidad": int(cantidad_v), 
                    "precio": p_pre, 
                    "subtotal": float(cantidad_v * p_pre)
                })
                st.toast(f"✅ {p_nom} añadido")
            else:
                st.error(f"Stock insuficiente (Disponible: {p_stk})")

# --- VISUALIZACIÓN DEL CARRITO Y FINALIZACIÓN ---
if st.session_state.cart:
    st.subheader("🛒 Carrito Actual")
    df_carrito = pd.DataFrame(st.session_state.cart)
    st.table(df_carrito[["nombre", "cantidad", "precio", "subtotal"]])
    
    total_final = sum(item["subtotal"] for item in st.session_state.cart)
    st.metric("TOTAL VENTA", f"${total_final:,.2f}")

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if st.button("🗑️ Vaciar Carrito", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
            
    with col_v2:
        if st.button("✅ Confirmar Venta", type="primary", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            try:
                # Procesamos cada item del carrito
                for item in st.session_state.cart:
                    # LIMPIEZA CRÍTICA: Convertir tipos NumPy a Python nativo
                    c_id = int(item["id"])
                    c_cant = int(item["cantidad"])
                    c_pre = float(item["precio"])
                    c_sub = float(item["subtotal"])

                    # 1. Descontar Stock
                    cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (c_cant, c_id))
                    
                    # 2. Registrar en Movimientos
                    cur.execute("""
                        INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) 
                        VALUES ('venta', %s, %s, %s, %s)
                    """, (c_id, c_cant, c_pre, c_sub))
                
                # 3. Registrar en Ventas y obtener N° Ticket
                cur.execute("""
                    INSERT INTO ventas (cajero, total, items) 
                    VALUES (%s, %s, %s) RETURNING ticket_num
                """, (st.session_state.username, float(total_final), str(st.session_state.cart)))
                
                n_ticket_generado = cur.fetchone()[0]
                conn.commit()
                
                # 4. Generar el PDF y guardar en sesión
                st.session_state.last_ticket_bin = generar_ticket_pdf(st.session_state.cart, total_final, n_ticket_generado)
                st.session_state.cart = [] # Limpiar carrito tras éxito
                st.success(f"Venta registrada. Ticket N° {n_ticket_generado}")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error en la base de datos: {e}")
            finally:
                cur.close()
                conn.close()

# --- BOTÓN DE DESCARGA ---
if st.session_state.last_ticket_bin:
    st.divider()
    st.download_button(
        label="📥 Descargar e Imprimir Ticket",
        data=st.session_state.last_ticket_bin,
        file_name=f"ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    if st.button("Nueva Venta"):
        st.session_state.last_ticket_bin = None
        st.rerun()
