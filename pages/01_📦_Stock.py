import streamlit as st
import pandas as pd
from database import get_connection
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

# Validar sesión al principio de cada página
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📋 Stock Actual")

def export_stock_to_pdf(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>REPORTE DE STOCK</b>", styles['Title']))
    
    data = [["Producto", "Categoría", "P. Venta", "Stock", "Mínimo"]]
    for _, r in df.iterrows():
        data.append([r['nombre'], r['categoria'], f"${r['precio_venta']:.2f}", str(r['stock']), str(r['stock_minimo'])])
    
    t = Table(data, colWidths=[60*mm, 40*mm, 25*mm, 20*mm, 25*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.black)
    ]))
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

conn = get_connection()
df = pd.read_sql_query("SELECT nombre, categoria, precio_venta, stock, stock_minimo FROM productos ORDER BY nombre", conn)
conn.close()

if df.empty:
    st.warning("No hay productos.")
else:
    st.dataframe(df, use_container_width=True)
    if st.button("📄 Exportar PDF"):
        pdf_data = export_stock_to_pdf(df)
        st.download_button("Descargar PDF", pdf_data, "stock.pdf", "application/pdf")
