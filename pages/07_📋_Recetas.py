import streamlit as st
import pandas as pd
from database import get_connection, get_engine

st.set_page_config(page_title="Gestión de Recetas", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📋 Configuración de Recetas")
engine = get_engine()

# 1. Selección de Producto Elaborado
df_platos = pd.read_sql("""
    SELECT id, nombre FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final')
    ORDER BY nombre
""", engine)

if df_platos.empty:
    st.error("No hay productos tipo 'Preelaborado' o 'Producto Final'.")
    st.stop()

plato_nombre = st.selectbox("🔍 Selecciona el producto para editar su receta", df_platos['nombre'].tolist())
plato_id = int(df_platos[df_platos['nombre'] == plato_nombre]['id'].values[0])

# 2. Mostrar Receta Actual
st.subheader(f"Ingredientes de: {plato_nombre}")
query_receta = """
    SELECT p.nombre as insumo, r.cantidad, r.unidad 
    FROM recetas r
    JOIN productos p ON r.insumo_id = p.id
    WHERE r.plato_id = %s
"""
df_receta = pd.read_sql(query_receta, engine, params=(plato_id,))

if not df_receta.empty:
    st.table(df_receta)
    if st.button("🗑️ Borrar toda la receta"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM recetas WHERE plato_id = %s", (plato_id,))
        conn.commit()
        conn.close()
        st.rerun()
else:
    st.info("Sin ingredientes asignados.")

st.divider()

# 3. Formulario para añadir ingredientes (Solo Materia Prima)
st.subheader("➕ Añadir Insumo")
df_insumos = pd.read_sql("SELECT id, nombre FROM productos WHERE subcategoria = 'Materia Prima' ORDER BY nombre", engine)

with st.form("form_nuevo_insumo", clear_on_submit=True):
    insumo_nombre = st.selectbox("Selecciona Materia Prima", df_insumos['nombre'].tolist())
    cantidad = st.number_input("Cantidad necesaria (para 1 unidad final)", min_value=0.001, format="%.3f")
    unidad = st.selectbox("Unidad", ["kg", "g", "unidades", "litros", "ml"])
    
    if st.form_submit_button("Guardar Ingrediente"):
        insumo_id = int(df_insumos[df_insumos['nombre'] == insumo_nombre]['id'].values[0])
        conn = get_connection()
        cur = conn.cursor()
        try:
            # Importante: Requiere el CONSTRAINT UNIQUE en la DB
            cur.execute("""
                INSERT INTO recetas (plato_id, insumo_id, cantidad, unidad)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (plato_id, insumo_id) 
                DO UPDATE SET cantidad = EXCLUDED.cantidad, unidad = EXCLUDED.unidad
            """, (plato_id, insumo_id, cantidad, unidad))
            conn.commit()
            st.success(f"✅ Guardado: {insumo_nombre}")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
        finally:
            conn.close()
