import streamlit as st
import pandas as pd
from database import get_connection
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📋 Stock Actual - Fraccionado")

def export_stock_to_pdf(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>REPORTE DE STOCK - DULCE JAZMÍN</b>", styles['Title']))
    
    data = [["Producto", "Categoría", "Subcategoría", "P. Venta", "Stock", "Mínimo"]]
    for _, r in df.iterrows():
        data.append([r['nombre'], r['categoria'], r['subcategoria'], 
                     f"${r['precio_venta']:.2f}", str(r['stock']), str(r['stock_minimo'])])
    
    t = Table(data, colWidths=[50*mm, 30*mm, 30*mm, 25*mm, 20*mm, 25*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.black)
    ]))
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

conn = get_connection()
df = pd.read_sql_query("""
    SELECT nombre, categoria, subcategoria, precio_venta, stock, stock_minimo 
    FROM productos 
    ORDER BY subcategoria, nombre
""", conn)
conn.close()

if df.empty:
    st.warning("No hay productos.")
else:
    st.subheader("Stock Fraccionado por Tipo")
    tab_mp, tab_pre, tab_final = st.tabs(["📦 Materia Prima", "🔧 Preelaborado", "🏷️ Producto Final"])
    
    for tab, subtipo in zip([tab_mp, tab_pre, tab_final], ["Materia Prima", "Preelaborado", "Producto Final"]):
        with tab:
            df_f = df[df["subcategoria"] == subtipo]
            if df_f.empty:
                st.info(f"🌟 Aún no hay {subtipo.lower()} en stock.")
            else:
                st.dataframe(df_f[["nombre", "categoria", "precio_venta", "stock", "stock_minimo"]], 
                            use_container_width=True, hide_index=True)
    
    st.divider()
    if st.button("📄 Exportar PDF (todo el stock)"):
        pdf_data = export_stock_to_pdf(df)
        st.download_button("Descargar PDF", pdf_data, "stock_completo.pdf", "application/pdf")
