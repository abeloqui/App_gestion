import streamlit as st
from database import init_db, get_engine
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dulce Jazmín - Gestión", layout="wide", page_icon="🎂")

# Inicializar Base de Datos
try:
    init_db()
except Exception as e:
    st.error(f"Error de base de datos: {e}")

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso al Sistema - Dulce Jazmín")
    with st.form("login_form"):
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar", use_container_width=True):
            if user == "admin" and pw == "1234":
                st.session_state.logged_in = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
else:
    st.title(f"📊 Panel de Control - {st.session_state.username}")

    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

    engine = get_engine()
    hoy = pd.Timestamp.now().date()

    # --- MÉTRICAS ---
    c1, c2, c3, c4 = st.columns(4)
    try:
        df_v = pd.read_sql(f"SELECT total, medio_pago FROM ventas WHERE fecha::date = '{hoy}'", engine)
        c1.metric("💰 Ventas Hoy", f"${df_v['total'].sum():,.2f}")
        c2.metric("🧾 Tickets Emitidos", len(df_v))

        df_crit = pd.read_sql("SELECT nombre, stock, stock_minimo FROM productos WHERE stock <= stock_minimo", engine)
        c3.metric("⚠️ Alertas de Stock", len(df_crit), delta=len(df_crit), delta_color="inverse")

        df_prod_hoy = pd.read_sql(
            f"SELECT COALESCE(SUM(cantidad), 0) as total FROM movimientos WHERE tipo='produccion' AND fecha::date = '{hoy}'",
            engine
        )
        c4.metric("👩‍🍳 Unidades Producidas", f"{df_prod_hoy['total'].iloc[0]:.1f}")

        st.divider()

        # --- GRÁFICOS ---
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("💳 Ventas por Medio de Pago")
            if not df_v.empty:
                fig_pago = px.pie(df_v, values='total', names='medio_pago', hole=0.4,
                                  color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_pago, use_container_width=True)
            else:
                st.info("Sin ventas registradas hoy.")

        with col_g2:
            st.subheader("🔥 Top 5 Más Vendidos")
            df_top = pd.read_sql("""
                SELECT p.nombre, SUM(dv.cantidad) as total
                FROM detalle_ventas dv
                JOIN productos p ON dv.producto_id = p.id
                GROUP BY p.nombre
                ORDER BY total DESC
                LIMIT 5
            """, engine)
            if not df_top.empty:
                fig_top = px.bar(df_top, x='total', y='nombre', orientation='h',
                                 color='total', color_continuous_scale='Viridis')
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.info("Sin datos de ventas aún.")

        st.divider()

        # --- STOCK CRÍTICO ---
        if not df_crit.empty:
            st.subheader("⚠️ Productos Bajo Mínimo")
            st.dataframe(df_crit, use_container_width=True, hide_index=True)

        # --- PRODUCCIÓN SEMANA ---
        st.subheader("👩‍🍳 Producción de la Semana")
        df_semana = pd.read_sql("""
            SELECT p.nombre, m.cantidad, m.fecha::date as dia
            FROM movimientos m
            JOIN productos p ON m.producto_id = p.id
            WHERE m.tipo = 'produccion'
            AND m.fecha > CURRENT_DATE - INTERVAL '7 days'
        """, engine)
        if not df_semana.empty:
            fig_prod = px.area(df_semana, x="dia", y="cantidad", color="nombre",
                               title="Volumen de Elaboración")
            st.plotly_chart(fig_prod, use_container_width=True)
        else:
            st.info("No hay registros de producción en la última semana.")

    except Exception as e:
        st.error(f"Error al cargar el dashboard: {e}")
        
