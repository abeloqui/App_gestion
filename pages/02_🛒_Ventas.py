import streamlit as st
from database import get_connection
import pandas as pd
from datetime import datetime

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("🛒 Registrar Venta")

if "cart" not in st.session_state: st.session_state.cart = []

conn = get_connection()
df = pd.read_sql_query("SELECT id, nombre, precio_venta, stock FROM productos WHERE stock > 0", conn)
conn.close()

with st.form("venta_form"):
    col1, col2 = st.columns(2)
    with col1:
        prod_sel = st.selectbox("Producto", df["nombre"].tolist() if not df.empty else [])
    with col2:
        cant = st.number_input("Cantidad", min_value=1, value=1)
    
    if st.form_submit_button("➕ Añadir al Carrito"):
        if not df.empty:
            row = df[df["nombre"] == prod_sel].iloc[0]
            if cant <= row['stock']:
                st.session_state.cart.append({
                    "id": int(row['id']), "nombre": row['nombre'], 
                    "cantidad": cant, "precio": row['precio_venta'], 
                    "subtotal": cant * row['precio_venta']
                })
                st.rerun()
            else:
                st.error("Stock insuficiente.")

if st.session_state.cart:
    total = sum(i["subtotal"] for i in st.session_state.cart)
    st.table(st.session_state.cart)
    st.subheader(f"💰 TOTAL: ${total:.2f}")
    
    if st.button("✅ Confirmar Venta"):
        conn = get_connection()
        cur = conn.cursor()
        try:
            for i in st.session_state.cart:
                cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (i["cantidad"], i["id"]))
                cur.execute("INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) VALUES ('venta', %s, %s, %s, %s)",
                          (i["id"], i["cantidad"], i["precio"], i["subtotal"]))
            
            cur.execute("INSERT INTO ventas (cajero, total, medio_pago, items) VALUES (%s, %s, %s, %s)",
                      (st.session_state.username, total, "Efectivo", str(st.session_state.cart)))
            conn.commit()
            st.session_state.cart = []
            st.success("✅ Venta registrada exitosamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al procesar la venta: {e}")
        finally:
            conn.close()
