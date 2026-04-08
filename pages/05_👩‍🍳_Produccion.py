import streamlit as st
import pandas as pd
from database import get_connection, get_engine

st.set_page_config(page_title="Registro de Producción", layout="centered")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión.")
    st.stop()

st.header("👩‍🍳 Registro de Producción")
engine = get_engine()

# Obtenemos productos (puedes filtrar por los que tengan receta)
df_p = pd.read_sql("SELECT id, nombre FROM productos ORDER BY nombre", engine)

with st.form("form_p", clear_on_submit=True):
    producto = st.selectbox("¿Qué elaboraste hoy?", df_p['nombre'])
    cantidad = st.number_input("Cantidad producida (unidades/kg)", min_value=0.1, step=0.1)
    
    if st.form_submit_button("Registrar y Descontar Insumos", use_container_width=True):
        id_prod = int(df_p[df_p['nombre'] == producto]['id'].values[0])
        conn = get_connection()
        cur = conn.cursor()
        try:
            # 1. Buscar receta
            cur.execute("SELECT insumo_id, cantidad FROM recetas WHERE plato_id = %s", (id_prod,))
            receta = cur.fetchall()
            
            if not receta:
                st.error(f"El producto '{producto}' no tiene una receta definida.")
            else:
                # 2. Descontar Insumos
                for ins_id, cant_u in receta:
                    cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cant_u * cantidad, ins_id))
                
                # 3. Sumar Producto Terminado
                cur.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", (cantidad, id_prod))
                
                # 4. Movimiento
                cur.execute("INSERT INTO movimientos (tipo, producto_id, cantidad, total) VALUES ('produccion', %s, %s, 0)", 
                           (id_prod, cantidad))
                
                conn.commit()
                st.success(f"¡Listo! Se fabricaron {cantidad} de {producto}.")
        except Exception as e:
            conn.rollback()
            st.error(f"Error: {e}")
        finally:
            cur.close()
            conn.close()
          
