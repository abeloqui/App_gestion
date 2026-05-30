import streamlit as st
import pandas as pd
from database import get_connection, get_engine
from datetime import datetime
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






st.header("🏁 Cierre de Caja y Reporte Diario")

if "reporte_cierre_bin" not in st.session_state:
    st.session_state.reporte_cierre_bin = None

engine = get_engine()
conn = get_connection()
cur = conn.cursor()

# Crear tabla cierres si no existe
cur.execute('''CREATE TABLE IF NOT EXISTS cierres (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_ventas FLOAT DEFAULT 0,
    total_efectivo FLOAT DEFAULT 0,
    total_transferencia FLOAT DEFAULT 0,
    total_tarjeta FLOAT DEFAULT 0,
    efectivo_contado FLOAT DEFAULT 0,
    diferencia FLOAT DEFAULT 0,
    usuario TEXT DEFAULT 'admin'
)''')
conn.commit()

# Obtener fecha del último cierre
cur.execute("SELECT MAX(fecha) FROM cierres")
ultimo_cierre = cur.fetchone()[0]
conn.close()

if ultimo_cierre:
    desde = f"'{ultimo_cierre}'"
    st.caption(f"📅 Mostrando ventas desde el último cierre: {ultimo_cierre.strftime('%d/%m/%Y %H:%M')}")
else:
    desde = "'2000-01-01'"
    st.caption("📅 No hay cierres previos — mostrando todas las ventas.")

def generar_pdf(df_pagos, df_ventas, df_stock_bajo, efectivo_esp, contado, desde_label):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('H1', fontSize=16, alignment=1, spaceAfter=15, fontName="Helvetica-Bold")
    h2 = ParagraphStyle('H2', fontSize=12, spaceBefore=12, spaceAfter=8, fontName="Helvetica-Bold")
    normal = ParagraphStyle('N', fontSize=10)

    elements.append(Paragraph("CIERRE DE CAJA — DULCE JAZMÍN", h1))
    elements.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal))
    elements.append(Paragraph(f"Usuario: {st.session_state.username}", normal))
    elements.append(Paragraph(f"Período: desde {desde_label}", normal))
    elements.append(Spacer(1, 10))

    # Resumen por medio de pago
    elements.append(Paragraph("Ingresos por Medio de Pago", h2))
    data_pagos = [["Medio de Pago", "Cantidad", "Total"]]
    for _, row in df_pagos.iterrows():
        data_pagos.append([row['medio_pago'], str(int(row['cantidad'])), f"${row['total']:,.2f}"])
    data_pagos.append(["TOTAL", str(int(df_pagos['cantidad'].sum())), f"${df_pagos['total'].sum():,.2f}"])
    t = Table(data_pagos, colWidths=[150, 80, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    diferencia = contado - efectivo_esp
    elements.append(Paragraph(f"<b>Efectivo esperado:</b> ${efectivo_esp:,.2f}", normal))
    elements.append(Paragraph(f"<b>Efectivo contado:</b> ${contado:,.2f}", normal))
    color_dif = "red" if diferencia < 0 else "green"
    elements.append(Paragraph(f'<b>Diferencia:</b> <font color="{color_dif}">${diferencia:,.2f}</font>', normal))
    elements.append(Spacer(1, 10))

    # Alertas stock
    elements.append(Paragraph("Alertas de Stock Bajo Mínimo", h2))
    if not df_stock_bajo.empty:
        data_stock = [["Producto", "Cantidad", "Mínimo", "Unidad"]]
        for _, row in df_stock_bajo.iterrows():
            data_stock.append([row['nombre'], str(row['stock']), str(row['stock_minimo']), row.get('unidad', '-')])
        ts = Table(data_stock, colWidths=[160, 70, 70, 70])
        ts.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.indianred),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ]))
        elements.append(ts)
    else:
        elements.append(Paragraph("✅ Sin productos bajo el mínimo.", normal))

    # Detalle ventas
    if not df_ventas.empty:
        elements.append(Paragraph("Detalle de Ventas", h2))
        data_v = [["#", "Hora", "Total", "Medio de Pago"]]
        for i, row in df_ventas.iterrows():
            hora = row['fecha'].strftime('%H:%M') if hasattr(row['fecha'], 'strftime') else str(row['fecha'])
            data_v.append([str(i+1), hora, f"${row['total']:.2f}", row['medio_pago']])
        tv = Table(data_v, colWidths=[30, 60, 100, 100])
        tv.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        elements.append(tv)

    doc.build(elements)
    return buffer.getvalue()

