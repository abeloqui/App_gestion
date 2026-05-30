import streamlit as st
import pandas as pd
from database import get_engine
from datetime import date, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

# --- RESTAURAR SESIÓN ---
if "logged_in" not in st.session_state:
    params = st.query_params
    st.session_state.logged_in = params.get("logged_in", "false") == "true"
    st.session_state.username = params.get("username", None)
    st.session_state.rol = params.get("rol", None)

if not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

if st.session_state.get("rol") != "admin":
    st.error("🔒 Acceso restringido. Solo administradores.")
    st.stop()

st.header("📅 Historial de Compras")

engine = get_engine()

col1, col2, col3 = st.columns(3)
with col1:
    fecha_desde = st.date_input("Desde", value=date.today() - timedelta(days=30))
with col2:
    fecha_hasta = st.date_input("Hasta", value=date.today())
with col3:
    df_prods = pd.read_sql("SELECT nombre FROM productos ORDER BY nombre", engine)
    opciones = ["Todos"] + df_prods['nombre'].tolist()
    filtro_prod = st.selectbox("Producto", opciones)

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
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Total Ingresos", len(df))
    c2.metric("💰 Gasto Total", f"${float(df['total'].sum()):,.2f}")
    c3.metric("📊 Costo Prom. Unitario", f"${float(df['precio_unit'].mean()):,.2f}")

    st.divider()
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📥 Exportar")

    # Generar Excel
    excel_buf = BytesIO()
    with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Historial Compras')

    # Generar PDF
    pdf_buf = BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=A4, rightMargin=20, leftMargin=20,
                            topMargin=20, bottomMargin=20)
    elements = []
    h1 = ParagraphStyle('H1', fontSize=14, alignment=1, spaceAfter=10, fontName="Helvetica-Bold")
    normal = ParagraphStyle('N', fontSize=9)
    cell_style = ParagraphStyle('C', fontSize=7, wordWrap='CJK')

    elements.append(Paragraph(f"HISTORIAL DE COMPRAS — DULCE JAZMÍN", h1))
    elements.append(Paragraph(f"Período: {fecha_desde} al {fecha_hasta}", normal))
    elements.append(Spacer(1, 10))

    data = [["Fecha", "Producto", "Cant.", "P.Unit.", "Total"]]
    for _, row in df.iterrows():
        data.append([
            str(row['fecha']),
            Paragraph(str(row['producto']), cell_style),
            f"{row['cantidad']:.1f}",
            f"${row['precio_unit']:,.2f}",
            f"${row['total']:,.2f}",
        ])

    t = Table(data, colWidths=[55, 175, 40, 60, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.4, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
    ]))
    elements.append(t)
    doc.build(elements)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            "📊 Descargar Excel",
            excel_buf.getvalue(),
            file_name=f"compras_{fecha_desde}_{fecha_hasta}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with col_d2:
        st.download_button(
            "📄 Descargar PDF",
            pdf_buf.getvalue(),
            file_name=f"compras_{fecha_desde}_{fecha_hasta}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
