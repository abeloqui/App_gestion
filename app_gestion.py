import streamlit as st
from database import init_db, get_engine, get_connection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dulce Jazmín APP", layout="wide", page_icon="🎂")

# --- RESTAURAR SESIÓN DESDE QUERY PARAMS ---
if "logged_in" not in st.session_state:
    params = st.query_params
    st.session_state.logged_in = params.get("logged_in", "false") == "true"
    st.session_state.username = params.get("username", None)
    st.session_state.rol = params.get("rol", None)

try:
    init_db()
except Exception as e:
    st.error(f"Error de base de datos: {e}")
    st.stop()

if not st.session_state.logged_in:
    st.title("🎂 Dulce Jazmín APP")
    with st.form("login_form"):
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT username, rol FROM usuarios WHERE username=%s AND password=%s AND activo=TRUE",
                (user, pw)
            )
            result = cur.fetchone()
            conn.close()
            if result:
                st.session_state.logged_in = True
                st.session_state.username = result[0]
                st.session_state.rol = result[1]
                # Guardar en query params para persistir entre páginas
                st.query_params["logged_in"] = "true"
                st.query_params["username"] = result[0]
                st.query_params["rol"] = result[1]
                st.rerun()
            else:
                st.error("Credenciales incorrectas o usuario inactivo.")
else:
    rol = st.session_state.rol
    col_titulo, col_logout = st.columns([4, 1])
    with col_titulo:
        st.title(f"📊 Panel de Control — {st.session_state.username}")
        st.caption(f"Rol: {'🔑 Administrador' if rol == 'admin' else '👤 Operador'}")
    with col_logout:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.rol = None
            st.session_state.username = None
            st.query_params.clear()
            st.rerun()

    engine = get_engine()

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT MAX(fecha) FROM cierres")
        ultimo_cierre = cur.fetchone()[0]
        conn.close()
        desde = f"'{ultimo_cierre}'" if ultimo_cierre else "'2000-01-01'"
    except:
        desde = "'2000-01-01'"

    c1, c2, c3, c4 = st.columns(4)
    try:
        df_v = pd.read_sql(f"SELECT total, medio_pago FROM ventas WHERE fecha > {desde}", engine)
        c1.metric("💰 Ventas del Período", f"${df_v['total'].sum():,.2f}")
        c2.metric("🧾 Tickets", len(df_v))

        df_crit = pd.read_sql(
            "SELECT nombre, stock, stock_minimo FROM productos WHERE stock <= stock_minimo", engine)
        c3.metric("⚠️ Alertas Stock", len(df_crit), delta=len(df_crit), delta_color="inverse")

        df_prod = pd.read_sql(
            f"SELECT COALESCE(SUM(cantidad), 0) as total FROM movimientos WHERE tipo='produccion' AND fecha > {desde}",
            engine)
        c4.metric("👩‍🍳 Producido", f"{df_prod['total'].iloc[0]:.1f}")

        st.divider()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("💳 Ventas por Medio de Pago")
            if not df_v.empty:
                fig = px.pie(df_v, values='total', names='medio_pago', hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin ventas en el período actual.")

        with col_g2:
            st.subheader("🔥 Top 5 Más Vendidos")
            df_top = pd.read_sql(f"""
                SELECT p.nombre, SUM(dv.cantidad) as total
                FROM detalle_ventas dv
                JOIN productos p ON dv.producto_id = p.id
                JOIN ventas v ON dv.venta_id = v.id
                WHERE v.fecha > {desde}
                GROUP BY p.nombre ORDER BY total DESC LIMIT 5
            """, engine)
            if not df_top.empty:
                fig2 = px.bar(df_top, x='total', y='nombre', orientation='h',
                              color='total', color_continuous_scale='Viridis')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sin datos de ventas aún.")

        if rol == 'admin' and not df_crit.empty:
            st.divider()
            st.subheader("⚠️ Reponer Urgente")
            st.dataframe(df_crit, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error al cargar el dashboard: {e}")
                
