import streamlit as st
from database import init_db, get_engine
import pandas as pd

# Configuración inicial
st.set_page_config(page_title="Sistema Gestión Pro", layout="wide")

# Inicializar Base de Datos
try:
    init_db()
except Exception as e:
    st.error(f"Error de base de datos: {e}")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso al Sistema")
    with st.form("login_form"):
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            if user == "admin" and pw == "1234":
                st.session_state.logged_in = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
else:
    st.title(f"📊 Panel de Control - {st.session_state.username}")
    engine = get_engine()
    
    # Métricas Superiores
    c1, c2, c3 = st.columns(3)
    hoy = pd.Timestamp.now().date()
    try:
        df_v = pd.read_sql(f"SELECT total, medio_pago FROM ventas WHERE fecha >= '{hoy}'", engine)
        c1.metric("Ventas Hoy", f"${df_v['total'].sum():,.2f}")
        c2.metric("Operaciones", len(df_v))
        
        df_crit = pd.read_sql("SELECT nombre, stock FROM productos WHERE stock <= stock_minimo", engine)
        c3.metric("Alertas Stock", len(df_crit), delta_color="inverse")
        
        if not df_crit.empty:
            st.warning("⚠️ Productos bajo stock mínimo:")
            st.dataframe(df_crit, use_container_width=True)

        # Gráficos
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("💰 Ventas por Pago (Hoy)")
            if not df_v.empty:
                st.bar_chart(df_v.groupby('medio_pago')['total'].sum())
        with col_g2:
            st.subheader("🔥 Top 5 Más Vendidos")
            query_top = "SELECT p.nombre, SUM(m.cantidad) as cant FROM movimientos m JOIN productos p ON m.producto_id = p.id WHERE m.tipo = 'venta' GROUP BY p.nombre ORDER BY cant DESC LIMIT 5"
            df_top = pd.read_sql(query_top, engine)
            if not df_top.empty:
                st.bar_chart(data=df_top, x="nombre", y="cant")
    except:
        st.info("Sin datos suficientes para mostrar estadísticas.")
