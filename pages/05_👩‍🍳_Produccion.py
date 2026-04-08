import streamlit as st
import pandas as pd
from database import get_connection, get_engine

st.set_page_config(page_title="Registro de Producción", layout="centered")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión.")
    st.stop()

st.header("👩‍🍳 Registro de Producción")
engine = get_engine()

df_p = pd.read_sql("SELECT id, nombre FROM productos WHERE subcategoria IN ('Preelaborado', 'Producto Final') ORDER BY nombre", engine)

with st.form("form_produccion"):
    producto = st.selectbox("¿Qué elaboraste hoy?", df_p['nombre'].tolist()) if not df_p.empty else None
    cantidad_prod = st.number_input("Cantidad producida", min_value=0.1, step=0.1)
    
    if st.form_submit_button("🚀 Registrar y Descontar Stock", use_container_width=True):
        if not producto:
            st.error("No hay productos disponibles.")
        else:
            id_final = int(df_p[df_p['nombre'] == producto]['id'].values[0])
            conn = get_connection()
            cur = conn.cursor()
            try:
                # 1. Obtener Receta
                cur.execute("SELECT insumo_id, cantidad FROM recetas WHERE plato_id = %s", (id_final,))
                receta = cur.fetchall()

                if not receta:
                    st.error("Este producto no tiene receta configurada.")
                else:
                    # 2. Descontar Insumos
                    for ins_id, cant_u in receta:
                        cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", 
                                   (cant_u * cantidad_prod, ins_id))
                    
                    # 3. Sumar Stock Producto Final
                    cur.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", 
                               (cantidad_prod, id_final))
                    
                    # 4. Historial
                    cur.execute("INSERT INTO movimientos (tipo, producto_id, cantidad, fecha) VALUES ('produccion', %s, %s, NOW())", 
                               (id_final, cantidad_prod))
                    
                    conn.commit()
                    st.success(f"✅ Producción registrada y stock actualizado.")
                    st.balloons()
            except Exception as e:
                conn.rollback()
                st.error(f"Error: {e}")
            finally:
                conn.close()
