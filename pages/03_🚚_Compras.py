import streamlit as st
import pandas as pd
from database import get_connection

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("🚚 Compras y Costo Medio Ponderado")

conn = get_connection()
df_p = pd.read_sql_query("SELECT id, nombre, stock, precio_costo FROM productos", conn)
conn.close()

with st.form("compra_form"):
    prod_compra = st.selectbox("Seleccionar Producto", df_p["nombre"].tolist())
    cant_compra = st.number_input("Cantidad Comprada", min_value=1)
    costo_factura = st.number_input("Costo Unitario Factura", min_value=0.1)
    
    if st.form_submit_button("Registrar Ingreso"):
        row = df_p[df_p["nombre"] == prod_compra].iloc[0]
        id_p, s_ant, c_ant = int(row['id']), int(row['stock']), float(row['precio_costo'])
        
        # Fórmula CMP
        n_stock = s_ant + cant_compra
        n_costo = ((s_ant * c_ant) + (cant_compra * costo_factura)) / n_stock
        
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE productos SET stock = %s, precio_costo = %s WHERE id = %s", (n_stock, n_costo, id_p))
            cur.execute("INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) VALUES ('compra', %s, %s, %s, %s)",
                      (id_p, cant_compra, costo_factura, cant_compra * costo_factura))
            conn.commit()
            st.success(f"Stock actualizado. Nuevo Costo Medio: ${n_costo:.2f}")
        finally:
            conn.close()
