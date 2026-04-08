import streamlit as st
from database import get_connection

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión.")
    st.stop()

st.header("➕ Agregar Nuevo Producto")
st.write("Completa los datos para dar de alta un producto en el sistema.")

with st.form("new_product_form", clear_on_submit=True):
    nombre = st.text_input("Nombre del Producto (Ej: Coca Cola 1.5L)")
    categoria = st.selectbox("Categoría", ["Bebidas", "Almacén", "Limpieza", "Fiambrería", "Otros"])
    
    col1, col2 = st.columns(2)
    with col1:
        precio_venta = st.number_input("Precio de Venta al Público", min_value=0.0, step=0.01)
        stock_inicial = st.number_input("Stock Inicial", min_value=0, step=1)
    with col2:
        precio_costo = st.number_input("Precio de Costo Inicial (CMP)", min_value=0.0, step=0.01)
        stock_minimo = st.number_input("Alerta Stock Mínimo", min_value=1, value=5)

    if st.form_submit_button("💾 Guardar Producto"):
        if nombre:
            conn = get_connection()
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO productos (nombre, categoria, precio_venta, precio_costo, stock, stock_minimo)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (nombre, categoria, precio_venta, precio_costo, stock_inicial, stock_minimo))
                conn.commit()
                st.success(f"✅ Producto '{nombre}' agregado correctamente.")
            except Exception as e:
                st.error(f"❌ Error: El producto ya existe o hay un problema con la base de datos.")
            finally:
                conn.close()
        else:
            st.warning("El nombre del producto es obligatorio.")
