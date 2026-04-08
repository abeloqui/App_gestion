import streamlit as st
import pandas as pd
from database import get_connection, get_engine

st.set_page_config(page_title="Gestión de Recetas", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📋 Gestión de Recetas")
st.markdown("Define los insumos necesarios para fabricar cada **Preelaborado** o **Producto Final**.")

engine = get_engine()

# Cargar productos
df_platos = pd.read_sql("""
    SELECT id, nombre, subcategoria 
    FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final')
    ORDER BY nombre
""", engine)

df_insumos = pd.read_sql("""
    SELECT id, nombre 
    FROM productos 
    WHERE subcategoria = 'Materia Prima'
    ORDER BY nombre
""", engine)

# Selección del producto
if df_platos.empty:
    st.error("No hay productos configurados como Preelaborado o Producto Final.")
    st.stop()

plato_seleccionado = st.selectbox("🔍 Selecciona el producto a fabricar", df_platos['nombre'].tolist())
plato_id = int(df_platos[df_platos['nombre'] == plato_seleccionado]['id'].values[0])
subcat = df_platos[df_platos['nombre'] == plato_seleccionado]['subcategoria'].values[0]

st.subheader(f"Receta para: **{plato_seleccionado}** ({subcat})")

# ====================== CARGA DE RECETA ACTUAL ======================
df_receta_actual = pd.read_sql("""
    SELECT 
        r.id as receta_id,
        i.nombre as insumo,
        r.cantidad,
        i.id as insumo_id
    FROM recetas r
    JOIN productos i ON r.insumo_id = i.id
    WHERE r.plato_id = %s
    ORDER BY i.nombre
""", engine, params=(plato_id,))

# ====================== PESTAÑAS ======================
tab_edit, tab_ver, tab_eliminar = st.tabs(["✏️ Editar Receta", "📋 Ver Receta Completa", "🗑️ Eliminar Receta"])

with tab_edit:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### Agregar o Modificar Insumo")
        with st.form("form_agregar_insumo", clear_on_submit=True):
            insumo_nombre = st.selectbox("Insumo (Materia Prima)", 
                                        df_insumos['nombre'].tolist() if not df_insumos.empty else ["Sin insumos disponibles"])
            cantidad = st.number_input("Cantidad por unidad producida", 
                                     min_value=0.001, 
                                     step=0.001, 
                                     format="%.3f",
                                     help="Ej: 0.250 = 250 gramos")
            
            if st.form_submit_button("💾 Guardar Insumo", use_container_width=True, type="primary"):
                if insumo_nombre and cantidad > 0:
                    insumo_id = int(df_insumos[df_insumos['nombre'] == insumo_nombre]['id'].values[0])
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO recetas (plato_id, insumo_id, cantidad)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (plato_id, insumo_id) 
                            DO UPDATE SET cantidad = EXCLUDED.cantidad
                        """, (plato_id, insumo_id, cantidad))
                        conn.commit()
                        st.success(f"✅ {insumo_nombre} guardado correctamente ({cantidad})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        cur.close()
                        conn.close()

    with col2:
        st.markdown("### Receta Actual")
        if df_receta_actual.empty:
            st.info("Aún no hay insumos en esta receta.")
        else:
            for _, row in df_receta_actual.iterrows():
                with st.container():
                    col_a, col_b, col_c = st.columns([4, 2, 1])
                    with col_a:
                        st.write(f"**{row['insumo']}**")
                    with col_b:
                        st.write(f"{row['cantidad']:.3f}")
                    with col_c:
                        if st.button("🗑️", key=f"del_{row['receta_id']}", help="Eliminar insumo"):
                            conn = get_connection()
                            cur = conn.cursor()
                            try:
                                cur.execute("DELETE FROM recetas WHERE id = %s", (row['receta_id'],))
                                conn.commit()
                                st.success(f"{row['insumo']} eliminado")
                                st.rerun()
                            finally:
                                cur.close()
                                conn.close()
                    st.divider()

with tab_ver:
    st.subheader("Vista Completa de la Receta")
    if not df_receta_actual.empty:
        df_mostrar = df_receta_actual[['insumo', 'cantidad']].copy()
        df_mostrar.columns = ['Insumo', 'Cantidad requerida']
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        st.caption(f"Total de insumos en la receta: **{len(df_receta_actual)}**")
    else:
        st.info("Esta receta aún no tiene insumos cargados.")

with tab_eliminar:
    st.subheader("Eliminar Receta Completa")
    st.warning("⚠️ Esta acción eliminará **todos** los insumos de esta receta.")
    if st.button("🗑️ Eliminar toda la receta", type="primary"):
        if st.checkbox("Confirmo que quiero borrar completamente esta receta"):
            conn = get_connection()
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM recetas WHERE plato_id = %s", (plato_id,))
                conn.commit()
                st.success(f"✅ Receta de **{plato_seleccionado}** eliminada completamente.")
                st.rerun()
            finally:
                cur.close()
                conn.close()

st.caption("💡 Usa cantidades consistentes (ej: todo en kg o todo en gramos).")
