import streamlit as st
import pandas as pd
from database import get_engine
from datetime import date, timedelta

from streamlit_cookies_manager import EncryptedCookieManager

# --- COOKIES: restaurar sesión ---
cookies = EncryptedCookieManager(prefix="dulcejazmin_", password="dj_secret_2024_$")
if not cookies.ready():
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = cookies.get("logged_in") == "true"
if "username" not in st.session_state:
    st.session_state.username = cookies.get("username") or None
if "rol" not in st.session_state:
    st.session_state.rol = cookies.get("rol") or None



if "logged_in" not in st.session_state or not st.session_state.logged_in or "rol" not in st.session_state:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

if st.session_state.rol != 'admin':
    st.error("🔒 Acceso restringido. Solo administradores.")
    st.stop()

st.header("📅 Historial de Compras")

engine = get_engine()

# --- FILTROS ---
col1, col2, col3 = st.columns(3)
with col1:
    fecha_desde = st.date_input("Desde", value=date.today() - timedelta(days=30))
with col2:
    fecha_hasta = st.date_input("Hasta", value=date.today())
with col3:
    df_prods = pd.read_sql("SELECT nombre FROM productos ORDER BY nombre", engine)
    opciones = ["Todos"] + df_prods['nombre'].tolist()
    filtro_prod = st.selectbox("Producto", opciones)

# --- CONSULTA ---
query = f"""
    SELECT 
        m.fecha::date as fecha,
        p.nombre as producto,
        p.subcategoria as tipo,
        p.unidad,
        m.cantidad,
        m.costo_unitario as precio_unit,
        m.total,
        m.usuario,
        m.detalle
    FROM movimientos m
    JOIN productos p ON m.producto_id = p.id
    WHERE m.tipo = 'compra'
    AND m.fecha::date BETWEEN '{fecha_desde}' AND '{fecha_hasta}'
"""
if filtro_prod != "Todos":
    query += f" AND p.nombre = '{filtro_prod}'"
query += " ORDER BY m.fecha DESC"

df = pd.read_sql(query, engine)

if df.empty:
    st.info("No hay compras registradas para ese período.")
else:
    # Métricas resumen
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Total de Ingresos", len(df))
    c2.metric("💰 Gasto Total", f"${df['total'].sum():,.2f}")
    c3.metric("📊 Costo Promedio Unitario", f"${df['precio_unit'].mean():,.2f}")

    st.divider()
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Exportar a Excel
    st.divider()
    if st.button("📥 Exportar a Excel"):
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Historial Compras')
        st.download_button(
            "⬇️ Descargar Excel",
            output.getvalue(),
            file_name=f"historial_compras_{fecha_desde}_{fecha_hasta}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
