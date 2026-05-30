import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_engine
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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






st.header("📊 Reporte Mensual")

engine = get_engine()

# --- SELECTOR DE MES ---
col1, col2 = st.columns(2)
with col1:
    mes = st.selectbox("Mes", list(range(1, 13)), index=date.today().month - 1,
                       format_func=lambda m: ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                               "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][m-1])
with col2:
    anio = st.number_input("Año", min_value=2024, max_value=2030, value=date.today().year)

if st.button("🔍 Generar Reporte", type="primary", use_container_width=True):

    # --- VENTAS DEL MES ---
    df_ventas = pd.read_sql(f"""
        SELECT fecha::date as dia, SUM(total) as total, COUNT(*) as tickets
        FROM ventas
        WHERE EXTRACT(MONTH FROM fecha) = {mes} AND EXTRACT(YEAR FROM fecha) = {anio}
        GROUP BY dia ORDER BY dia
    """, engine)

    df_medios = pd.read_sql(f"""
        SELECT medio_pago, SUM(total) as total, COUNT(*) as cantidad
        FROM ventas
        WHERE EXTRACT(MONTH FROM fecha) = {mes} AND EXTRACT(YEAR FROM fecha) = {anio}
        GROUP BY medio_pago
    """, engine)

    df_productos = pd.read_sql(f"""
        SELECT p.nombre, SUM(dv.cantidad) as unidades, SUM(dv.subtotal) as facturado
        FROM detalle_ventas dv
        JOIN productos p ON dv.producto_id = p.id
        JOIN ventas v ON dv.venta_id = v.id
        WHERE EXTRACT(MONTH FROM v.fecha) = {mes} AND EXTRACT(YEAR FROM v.fecha) = {anio}
        GROUP BY p.nombre ORDER BY facturado DESC
    """, engine)

    # --- COMPRAS DEL MES ---
    df_compras = pd.read_sql(f"""
        SELECT p.nombre, SUM(m.cantidad) as cantidad, SUM(m.total) as gasto
        FROM movimientos m
        JOIN productos p ON m.producto_id = p.id
        WHERE m.tipo = 'compra'
        AND EXTRACT(MONTH FROM m.fecha) = {mes} AND EXTRACT(YEAR FROM m.fecha) = {anio}
        GROUP BY p.nombre ORDER BY gasto DESC
    """, engine)

    total_ventas = df_ventas['total'].sum() if not df_ventas.empty else 0
    total_compras = df_compras['gasto'].sum() if not df_compras.empty else 0
    ganancia_bruta = total_ventas - total_compras

    # --- MÉTRICAS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Ventas", f"${total_ventas:,.2f}")
    c2.metric("🚚 Total Compras", f"${total_compras:,.2f}")
    c3.metric("📈 Ganancia Bruta", f"${ganancia_bruta:,.2f}",
              delta=f"{(ganancia_bruta/total_ventas*100):.1f}% margen" if total_ventas > 0 else "")
    c4.metric("🧾 Tickets emitidos", df_ventas['tickets'].sum() if not df_ventas.empty else 0)

    st.divider()

    # --- GRÁFICOS ---
    if not df_ventas.empty:
        st.subheader("📈 Evolución de Ventas Diarias")
        fig = px.bar(df_ventas, x='dia', y='total', text_auto='.0f',
                     color_discrete_sequence=['#2ecc71'])
        st.plotly_chart(fig, use_container_width=True)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if not df_medios.empty:
            st.subheader("💳 Ventas por Medio de Pago")
            fig2 = px.pie(df_medios, values='total', names='medio_pago', hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

    with col_g2:
        if not df_productos.empty:
            st.subheader("🏆 Top Productos Vendidos")
            fig3 = px.bar(df_productos.head(8), x='facturado', y='nombre',
                          orientation='h', color='facturado', color_continuous_scale='Blues')
            st.plotly_chart(fig3, use_container_width=True)

    st.divider()
    st.subheader("📋 Detalle de Productos Vendidos")
    if not df_productos.empty:
        st.dataframe(df_productos, use_container_width=True, hide_index=True)

    st.subheader("🚚 Detalle de Compras del Mes")
    if not df_compras.empty:
        st.dataframe(df_compras, use_container_width=True, hide_index=True)
    else:
        st.info("Sin compras registradas este mes.")

    st.divider()

    # --- EXPORTAR EXCEL ---
    nombre_mes = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][mes-1]

    col_ex1, col_ex2 = st.columns(2)

    with col_ex1:
        if st.button("📥 Exportar a Excel"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                if not df_ventas.empty:
                    df_ventas.to_excel(writer, sheet_name='Ventas por Día', index=False)
                if not df_medios.empty:
                    df_medios.to_excel(writer, sheet_name='Medios de Pago', index=False)
                if not df_productos.empty:
                    df_productos.to_excel(writer, sheet_name='Productos Vendidos', index=False)
                if not df_compras.empty:
                    df_compras.to_excel(writer, sheet_name='Compras', index=False)
                # Resumen
                df_resumen = pd.DataFrame({
                    'Concepto': ['Total Ventas', 'Total Compras', 'Ganancia Bruta'],
                    'Monto': [total_ventas, total_compras, ganancia_bruta]
                })
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

            st.download_button(
                "⬇️ Descargar Excel",
                output.getvalue(),
                file_name=f"reporte_{nombre_mes}_{anio}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with col_ex2:
        if st.button("📄 Exportar a PDF"):
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20,
                                    topMargin=20, bottomMargin=20)
            elements = []
            styles = getSampleStyleSheet()
            h1 = ParagraphStyle('H1', fontSize=16, alignment=1, spaceAfter=15, fontName="Helvetica-Bold")
            h2 = ParagraphStyle('H2', fontSize=12, spaceBefore=12, spaceAfter=8, fontName="Helvetica-Bold")
            normal = ParagraphStyle('N', fontSize=10)

            elements.append(Paragraph(f"REPORTE MENSUAL — {nombre_mes.upper()} {anio}", h1))
            elements.append(Paragraph("Dulce Jazmín — Sistema de Gestión", normal))
            elements.append(Spacer(1, 10))

            # Resumen
            elements.append(Paragraph("Resumen Financiero", h2))
            data_res = [
                ["Concepto", "Monto"],
                ["Total Ventas", f"${total_ventas:,.2f}"],
                ["Total Compras", f"${total_compras:,.2f}"],
                ["Ganancia Bruta", f"${ganancia_bruta:,.2f}"],
            ]
            t = Table(data_res, colWidths=[200, 150])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('BACKGROUND', (0,-1), (-1,-1), colors.lightgreen),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 10))

            # Top productos
            if not df_productos.empty:
                elements.append(Paragraph("Productos Más Vendidos", h2))
                data_p = [["Producto", "Unidades", "Facturado"]]
                for _, row in df_productos.head(10).iterrows():
                    data_p.append([row['nombre'], f"{row['unidades']:.1f}", f"${row['facturado']:,.2f}"])
                tp = Table(data_p, colWidths=[200, 80, 100])
                tp.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.steelblue),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                ]))
                elements.append(tp)

            doc.build(elements)
            st.download_button(
                "⬇️ Descargar PDF",
                buffer.getvalue(),
                file_name=f"reporte_{nombre_mes}_{anio}.pdf",
                mime="application/pdf"
            )
