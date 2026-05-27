import streamlit as st
import pandas as pd
from database import get_connection, get_engine
from datetime import datetime

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

if st.session_state.rol != 'admin':
    st.error("🔒 Acceso restringido. Solo administradores.")
    st.stop()

st.header("🔧 Ajuste de Stock")
st.caption("Usá esta pantalla para corregir el stock real luego de un conteo físico.")

engine = get_engine()

# --- FILTRO POR TIPO ---
subtipo = st.selectbox("Filtrar por tipo", ["Todos", "Materia Prima", "Preelaborado", "Producto Final"])

query = "SELECT id, nombre, subcategoria, unidad, stock, stock_minimo FROM productos"
if subtipo != "Todos":
    query += f" WHERE subcategoria = '{subtipo}'"
query += " ORDER BY subcategoria, nombre"

df = pd.read_sql(query, engine)

if df.empty:
    st.info("No hay productos cargados.")
    st.stop()

tab_individual, tab_masivo = st.tabs(["✏️ Ajuste Individual", "📋 Ajuste Masivo"])

with tab_individual:
    st.subheader("Corregir stock de un producto")
    producto_sel = st.selectbox("Seleccioná el producto", df['nombre'].tolist())
    row = df[df['nombre'] == producto_sel].iloc[0]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Stock actual en sistema", f"{row['stock']} {row['unidad']}")
    with col2:
        st.metric("Stock mínimo", f"{row['stock_minimo']} {row['unidad']}")

    nuevo_stock = st.number_input(
        f"Stock real contado ({row['unidad']})",
        min_value=0.0,
        value=float(row['stock']),
        step=0.5
    )
    motivo = st.text_input("Motivo del ajuste (opcional)", placeholder="Ej: Conteo físico 27/05")

    if st.button("💾 Guardar Ajuste", type="primary", use_container_width=True):
        diferencia = nuevo_stock - float(row['stock'])
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, int(row['id'])))
            cur.execute("""
                INSERT INTO movimientos (tipo, producto_id, cantidad, detalle, fecha)
                VALUES ('ajuste', %s, %s, %s, NOW())
            """, (
                int(row['id']),
                diferencia,
                motivo or f"Ajuste manual por {st.session_state.username}"
            ))
            conn.commit()
            signo = "+" if diferencia >= 0 else ""
            st.success(f"✅ Stock de '{producto_sel}' actualizado a {nuevo_stock} {row['unidad']} ({signo}{diferencia:.1f})")
        except Exception as e:
            conn.rollback()
            st.error(f"Error: {e}")
        finally:
            conn.close()

with tab_masivo:
    st.subheader("Corregir múltiples productos a la vez")
    st.caption("Editá la columna 'stock_real' con los valores del conteo físico y guardá.")

    df_edit = df[['nombre', 'subcategoria', 'unidad', 'stock']].copy()
    df_edit = df_edit.rename(columns={'stock': 'stock_sistema'})
    df_edit['stock_real'] = df_edit['stock_sistema']

    edited = st.data_editor(
        df_edit,
        column_config={
            "nombre": st.column_config.TextColumn("Producto", disabled=True),
            "subcategoria": st.column_config.TextColumn("Tipo", disabled=True),
            "unidad": st.column_config.TextColumn("Unidad", disabled=True),
            "stock_sistema": st.column_config.NumberColumn("Stock Sistema", disabled=True),
            "stock_real": st.column_config.NumberColumn("Stock Real ✏️", min_value=0.0, step=0.5),
        },
        use_container_width=True,
        hide_index=True
    )

    cambios = edited[edited['stock_real'] != edited['stock_sistema']]

    if not cambios.empty:
        st.warning(f"⚠️ Hay {len(cambios)} producto(s) con cambios pendientes de guardar.")
        st.dataframe(cambios[['nombre', 'stock_sistema', 'stock_real', 'unidad']], 
                     use_container_width=True, hide_index=True)

        if st.button("💾 Guardar Todos los Cambios", type="primary", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            try:
                for _, row_c in cambios.iterrows():
                    prod_row = df[df['nombre'] == row_c['nombre']].iloc[0]
                    diferencia = row_c['stock_real'] - row_c['stock_sistema']
                    cur.execute("UPDATE productos SET stock = %s WHERE nombre = %s",
                                (row_c['stock_real'], row_c['nombre']))
                    cur.execute("""
                        INSERT INTO movimientos (tipo, producto_id, cantidad, detalle, fecha)
                        VALUES ('ajuste', %s, %s, %s, NOW())
                    """, (int(prod_row['id']), diferencia, f"Ajuste masivo por {st.session_state.username}"))
                conn.commit()
                st.success(f"✅ {len(cambios)} productos actualizados correctamente.")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"Error: {e}")
            finally:
                conn.close()
    else:
        st.info("No hay cambios pendientes.")
