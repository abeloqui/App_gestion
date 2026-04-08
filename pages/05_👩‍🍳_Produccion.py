import streamlit as st
import pandas as pd
from database import get_connection, get_engine

st.set_page_config(page_title="Registro de Producción", layout="centered")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("👩‍🍳 Registro de Producción")
st.write("Al registrar, se sumará el stock al producto y se descontará automáticamente de la materia prima según la receta.")

engine = get_engine()

# Obtener productos que se pueden producir
df_p = pd.read_sql("""
    SELECT id, nombre 
    FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final') 
    ORDER BY nombre
""", engine)

with st.form("form_produccion", clear_on_submit=True):
    if df_p.empty:
        st.warning("No hay productos configurados para producir.")
        producto = None
    else:
        producto = st.selectbox("¿Qué elaboraste hoy?", df_p['nombre'].tolist())
    
    cantidad_producida = st.number_input("Cantidad producida (unidades/kg)", min_value=0.1, step=0.1)
    
    if st.form_submit_button("🚀 Registrar Producción y Descontar Stock", use_container_width=True):
        if not producto:
            st.error("Selecciona un producto válido.")
        else:
            id_prod_final = int(df_p[df_p['nombre'] == producto]['id'].values[0])
            
            conn = get_connection()
            cur = conn.cursor()
            try:
                # 1. Buscar la receta del producto
                cur.execute("""
                    SELECT insumo_id, cantidad 
                    FROM recetas 
                    WHERE plato_id = %s
                """, (id_prod_final,))
                receta = cur.fetchall()

                if not receta:
                    st.error(f"❌ El producto '{producto}' no tiene una receta configurada. Ve a 'Recetas' primero.")
                else:
                    # 2. Descontar cada insumo de la tabla productos
                    for insumo_id, cant_unitaria in receta:
                        descuento_total = cant_unitaria * cantidad_producida
                        cur.execute("""
                            UPDATE productos 
                            SET stock = stock - %s 
                            WHERE id = %s
                        """, (descuento_total, insumo_id))
                    
                    # 3. Sumar el stock al producto terminado
                    cur.execute("""
                        UPDATE productos 
                        SET stock = stock + %s 
                        WHERE id = %s
                    """, (cantidad_producida, id_prod_final))
                    
                    # 4. Registrar movimiento en el historial
                    cur.execute("""
                        INSERT INTO movimientos (tipo, producto_id, cantidad, fecha) 
                        VALUES ('produccion', %s, %s, NOW())
                    """, (id_prod_final, cantidad_producida))
                    
                    conn.commit()
                    st.success(f"✅ ¡Producción registrada! Se descontaron los insumos de {producto}.")
                    st.balloons()
            
            except Exception as e:
                conn.rollback()
                st.error(f"❌ Error en la base de datos: {e}")
            finally:
                cur.close()
                conn.close()

st.info("💡 **Recordatorio**: Si un ingrediente no se descuenta, asegúrate de que esté agregado en la receta del producto correspondiente.")
