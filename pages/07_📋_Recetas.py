import streamlit as st
import pandas as pd
from database import get_connection, get_engine

st.set_page_config(page_title="Gestión de Recetas", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📋 Configuración de Recetas")
st.markdown("Define qué ingredientes (materia prima) componen cada producto elaborado.")

engine = get_engine()

# 1. Seleccionar el Producto a configurar (Solo Preelaborados o Finales)
df_platos = pd.read_sql("""
    SELECT id, nombre FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final')
    ORDER BY nombre
""", engine)

if df_platos.empty:
    st.error("Primero debes agregar productos tipo 'Preelaborado' o 'Producto Final' en la sección Agregar Producto.")
    st.stop()

plato_nombre = st.selectbox("🔍 Selecciona el producto para editar su receta", df_platos['nombre'].tolist())
plato_id = int(df_platos[df_platos['nombre'] == plato_nombre]['id'].values[0])

# 2. Mostrar Receta Actual
st.subheader(f"Ingredientes de: {plato_nombre}")
query_receta = """
    SELECT r.id, p.nombre as insumo, r.cantidad, r.unidad 
    FROM recetas r
    JOIN productos p ON r.insumo_id = p.id
    WHERE r.plato_id = %s
"""
df_receta = pd.read_sql(query_receta, engine, params=(plato_id,))

if df_receta.empty:
    st.info("Este producto aún no tiene ingredientes asignados.")
else:
    st.table(df_receta[['insumo', 'cantidad', 'unidad']])
    if st.button("🗑️ Limpiar Receta (Borrar todos los ingredientes)"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM recetas WHERE plato_id = %s", (plato_id,))
        conn.commit()
        conn.close()
        st.rerun()

st.divider()

# 3. Formulario para añadir ingredientes
st.subheader("➕ Añadir Insumo a la Receta")
# Solo permitimos elegir "Materia Prima" como ingrediente
df_insumos = pd.read_sql("SELECT id, nombre FROM productos WHERE subcategoria = 'Materia Prima' ORDER BY nombre", engine)

with st.form("form_nuevo_insumo"):
    insumo_nombre = st.selectbox("Selecciona la Materia Prima", df_insumos['nombre'].tolist())
    cantidad_neta = st.number_input("Cantidad (necesaria para 1 unidad/kg del producto final)", min_value=0.001, format="%.3f")
    unidad_medida = st.selectbox("Unidad de medida", ["kg", "g", "unidades", "litros", "ml"])
    
    if st.form_submit_button("Guardar Ingrediente"):
        insumo_id = int(df_insumos[df_insumos['nombre'] == insumo_nombre]['id'].values[0])
        conn = get_connection()
        cur = conn.cursor()
        try:
            # Insertar o actualizar si ya existe ese insumo en la receta
            cur.execute("""
                INSERT INTO recetas (plato_id, insumo_id, cantidad, unidad)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (plato_id, insumo_id) 
                DO UPDATE SET cantidad = EXCLUDED.cantidad, unidad = EXCLUDED.unidad
            """, (plato_id, insumo_id, cantidad_neta, unidad_medida))
            conn.commit()
            st.success(f"✅ {insumo_nombre} añadido a la receta.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
        finally:
            conn.close()