# --- CARGAR DATOS DESDE ÚLTIMO CIERRE ---
df_pagos = pd.read_sql(f"""
    SELECT medio_pago, SUM(total) as total, COUNT(*) as cantidad
    FROM ventas
    WHERE fecha > {desde}
    GROUP BY medio_pago
""", engine)

df_ventas = pd.read_sql(f"""
    SELECT id, fecha, total, medio_pago
    FROM ventas
    WHERE fecha > {desde}
    ORDER BY fecha ASC
""", engine)

df_alertas = pd.read_sql("""
    SELECT nombre, stock, stock_minimo, unidad
    FROM productos WHERE stock <= stock_minimo
""", engine)

# --- INTERFAZ ---
if df_ventas.empty:
    st.info("No hay ventas registradas desde el último cierre.")
else:
    total_dia = float(df_pagos['total'].sum())
    efectivo_esp = float(df_pagos[df_pagos['medio_pago'] == 'Efectivo']['total'].sum()) if 'Efectivo' in df_pagos['medio_pago'].values else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total del Período", f"${total_dia:,.2f}")
    c2.metric("🧾 Ventas", len(df_ventas))
    c3.metric("💵 Efectivo Esperado", f"${efectivo_esp:,.2f}")

    st.divider()
    st.dataframe(df_pagos[['medio_pago', 'cantidad', 'total']], use_container_width=True, hide_index=True)

    if not df_alertas.empty:
        st.divider()
        st.error(f"⚠️ {len(df_alertas)} producto(s) bajo el mínimo.")
        st.dataframe(df_alertas, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📝 Confirmación de Cierre")
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
        # Registrar el cierre en la BD
        conn2 = get_connection()
        cur2 = conn2.cursor()
        try:
            total_transf = float(df_pagos[df_pagos['medio_pago'] == 'Transferencia']['total'].sum()) if 'Transferencia' in df_pagos['medio_pago'].values else 0.0
            total_tarj = float(df_pagos[df_pagos['medio_pago'] == 'Tarjeta']['total'].sum()) if 'Tarjeta' in df_pagos['medio_pago'].values else 0.0

            cur2.execute("""
                INSERT INTO cierres (total_ventas, total_efectivo, total_transferencia, total_tarjeta, efectivo_contado, diferencia, usuario)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (total_dia, efectivo_esp, total_transf, total_tarj, float(contado), float(diferencia), st.session_state.username))
            conn2.commit()

            desde_label = ultimo_cierre.strftime('%d/%m/%Y %H:%M') if ultimo_cierre else "el inicio"
            pdf_bin = generar_pdf(df_pagos, df_ventas, df_alertas, efectivo_esp, contado, desde_label)
            st.session_state.reporte_cierre_bin = pdf_bin
            st.success("✅ Cierre registrado. Las ventas del próximo período se contarán desde ahora.")
        except Exception as e:
            conn2.rollback()
            st.error(f"Error al registrar el cierre: {e}")
        finally:
            conn2.close()

if st.session_state.reporte_cierre_bin:
    st.download_button(
        "📥 DESCARGAR REPORTE PDF",
        st.session_state.reporte_cierre_bin,
        file_name=f"cierre_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.balloons()
    if st.button("🧹 Limpiar Pantalla"):
        st.session_state.reporte_cierre_bin = None
        st.rerun()

# Historial de cierres (solo admin)
if st.session_state.rol == 'admin':
    st.divider()
    st.subheader("📋 Historial de Cierres")
    df_hist = pd.read_sql("""
        SELECT fecha, total_ventas, total_efectivo, total_transferencia,
               total_tarjeta, efectivo_contado, diferencia, usuario
        FROM cierres ORDER BY fecha DESC LIMIT 10
    """, engine)
    if df_hist.empty:
        st.info("Sin cierres registrados aún.")
    else:
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
