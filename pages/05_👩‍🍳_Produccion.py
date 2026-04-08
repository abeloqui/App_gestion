import streamlit as st
import pandas as pd
from database import get_connection, get_engine

st.set_page_config(page_title="Registro de Producción", layout="centered")

# Validación de sesión
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("👩‍🍳 Registro de Producción")

# --- Obtener datos ---
engine = get_engine()

# Solo mostramos productos que se pueden fabricar (Preelaborado y Producto Final)
df_p = pd.read_sql("""
    SELECT id, nombre 
    FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final') 
    ORDER BY nombre
""", engine)

with st.form("form_p", clear_on_submit=True):
    if df_p.empty:
        st.warning("No hay productos configurados como Preelaborado o Producto Final aún.")
        producto = None
    else:
        producto = st.selectbox("¿Qué elaboraste hoy?", df_p['nombre'].tolist())
    
    cantidad = st.number_input("Cantidad producida (unidades/kg)", min_value=0.1, step=0.1)
    
    if st.form_submit_button("Registrar y Descontar Insumos", use_container_width=True):
        if not producto:
            st.error("No hay productos disponibles para producir.")
        else:
            id_prod = int(df_p[df_p['nombre'] == producto]['id'].values[0])
            
            conn = get_connection()
            cur = conn.cursor()
            try:
                # 1. Buscar la receta del producto
                cur.execute("SELECT insumo_id, cantidad FROM recetas WHERE plato_id = %s", (id_prod,))
                receta = cur.fetchall()
                
                if not receta:
                    st.warning(f"⚠️ El producto '{producto}' no tiene una receta definida todavía.")
                    # Aun así podemos registrar la producción (solo suma stock)
                    cur.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", 
                               (cantidad, id_prod))
                else:
                    # 2. Descontar Insumos según la receta
                    for ins_id, cant_u in receta:
                        cur.execute("""
                            UPDATE productos 
                            SET stock = stock - %s 
                            WHERE id = %s AND stock >= %s
                        """, (cant_u * cantidad, ins_id, cant_u * cantidad))
                    
                    # 3. Sumar el producto terminado
                    cur.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", 
                               (cantidad, id_prod))
                
                # 4. Registrar el movimiento de producción
                cur.execute("""
                    INSERT INTO movimientos (tipo, producto_id, cantidad, total) 
                    VALUES ('produccion', %s, %s, 0)
                """, (id_prod, cantidad))
                
                conn.commit()
                st.success(f"✅ ¡Listo! Se registraron {cantidad} de **{producto}**.")
                st.balloons()
                
            except Exception as e:
                conn.rollback()
                st.error(f"❌ Error al registrar producción: {e}")
            finally:
                cur.close()
                conn.close()

# Información adicional
st.info("💡 **Tip**: Primero debes crear las recetas en la página de Recetas para que se descuenten automáticamente los insumos.")
