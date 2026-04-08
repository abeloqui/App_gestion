import streamlit as st
from database import init_db, get_engine
import pandas as pd
import plotly.express as px

# Configuración inicial
st.set_page_config(page_title="Pastelería Gestión Pro", layout="wide", page_icon="🎂")

# Inicializar Base de Datos
try:
    init_db()
except Exception as e:
    st.error(f"Error de base de datos: {e}")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso al Sistema - Pastelería")
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
    engine = get_engine()
    hoy = pd.Timestamp.now().date()
    
    # --- MÉTRICAS SUPERIORES ---
    c1, c2, c3, c4 = st.columns(4)
    try:
        # Ventas del día
        df_v = pd.read_sql(f"SELECT total, medio_pago FROM ventas WHERE fecha >= '{hoy}'", engine)
        c1.metric("Ventas Hoy", f"${df_v['total'].sum():,.2f}")
        c2.metric("Tickets Emitidos", len(df_v))
        
        # Alertas de Stock
        df_crit = pd.read_sql("SELECT nombre, stock FROM productos WHERE stock <= stock_minimo", engine)
        c3.metric("Alertas de Stock", len(df_crit), delta=len(df_crit), delta_color="inverse")
        
        # Producción del día
        df_prod_hoy = pd.read_sql(f"SELECT SUM(cantidad) as total FROM movimientos WHERE tipo='produccion' AND fecha >= '{hoy}'", engine)
        cant_prod = df_prod_hoy['total'].iloc[0] or 0
        c4.metric("Unidades Producidas", f"{cant_prod:.1f}")

        st.divider()

        # --- FILA DE GRÁFICOS 1: VENTAS ---
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("💰 Ventas por Medio de Pago")
            if not df_v.empty:
                fig_pago = px.pie(df_v, values='total', names='medio_pago', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_pago, use_container_width=True)
            else:
                st.info("Sin ventas hoy")

        with col_g2:
            st.subheader("🔥 Top 5 Más Vendidos")
            query_top = "SELECT p.nombre, SUM(m.cantidad) as total FROM movimientos m JOIN productos p ON m.producto_id = p.id WHERE m.tipo='venta' GROUP BY p.nombre ORDER BY total DESC LIMIT 5"
            df_top = pd.read_sql(query_top, engine)
            if not df_top.empty:
                fig_top = px.bar(df_top, x='total', y='nombre', orientation='h', color='total', color_continuous_scale='Viridis')
                st.plotly_chart(fig_top, use_container_width=True)

        # --- FILA DE GRÁFICOS 2: PRODUCCIÓN ---
        st.divider()
        col_p1, col_p2 = st.columns([2, 1])
        
        with col_p1:
            st.subheader("👩‍🍳 Producción de la Semana")
            # Traemos los últimos 7 días de producción
            df_semana = pd.read_sql("""
                SELECT p.nombre, m.cantidad, m.fecha::date as dia 
                FROM movimientos m 
                JOIN productos p ON m.producto_id = p.id 
                WHERE m.tipo='produccion' 
                AND m.fecha > CURRENT_DATE - INTERVAL '7 days'
            """, engine)
            if not df_semana.empty:
                fig_prod = px.area(df_semana, x="dia", y="cantidad", color="nombre", title="Volumen de Elaboración")
                st.plotly_chart(fig_prod, use_container_width=True)
            else:
                st.info("No hay registros de producción en la última semana.")

        with col_p2:
            if not df_crit.empty:
                st.subheader("⚠️ Reponer Urgente")
                st.dataframe(df_crit[['nombre', 'stock']], hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"Error al cargar el dashboard: {e}")
            
