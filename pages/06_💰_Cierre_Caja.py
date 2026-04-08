import streamlit as st
import pandas as pd
from database import get_connection, get_engine
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Validación de Sesión
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("🏁 Cierre de Caja y Reporte Diario")

# Inicializar estado del reporte
if "reporte_cierre_bin" not in st.session_state:
    st.session_state.reporte_cierre_bin = None

# --- FUNCIÓN PARA GENERAR EL PDF DE CIERRE ---
def generar_reporte_cierre_pdf(df_pagos, df_ventas, df_stock_bajo, efectivo_esp, contado, fecha):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos Custom
    estilo_h1 = ParagraphStyle('H1', fontSize=16, alignment=1, spaceAfter=20, fontName="Helvetica-Bold")
    estilo_h2 = ParagraphStyle('H2', fontSize=12, spaceBefore=15, spaceAfter=10, fontName="Helvetica-Bold")
    estilo_texto = ParagraphStyle('N', fontSize=10)

    # Encabezado
    elements.append(Paragraph(f"REPORTE DE CIERRE DIARIO - {fecha}", estilo_h1))
    elements.append(Paragraph(f"Generado por: {st.session_state.username}", estilo_texto))
    elements.append(Paragraph(f"Fecha/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_texto))
    elements.append(Spacer(1, 10))

    # --- SECCIÓN 1: RESUMEN FINANCIERO ---
    elements.append(Paragraph("1. Resumen de Ingresos", estilo_h2))
    data_pagos = [["Medio de Pago", "Total Recaudado"]]
    for _, row in df_pagos.iterrows():
        data_pagos.append([str(row['medio_pago']), f"${row['total']:,.2f}"])
    
    t_pagos = Table(data_pagos, colWidths=[80, 100])
    t_pagos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black)
    ]))
    elements.append(t_pagos)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Efectivo Esperado:</b> ${efectivo_esp:,.2f}", estilo_texto))
    elements.append(Paragraph(f"<b>Efectivo Contado:</b> ${contado:,.2f}", estilo_texto))
    elements.append(Paragraph(f"<b>Diferencia:</b> ${contado - efectivo_esp:,.2f}", estilo_texto))

    # --- SECCIÓN 2: ALERTAS DE STOCK ---
    elements.append(Paragraph("2. Alertas de Inventario (Bajo Mínimo)", estilo_h2))
    if not df_stock_bajo.empty:
        data_stock = [["Producto", "Stock Actual", "Mínimo"]]
        for _, row in df_stock_bajo.iterrows():
            data_stock.append([row['nombre'], str(row['stock']), str(row['stock_minimo'])])
        
        t_stock = Table(data_stock, colWidths=[200, 80, 80])
        t_stock.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.indianred),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black)
        ]))
        elements.append(t_stock)
    else:
        elements.append(Paragraph("No hay productos bajo el nivel crítico.", estilo_texto))

    # --- SECCIÓN 3: DETALLE DE VENTAS ---
    elements.append(Paragraph("3. Detalle de Operaciones", estilo_h2))
    data_v = [["Ticket", "Hora", "Total", "Medio"]]
    for _, row in df_ventas.iterrows():
        hora = row['fecha'].strftime('%H:%M')
        data_v.append([f"#{row['ticket_num']}", hora, f"${row['total']:.2f}", row['medio_pago']])
    
    t_v = Table(data_v, colWidths=[60, 60, 100, 100])
    t_v.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8)]))
    elements.append(t_v)

    doc.build(elements)
    return buffer.getvalue()

# --- LÓGICA DE INTERFAZ ---
engine = get_engine()
hoy = pd.Timestamp.now().date()

# Consultas de Datos
df_pagos = pd.read_sql(f"SELECT medio_pago, SUM(total) as total FROM ventas WHERE fecha >= '{hoy}' GROUP BY medio_pago", engine)
df_detalles = pd.read_sql(f"SELECT ticket_num, fecha, total, medio_pago FROM ventas WHERE fecha >= '{hoy}' ORDER BY ticket_num ASC", engine)
df_alertas = pd.read_sql("SELECT nombre, stock, stock_minimo FROM productos WHERE stock <= stock_minimo", engine)

if df_detalles.empty:
    st.info("Aún no hay ventas registradas para el cierre de hoy.")
else:
    st.subheader(f"Balance del día: {hoy.strftime('%d/%m/%Y')}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(df_pagos, use_container_width=True)
    with c2:
        efectivo_esp = df_pagos[df_pagos['medio_pago'] == 'Efectivo']['total'].sum() if 'Efectivo' in df_pagos['medio_pago'].values else 0
        st.metric("💵 Efectivo en Caja Esperado", f"${efectivo_esp:,.2f}")

    st.divider()
    
    # Formulario de Cierre
    with st.container():
        st.write("### 📝 Confirmación de Cierre")
        contado = st.number_input("Monto total de EFECTIVO contado físicamente", min_value=0.0, step=100.0)
        
        if st.button("🚀 GENERAR CIERRE Y PDF", type="primary", use_container_width=True):
            pdf_bin = generar_reporte_cierre_pdf(df_pagos, df_detalles, df_alertas, efectivo_esp, contado, hoy)
            st.session_state.reporte_cierre_bin = pdf_bin
            st.success("✅ Reporte generado exitosamente.")

# --- BOTÓN DE DESCARGA ---
if st.session_state.reporte_cierre_bin:
    st.balloons()
    st.download_button(
        label="📥 DESCARGAR REPORTE DE CIERRE (PDF)",
        data=st.session_state.reporte_cierre_bin,
        file_name=f"cierre_caja_{hoy}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    if st.button("Limpiar Pantalla"):
        st.session_state.reporte_cierre_bin = None
        st.rerun()
