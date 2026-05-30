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





st.header("➕ Gestión de Productos")

tab_agregar, tab_editar = st.tabs(["➕ Agregar Producto", "✏️ Ver / Editar"])

with tab_agregar:
    with st.form("new_product_form", clear_on_submit=True):
        nombre = st.text_input("Nombre del Producto")
        categoria = st.selectbox("Categoría", [
            "Materia Prima", "Repostería", "Lácteos", "Frutos Secos",
            "Packaging", "Bebidas", "Almacén", "Limpieza", "Otros"
        ])
        subcategoria = st.selectbox("Tipo de Stock", [
            "Materia Prima", "Preelaborado", "Producto Final"
        ], help="Define cómo se clasifica en el stock")

        unidad = st.selectbox("Unidad de Medida", [
            "kg", "gr", "lt", "ml", "unidad", "docena", "paquete"
        ])

        col1, col2 = st.columns(2)
        with col1:
            precio_venta = st.number_input("Precio de Venta ($)", min_value=0.0, step=0.01)
            stock_inicial = st.number_input("Stock Inicial", min_value=0.0, step=0.1)
        with col2:
            precio_costo = st.number_input("Precio de Costo Inicial ($)", min_value=0.0, step=0.01)
            stock_minimo = st.number_input("Stock Mínimo (alerta)", min_value=0.1, value=5.0, step=0.1)

        if st.form_submit_button("💾 Guardar Producto"):
            if not nombre.strip():
                st.warning("El nombre del producto es obligatorio.")
            else:
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("""
                        INSERT INTO productos 
                        (nombre, categoria, subcategoria, unidad, precio_venta, precio_costo, stock, stock_minimo, es_producido)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        nombre.strip(), categoria, subcategoria, unidad,
                        precio_venta, precio_costo, stock_inicial, stock_minimo,
                        subcategoria != "Materia Prima"
                    ))
                    conn.commit()
                    st.success(f"✅ '{nombre}' agregado como {subcategoria}.")
                except Exception as e:
                    conn.rollback()
                    if "unique" in str(e).lower():
                        st.error(f"❌ Ya existe un producto con el nombre '{nombre}'.")
                    else:
                        st.error(f"❌ Error: {e}")
                finally:
                    conn.close()

with tab_editar:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT nombre, categoria, subcategoria, unidad, precio_venta, precio_costo, stock, stock_minimo
        FROM productos ORDER BY subcategoria, nombre
    """, conn)
    conn.close()

    if df.empty:
        st.info("No hay productos cargados aún.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("✏️ Editar Precio de Venta")
        conn = get_connection()
        df_sel = pd.read_sql_query("SELECT id, nombre, precio_venta FROM productos ORDER BY nombre", conn)
        conn.close()

        prod_edit = st.selectbox("Seleccioná un producto", df_sel['nombre'].tolist())
        nuevo_precio = st.number_input("Nuevo Precio de Venta ($)", min_value=0.0, step=0.01)

        if st.button("💾 Actualizar Precio"):
            id_prod = int(df_sel[df_sel['nombre'] == prod_edit]['id'].values[0])
            conn = get_connection()
            cur = conn.cursor()
            try:
                cur.execute("UPDATE productos SET precio_venta = %s WHERE id = %s", (nuevo_precio, id_prod))
                conn.commit()
                st.success(f"✅ Precio de '{prod_edit}' actualizado a ${nuevo_precio:.2f}")
            except Exception as e:
                conn.rollback()
                st.error(f"Error: {e}")
            finally:
                conn.close()
