import streamlit as st
import pandas as pd
from database import get_connection
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

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

if not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()


st.header("📦 Stock Actual")

def export_stock_to_pdf(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>REPORTE DE STOCK - DULCE JAZMÍN</b>", styles['Title']))
    data = [["Producto", "Categoría", "Unidad", "Cantidad", "Mínimo"]]
    for _, r in df.iterrows():
        data.append([r['nombre'], r['categoria'], r.get('unidad', '-'),
                     str(r['stock']), str(r['stock_minimo'])])
    t = Table(data, colWidths=[55*mm, 35*mm, 20*mm, 25*mm, 25*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black)
    ]))
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

conn = get_connection()
df = pd.read_sql_query("""
    SELECT nombre, categoria, subcategoria, unidad, precio_venta, stock, stock_minimo
    FROM productos
    ORDER BY subcategoria, nombre
""", conn)
conn.close()

if df.empty:
    st.warning("No hay productos cargados.")
else:
    # Alerta general si hay productos bajo mínimo
    df_bajo = df[df['stock'] <= df['stock_minimo']]
    if not df_bajo.empty:
        st.error(f"⚠️ {len(df_bajo)} producto(s) por debajo del mínimo.")
        df_alerta = df_bajo[['nombre', 'stock', 'stock_minimo', 'unidad']].rename(
            columns={'stock': 'cantidad', 'stock_minimo': 'mínimo'})
        st.dataframe(df_alerta, use_container_width=True, hide_index=True)
        st.divider()

    st.subheader("Stock por Tipo")
    tab_mp, tab_final = st.tabs(["📦 Materia Prima", "🏷️ Producto Final"])

    # --- MATERIA PRIMA: sin precio ---
    with tab_mp:
        df_mp = df[df["subcategoria"] == "Materia Prima"].copy()
        if df_mp.empty:
            st.info("No hay materia prima cargada aún.")
        else:
            df_mp = df_mp[["nombre", "categoria", "unidad", "stock", "stock_minimo"]].rename(
                columns={'stock': 'cantidad', 'stock_minimo': 'mínimo'})

            def resaltar_mp(row):
                if row['cantidad'] <= row['mínimo']:
                    return ['background-color: #ffcccc'] * len(row)
                return [''] * len(row)

            styled_mp = df_mp.style.apply(resaltar_mp, axis=1)
            st.dataframe(styled_mp, use_container_width=True, hide_index=True)

    # --- PRODUCTO FINAL: con precio ---
    with tab_final:
        df_pf = df[df["subcategoria"] == "Producto Final"].copy()
        if df_pf.empty:
            st.info("No hay productos finales cargados aún.")
        else:
            df_pf = df_pf[["nombre", "categoria", "unidad", "precio_venta", "stock", "stock_minimo"]].rename(
                columns={'precio_venta': 'precio', 'stock': 'cantidad', 'stock_minimo': 'mínimo'})

            def resaltar_pf(row):
                if row['cantidad'] <= row['mínimo']:
                    return ['background-color: #ffcccc'] * len(row)
                return [''] * len(row)

            styled_pf = df_pf.style.apply(resaltar_pf, axis=1)
            st.dataframe(styled_pf, use_container_width=True, hide_index=True)

    st.divider()
    if st.button("📄 Exportar PDF"):
        pdf_data = export_stock_to_pdf(df)
        st.download_button("⬇️ Descargar PDF", pdf_data, "stock_completo.pdf", "application/pdf")
                         
