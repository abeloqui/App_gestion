import streamlit as st
import pandas as pd
from database import get_connection, get_engine
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("🏁 Cierre de Caja y Reporte Diario")

if "reporte_cierre_bin" not in st.session_state:
    st.session_state.reporte_cierre_bin = None

def generar_reporte_cierre_pdf(df_pagos, df_ventas, df_stock_bajo, efectivo_esp, contado, fecha):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    estilo_h1 = ParagraphStyle('H1', fontSize=16, alignment=1, spaceAfter=20, fontName="Helvetica-Bold")
    estilo_h2 = ParagraphStyle('H2', fontSize=12, spaceBefore=15, spaceAfter=10, fontName="Helvetica-Bold")
    estilo_texto = ParagraphStyle('N', fontSize=10)

    # Encabezado
    elements.append(Paragraph(f"REPORTE DE CIERRE DIARIO - DULCE JAZMÍN", estilo_h1))
    elements.append(Paragraph(f"Fecha: {fecha}", estilo_texto))
    elements.append(Paragraph(f"Generado por: {st.session_state.username}", estilo_texto))
    elements.append(Paragraph(f"Hora de cierre: {datetime.now().strftime('%H:%M')}", estilo_texto))
    elements.append(Spacer(1, 10))

    # 1. Resumen Financiero
    elements.append(Paragraph("1. Resumen de Ingresos por Medio de Pago", estilo_h2))
    data_pagos = [["Medio de Pago", "Total Recaudado"]]
    for _, row in df_pagos.iterrows():
        data_pagos.append([str(row['medio_pago']), f"${row['total']:,.2f}"])
    data_pagos.append(["TOTAL", f"${df_pagos['total'].sum():,.2f}"])

    t_pagos = Table(data_pagos, colWidths=[120, 120])
    t_pagos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black)
    ]))
    elements.append(t_pagos)
    elements.append(Spacer(1, 10))

    diferencia = contado - efectivo_esp
    elements.append(Paragraph(f"<b>Efectivo Esperado en Caja:</b> ${efectivo_esp:,.2f}", estilo_texto))
    elements.append(Paragraph(f"<b>Efectivo Contado Físicamente:</b> ${contado:,.2f}", estilo_texto))
    color_dif = "red" if diferencia < 0 else "green"
    elements.append(Paragraph(f'<b>Diferencia:</b> <font color="{color_dif}">${diferencia:,.2f}</font>', estilo_texto))
    elements.append(Spacer(1, 10))

    # 2. Alertas de Stock
    elements.append(Paragraph("2. Alertas de Inventario (Bajo Mínimo)", estilo_h2))
    if not df_stock_bajo.empty:
        data_stock = [["Producto", "Stock Actual", "Mínimo", "Unidad"]]
        for _, row in df_stock_bajo.iterrows():
            data_stock.append([row['nombre'], str(row['stock']), str(row['stock_minimo']), row.get('unidad', '-')])
        t_stock = Table(data_stock, colWidths=[160, 70, 70, 70])
        t_stock.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.indianred),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black)
        ]))
        elements.append(t_stock)
    else:
        elements.append(Paragraph("✅ No hay productos bajo el nivel crítico.", estilo_texto))

    # 3. Detalle de Ventas
    elements.append(Paragraph("3. Detalle de Operaciones del Día", estilo_h2))
    if not df_ventas.empty:
        data_v = [["#", "Hora", "Total", "Medio de Pago"]]
        for i, row in df_ventas.iterrows():
            hora = row['fecha'].strftime('%H:%M') if hasattr(row['fecha'], 'strftime') else str(row['fecha'])
            data_v.append([str(i+1), hora, f"${row['total']:.2f}", row['medio_pago']])
        t_v = Table(data_v, colWidths=[30, 60, 100, 100])
        t_v.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8)
        ]))
        elements.append(t_v)
    else:
        elements.append(Paragraph("Sin ventas registradas.", estilo_texto))

    doc.build(elements)
    return buffer.getvalue()

# --- INTERFAZ ---
engine = get_engine()
hoy = pd.Timestamp.now().date()

df_pagos = pd.read_sql(f"""
    SELECT medio_pago, SUM(total) as total 
    FROM ventas 
    WHERE fecha::date = '{hoy}' 
    GROUP BY medio_pago
""", engine)

df_ventas = pd.read_sql(f"""
    SELECT id, fecha, total, medio_pago 
    FROM ventas 
    WHERE fecha::date = '{hoy}' 
    ORDER BY fecha ASC
""", engine)

df_alertas = pd.read_sql("""
    SELECT nombre, stock, stock_minimo, unidad 
    FROM productos 
    WHERE stock <= stock_minimo
""", engine)

if df_ventas.empty:
    st.info("Aún no hay ventas registradas hoy.")
else:
    st.subheader(f"Balance del día: {hoy.strftime('%d/%m/%Y')}")

    c1, c2, c3 = st.columns(3)
    total_dia = df_pagos['total'].sum()
    efectivo_esp = float(df_pagos[df_pagos['medio_pago'] == 'Efectivo']['total'].sum()) if 'Efectivo' in df_pagos['medio_pago'].values else 0.0

    c1.metric("💰 Total del Día", f"${total_dia:,.2f}")
    c2.metric("🧾 Tickets", len(df_ventas))
    c3.metric("💵 Efectivo Esperado", f"${efectivo_esp:,.2f}")

    st.divider()
    st.dataframe(df_pagos, use_container_width=True, hide_index=True)

    if not df_alertas.empty:
        st.divider()
        st.error(f"⚠️ {len(df_alertas)} producto(s) bajo el mínimo — revisar antes de cerrar.")
        st.dataframe(df_alertas, use_container_width=True, hide_index=True)

    st.divider()
    st.write("### 📝 Confirmación de Cierre")
    contado = st.number_input("Efectivo contado físicamente ($)", min_value=0.0, step=100.0)

    diferencia = contado - efectivo_esp
    if contado > 0:
        if diferencia == 0:
            st.success("✅ Caja cuadrada.")
        elif diferencia > 0:
            st.warning(f"💰 Sobran ${diferencia:,.2f} en caja.")
        else:
            st.error(f"⚠️ Faltan ${abs(diferencia):,.2f} en caja.")

    if st.button("🚀 GENERAR CIERRE Y PDF", type="primary", use_container_width=True):
        pdf_bin = generar_reporte_cierre_pdf(df_pagos, df_ventas, df_alertas, efectivo_esp, contado, hoy)
        st.session_state.reporte_cierre_bin = pdf_bin
        st.success("✅ Reporte generado.")

if st.session_state.reporte_cierre_bin:
    st.balloons()
    st.download_button(
        label="📥 DESCARGAR REPORTE PDF",
        data=st.session_state.reporte_cierre_bin,
        file_name=f"cierre_caja_{hoy}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    if st.button("🧹 Limpiar Pantalla"):
        st.session_state.reporte_cierre_bin = None
        st.rerun()
    
