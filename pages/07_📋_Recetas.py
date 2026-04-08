import streamlit as st
import pandas as pd
from database import get_connection, get_engine

st.set_page_config(page_title="Gestión de Recetas", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📋 Gestión de Recetas")
st.write("Define qué insumos (Materia Prima) se necesitan para fabricar cada Preelaborado o Producto Final.")

engine = get_engine()

# Cargar productos separados
df_platos = pd.read_sql("""
    SELECT id, nombre, subcategoria 
    FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final')
    ORDER BY nombre
""", engine)

df_insumos = pd.read_sql("""
    SELECT id, nombre, subcategoria 
    FROM productos 
    WHERE subcategoria = 'Materia Prima'
    ORDER BY nombre
""", engine)

# Pestañas para separar visualmente
tab1, tab2, tab3 = st.tabs(["➕ Agregar / Editar Receta", "📋 Ver Todas las Recetas", "🗑️ Eliminar Receta"])

with tab1:
    st.subheader("Crear o Actualizar Receta")
    
    if df_platos.empty:
        st.warning("Primero debes tener productos como 'Preelaborado' o 'Producto Final'.")
    else:
        plato = st.selectbox("Producto a fabricar (Plato)", df_platos['nombre'].tolist())
        plato_id = int(df_platos[df_platos['nombre'] == plato]['id'].values[0])
        
        st.info(f"**{plato}** → Receta actual:")
        
        # Mostrar receta existente
        df_actual = pd.read_sql("""
            SELECT p.nombre as insumo, r.cantidad 
            FROM recetas r
            JOIN productos p ON r.insumo_id = p.id
            WHERE r.plato_id = %s
        """, engine, params=(plato_id,))
        
        if not df_actual.empty:
            st.dataframe(df_actual, use_container_width=True, hide_index=True)
        else:
            st.caption("Aún no tiene receta definida.")
        
        st.divider()
        
        with st.form("form_receta", clear_on_submit=True):
            insumo = st.selectbox("Insumo (Materia Prima)", df_insumos['nombre'].tolist() if not df_insumos.empty else ["Sin insumos"])
            cantidad = st.number_input("Cantidad necesaria por unidad de plato (gramos / kg / unidades)", min_value=0.01, step=0.01, format="%.3f")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.form_submit_button("➕ Agregar Insumo a la Receta", use_container_width=True):
                    if insumo and cantidad > 0:
                        insumo_id = int(df_insumos[df_insumos['nombre'] == insumo]['id'].values[0])
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
                            st.success(f"✅ {insumo} agregado a la receta de {plato}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                        finally:
                            cur.close()
                            conn.close()
            
            with col_b:
                if st.form_submit_button("🧹 Limpiar Receta Completa", use_container_width=True, type="secondary"):
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("DELETE FROM recetas WHERE plato_id = %s", (plato_id,))
                        conn.commit()
                        st.success(f"Receta de {plato} borrada completamente.")
                        st.rerun()
                    finally:
                        cur.close()
                        conn.close()

with tab2:
    st.subheader("Todas las Recetas del Sistema")
    
    df_recetas = pd.read_sql("""
        SELECT 
            p.nombre as "Producto Final / Preelaborado",
            p.subcategoria as "Tipo",
            i.nombre as "Insumo",
            r.cantidad as "Cantidad por unidad"
        FROM recetas r
        JOIN productos p ON r.plato_id = p.id
        JOIN productos i ON r.insumo_id = i.id
        ORDER BY p.nombre, i.nombre
    """, engine)
    
    if df_recetas.empty:
        st.info("Aún no hay recetas cargadas. Ve a la pestaña 'Agregar' para crearlas.")
    else:
        for producto in df_recetas["Producto Final / Preelaborado"].unique():
            st.write(f"**{producto}**")
            df_prod = df_recetas[df_recetas["Producto Final / Preelaborado"] == producto]
            st.dataframe(df_prod[["Insumo", "Cantidad por unidad"]], use_container_width=True, hide_index=True)
            st.divider()

with tab3:
    st.subheader("Eliminar Receta")
    if not df_platos.empty:
        plato_elim = st.selectbox("Seleccionar receta a eliminar", df_platos['nombre'].tolist(), key="elim")
        if st.button("🗑️ Eliminar toda la receta", type="primary"):
            plato_id_elim = int(df_platos[df_platos['nombre'] == plato_elim]['id'].values[0])
            conn = get_connection()
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM recetas WHERE plato_id = %s", (plato_id_elim,))
                conn.commit()
                st.success(f"Receta de **{plato_elim}** eliminada.")
                st.rerun()
            finally:
                cur.close()
                conn.close()
    else:
        st.info("No hay productos para eliminar recetas.")

st.caption("💡 Consejo: Usa cantidades en **kg** o **gramos** de forma consistente (ej: 0.250 para 250g).")
