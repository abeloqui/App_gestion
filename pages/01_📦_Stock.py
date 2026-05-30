import streamlit as st
import pandas as pd
from database import get_connection
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

# --- RESTAURAR SESIÓN ---
if "logged_in" not in st.session_state:
    params = st.query_params
    st.session_state.logged_in = params.get("logged_in", "false") == "true"
    st.session_state.username = params.get("username", None)
    st.session_state.rol = params.get("rol", None)

if not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📦 Stock Actual")

def export_stock_to_pdf(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15, leftMargin=15,
                            topMargin=15, bottomMargin=15)
    elements = []
    h1 = ParagraphStyle('H1', fontSize=14, alignment=1, spaceAfter=10, fontName="Helvetica-Bold")
    cell = ParagraphStyle('C', fontSize=7, wordWrap='CJK')

    elements.append(Paragraph("REPORTE DE STOCK — DULCE JAZMÍN", h1))
    elements.append(Spacer(1, 6))

    data = [["Producto", "Categoría", "Unidad", "Cantidad", "Mínimo"]]
    for _, r in df.iterrows():
        data.append([
            Paragraph(str(r['nombre']), cell),
            str(r['categoria']),
            str(r.get('unidad', '-')),
            str(r['stock']),
            str(r['stock_minimo'])
        ])

    t = Table(data, colWidths=[175, 70, 40, 45, 45])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (2,0), (-1,-1), 'CENTER'),
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
    df_bajo = df[df['stock'] <= df['stock_minimo']]
    if not df_bajo.empty:
        st.error(f"⚠️ {len(df_bajo)} producto(s) por debajo del mínimo.")
        df_alerta = df_bajo[['nombre', 'stock', 'stock_minimo', 'unidad']].rename(
            columns={'stock': 'cantidad', 'stock_minimo': 'mínimo'})
        st.dataframe(df_alerta, use_container_width=True, hide_index=True)
        st.divider()

    st.subheader("Stock por Tipo")
    tab_mp, tab_final = st.tabs(["📦 Materia Prima", "🏷️ Producto Final"])

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
            st.dataframe(df_mp.style.apply(resaltar_mp, axis=1), use_container_width=True, hide_index=True)

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
            st.dataframe(df_pf.style.apply(resaltar_pf, axis=1), use_container_width=True, hide_index=True)

    st.divider()
    pdf_data = export_stock_to_pdf(df)
    st.download_button(
        "📄 Descargar PDF",
        pdf_data,
        "stock_completo.pdf",
        "application/pdf",
        use_container_width=True
    )
