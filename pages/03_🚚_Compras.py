import streamlit as st
from database import get_connection
import pandas as pd

st.header("🚚 Registro de Compras (Proveedores)")

conn = get_connection()
df_prod = pd.read_sql_query("SELECT id, nombre, stock, precio_costo FROM productos", conn)

with st.form("compra_proveedor"):
    prod_sel = st.selectbox("Seleccionar Producto", df_prod["nombre"].tolist())
    cant_compra = st.number_input("Cantidad Comprada", min_value=1)
    costo_factura = st.number_input("Precio de Costo Unitario (Factura)", min_value=0.1)
    
    if st.form_submit_button("Registrar Ingreso"):
        row = df_prod[df_prod["nombre"] == prod_sel].iloc[0]
        id_p = int(row['id'])
        stock_ant = int(row['stock'])
        costo_ant = float(row['precio_costo'])
        
        # Lógica Costo Medio Ponderado
        nuevo_stock = stock_ant + cant_compra
        nuevo_costo_medio = ((stock_ant * costo_ant) + (cant_compra * costo_factura)) / nuevo_stock
        
        cur = conn.cursor()
        # Actualizar Producto
        cur.execute("""UPDATE productos SET stock = ?, precio_costo = ? WHERE id = ?""", 
                    (nuevo_stock, nuevo_costo_medio, id_p))
        # Registrar Movimiento
        cur.execute("""INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) 
                    VALUES ('compra', ?, ?, ?, ?)""", 
                    (id_p, cant_compra, costo_factura, cant_compra * costo_factura))
        
        conn.commit()
        st.success(f"Stock actualizado. Nuevo costo medio: ${nuevo_costo_medio:.2f}")

conn.close()