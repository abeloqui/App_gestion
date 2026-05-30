import streamlit as st
import pandas as pd
from database import get_connection

# --- RESTAURAR SESIÓN ---
if "logged_in" not in st.session_state:
    params = st.query_params
    st.session_state.logged_in = params.get("logged_in", "false") == "true"
    st.session_state.username = params.get("username", None)
    st.session_state.rol = params.get("rol", None)

if not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()





st.header("🚚 Compras e Ingreso de Materia Prima")

conn = get_connection()
df_p = pd.read_sql_query("""
    SELECT id, nombre, stock, precio_costo, unidad 
    FROM productos 
    ORDER BY subcategoria, nombre
""", conn)
conn.close()

with st.form("compra_form"):
    prod_compra = st.selectbox("Seleccionar Producto", df_p["nombre"].tolist())
    row = df_p[df_p["nombre"] == prod_compra].iloc[0]
    
    st.caption(f"Stock actual: {row['stock']} {row['unidad']} | Costo medio actual: ${row['precio_costo']:.2f}")

    cant_compra = st.number_input("Cantidad Comprada", min_value=0.1, step=0.1)
    costo_factura = st.number_input("Costo Unitario según Factura ($)", min_value=0.01, step=0.01)

    if st.form_submit_button("📥 Registrar Ingreso"):
        id_p = int(row['id'])
        s_ant = float(row['stock'])
        c_ant = float(row['precio_costo'])

        n_stock = s_ant + cant_compra

        # Costo Medio Ponderado
        if n_stock > 0:
            n_costo = ((s_ant * c_ant) + (cant_compra * costo_factura)) / n_stock
        else:
            n_costo = costo_factura

        total_compra = cant_compra * costo_factura

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE productos SET stock = %s, precio_costo = %s WHERE id = %s
            """, (n_stock, n_costo, id_p))

            cur.execute("""
                INSERT INTO movimientos (tipo, producto_id, cantidad, costo_unitario, total, detalle, fecha)
                VALUES ('compra', %s, %s, %s, %s, %s, NOW())
            """, (id_p, cant_compra, costo_factura, total_compra, f"Ingreso de compra: {prod_compra}"))

            conn.commit()
            st.success(f"✅ Ingreso registrado. Nuevo stock: {n_stock:.2f} {row['unidad']} | Nuevo costo medio: ${n_costo:.2f}")
        except Exception as e:
            conn.rollback()
            st.error(f"Error al registrar la compra: {e}")
        finally:
            conn.close()

st.divider()
st.subheader("📋 Stock Actual")
conn = get_connection()
df_actual = pd.read_sql_query("""
    SELECT nombre, subcategoria, unidad, stock, stock_minimo, precio_costo
    FROM productos ORDER BY subcategoria, nombre
""", conn)
conn.close()
st.dataframe(df_actual, use_container_width=True, hide_index=True)
