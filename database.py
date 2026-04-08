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

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso al Sistema - Pastelería Dulce Jazmín")
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
    st.stop()

# --- DASHBOARD PRINCIPAL ---
st.title(f"📊 Panel de Control - {st.session_state.username}")
engine = get_engine()
hoy = pd.Timestamp.now().date()

st.subheader("📈 Resumen General del Día")

# --- MÉTRICAS SUPERIORES ---
c1, c2, c3, c4, c5 = st.columns(5)

try:
    # Ventas del día
    df_v = pd.read_sql(f"SELECT total, medio_pago FROM ventas WHERE fecha >= '{hoy}'", engine)
    ventas_hoy = df_v['total'].sum() if not df_v.empty else 0
    tickets_hoy = len(df_v)

    # Alertas de stock total
    df_crit = pd.read_sql("SELECT nombre, stock, subcategoria FROM productos WHERE stock <= stock_minimo", engine)
    alertas_total = len(df_crit)

    # Producción del día
    df_prod_hoy = pd.read_sql(
        f"SELECT SUM(cantidad) as total FROM movimientos WHERE tipo='produccion' AND fecha >= '{hoy}'", 
        engine
    )
    cant_prod = df_prod_hoy['total'].iloc[0] if not df_prod_hoy.empty and df_prod_hoy['total'].iloc[0] is not None else 0

    # Stock por subcategoría
    df_stock_tipo = pd.read_sql("""
        SELECT subcategoria, SUM(stock) as stock_total, COUNT(*) as cantidad_productos 
        FROM productos 
        GROUP BY subcategoria
    """, engine)

    c1.metric("💰 Ventas Hoy", f"${ventas_hoy:,.2f}")
    c2.metric("🎟️ Tickets Hoy", tickets_hoy)
    c3.metric("⚠️ Alertas de Stock", alertas_total, delta=alertas_total, delta_color="inverse")
    c4.metric("👩‍🍳 Producido Hoy", f"{cant_prod:.1f}")
    
    # Mostramos stock total de Producto Final como métrica principal
    stock_final = df_stock_tipo[df_stock_tipo['subcategoria'] == 'Producto Final']['stock_total'].sum() if not df_stock_tipo.empty else 0
    c5.metric("🏷️ Stock Producto Final", f"{stock_final:.1f} u/kg")

    st.divider()

    # --- STOCK FRACCIONADO ---
    st.subheader("📦 Stock Actual por Tipo")
    if not df_stock_tipo.empty:
        col_mp, col_pre, col_final = st.columns(3)
        
        with col_mp:
            mp = df_stock_tipo[df_stock_tipo['subcategoria'] == 'Materia Prima']
            st.metric("📦 Materia Prima", 
                     f"{mp['stock_total'].sum() if not mp.empty else 0:.1f} u/kg",
                     f"{mp['cantidad_productos'].sum() if not mp.empty else 0} productos")
        
        with col_pre:
            pre = df_stock_tipo[df_stock_tipo['subcategoria'] == 'Preelaborado']
            st.metric("🔧 Preelaborado", 
                     f"{pre['stock_total'].sum() if not pre.empty else 0:.1f} u/kg",
                     f"{pre['cantidad_productos'].sum() if not pre.empty else 0} productos")
        
        with col_final:
            final = df_stock_tipo[df_stock_tipo['subcategoria'] == 'Producto Final']
            st.metric("🏷️ Producto Final", 
                     f"{final['stock_total'].sum() if not final.empty else 0:.1f} u/kg",
                     f"{final['cantidad_productos'].sum() if not final.empty else 0} productos")
    else:
        st.info("No hay productos cargados aún.")

    st.divider()

    # --- GRÁFICOS ---
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("💰 Ventas por Medio de Pago (Hoy)")
        if not df_v.empty:
            fig_pago = px.pie(df_v, values='total', names='medio_pago', 
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pago, use_container_width=True)
        else:
            st.info("Sin ventas registradas hoy")

    with col_g2:
        st.subheader("🔥 Top 5 Productos Finales Más Vendidos")
        query_top = """
            SELECT p.nombre, SUM(m.cantidad) as total 
            FROM movimientos m 
            JOIN productos p ON m.producto_id = p.id 
            WHERE m.tipo='venta' 
              AND p.subcategoria = 'Producto Final'
            GROUP BY p.nombre 
            ORDER BY total DESC LIMIT 5
        """
        df_top = pd.read_sql(query_top, engine)
        if not df_top.empty:
            fig_top = px.bar(df_top, x='total', y='nombre', orientation='h', 
                           color='total', color_continuous_scale='Viridis')
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("Aún no hay ventas de productos finales")

    # --- ALERTAS Y PRODUCCIÓN ---
    st.divider()
    col_p1, col_p2 = st.columns([2, 1])

    with col_p1:
        st.subheader("👩‍🍳 Producción de la Última Semana")
        df_semana = pd.read_sql("""
            SELECT p.nombre, m.cantidad, m.fecha::date as dia
            FROM movimientos m
            JOIN productos p ON m.producto_id = p.id
            WHERE m.tipo='produccion'
              AND m.fecha > CURRENT_DATE - INTERVAL '7 days'
            ORDER BY m.fecha
        """, engine)
        
        if not df_semana.empty:
            fig_prod = px.area(df_semana, x="dia", y="cantidad", color="nombre", 
                             title="Volumen de Elaboración por Producto")
            st.plotly_chart(fig_prod, use_container_width=True)
        else:
            st.info("No hay registros de producción en la última semana.")

    with col_p2:
        st.subheader("⚠️ Productos Bajo Mínimo")
        if not df_crit.empty:
            # Mostramos agrupado por subcategoría
            for subtipo in ['Materia Prima', 'Preelaborado', 'Producto Final']:
                df_sub = df_crit[df_crit['subcategoria'] == subtipo]
                if not df_sub.empty:
                    st.write(f"**{subtipo}**")
                    st.dataframe(df_sub[['nombre', 'stock']], hide_index=True, use_container_width=True)
        else:
            st.success("✅ No hay alertas de stock crítico en este momento.")

except Exception as e:
    st.error(f"Error al cargar el dashboard: {e}")
