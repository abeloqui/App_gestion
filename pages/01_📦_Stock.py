import streamlit as st
import pandas as pd
from database import get_connection

st.header("📋 Inventario Real-Time")

conn = get_connection()
df = pd.read_sql_query("""
    SELECT nombre, categoria, precio_costo as "Costo CMP", 
           precio_venta as "P. Venta", stock,
           (precio_venta - precio_costo) as "Margen Unit."
    FROM productos
""", conn)
conn.close()

st.dataframe(df.style.highlight_between(left=0, right=5, subset=['stock'], color='#ffcccc'), 
             use_container_width=True)

# Widget para agregar productos nuevos rápido
with st.expander("➕ Agregar Nuevo Producto"):
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
