import streamlit as st
from database import get_connection, get_engine
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.stop()

st.header("🛒 Ventas")

if "cart" not in st.session_state: st.session_state.cart = []
if "ticket" not in st.session_state: st.session_state.ticket = None

engine = get_engine()
df_p = pd.read_sql("SELECT id, nombre, precio_venta, stock FROM productos WHERE stock > 0", engine)

with st.form("add_cart"):
    col1, col2 = st.columns([3,1])
    p_sel = col1.selectbox("Producto", df_p['nombre'].tolist() if not df_p.empty else ["Sin Stock"])
    cant = col2.number_input("Cant", min_value=1, value=1)
    if st.form_submit_button("➕ Añadir"):
        row = df_p[df_p['nombre'] == p_sel].iloc[0]
        st.session_state.cart.append({
            "id": int(row['id']), "nombre": str(p_sel), 
            "cantidad": int(cant), "precio": float(row['precio_venta']), 
            "subtotal": float(cant * row['precio_venta'])
        })
        st.rerun()

if st.session_state.cart:
    st.table(pd.DataFrame(st.session_state.cart))
    total = sum(i['subtotal'] for i in st.session_state.cart)
    metodo = st.selectbox("Medio de Pago", ["Efectivo", "Tarjeta", "Transferencia", "QR"])
    
    if st.button("✅ Confirmar Venta"):
        conn = get_connection()
        cur = conn.cursor()
        try:
            for i in st.session_state.cart:
                # Descontar Producto Principal
                cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (i['cantidad'], i['id']))
                # Descontar Insumos (Recetas)
                cur.execute("SELECT insumo_id, cantidad FROM recetas WHERE plato_id = %s", (i['id'],))
                for ins_id, cant_receta in cur.fetchall():
                    cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (float(cant_receta * i['cantidad']), ins_id))
                
                cur.execute("INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) VALUES ('venta',%s,%s,%s,%s)",
                          (i['id'], i['cantidad'], i['precio'], i['subtotal']))
            
            cur.execute("INSERT INTO ventas (cajero, total, medio_pago, items) VALUES (%s,%s,%s,%s) RETURNING ticket_num",
                      (st.session_state.username, total, metodo, str(st.session_state.cart)))
            conn.commit()
            st.success("Venta Exitosa")
            st.session_state.cart = []
            st.rerun()
        finally:
            conn.close()
