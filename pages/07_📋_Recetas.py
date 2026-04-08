import streamlit as st
import pandas as pd
from database import get_connection, get_engine
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime

st.set_page_config(page_title="Gestión de Recetas", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📋 Gestión de Recetas")
st.markdown("Define los insumos necesarios y exporta las recetas a PDF.")

engine = get_engine()

# Cargar productos
df_platos = pd.read_sql("""
    SELECT id, nombre, subcategoria 
    FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final')
    ORDER BY nombre
""", engine)

df_insumos = pd.read_sql("""
    SELECT id, nombre 
    FROM productos 
    WHERE subcategoria = 'Materia Prima'
    ORDER BY nombre
""", engine)

if df_platos.empty:
    st.error("No hay productos configurados como Preelaborado o Producto Final.")
    st.stop()

plato_seleccionado = st.selectbox("🔍 Selecciona el producto", df_platos['nombre'].tolist())
plato_id = int(df_platos[df_platos['nombre'] == plato_seleccionado]['id'].values[0])
subcat = df_platos[df_platos['nombre'] == plato_seleccionado]['subcategoria'].values[0]

st.subheader(f"Receta: **{plato_seleccionado}** ({subcat})")

# Cargar receta actual
df_receta = pd.read_sql("""
    SELECT 
        r.id as receta_id,
        i.nombre as insumo,
        r.cantidad
    FROM recetas r
    JOIN productos i ON r.insumo_id = i.id
    WHERE r.plato_id = %s
    ORDER BY i.nombre
""", engine, params=(plato_id,))

# ====================== EXPORTAR A PDF ======================
def generar_receta_pdf(plato_nombre, df_receta_actual):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"<b>RECETA: {plato_nombre.upper()}</b>", styles['Title']))
    elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    if not df_receta_actual.empty:
        data = [["Insumo (Materia Prima)", "Cantidad"]]
        for _, row in df_receta_actual.iterrows():
            data.append([row['insumo'], f"{row['cantidad']:.3f}"])

        t = Table(data, colWidths=[300, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 10),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("Esta receta aún no tiene insumos definidos.", styles['Normal']))

    doc.build(elements)
    return buffer.getvalue()

# Botón de exportar (siempre visible)
if st.button("📄 Exportar esta receta a PDF", type="primary", use_container_width=True):
    if df_receta.empty:
        st.warning("No hay nada para exportar aún.")
    else:
        pdf_bytes = generar_receta_pdf(plato_seleccionado, df_receta)
        st.download_button(
            label="⬇️ Descargar PDF",
            data=pdf_bytes,
            file_name=f"Receta_{plato_seleccionado.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

st.divider()

# ====================== EDICIÓN DE RECETA ======================
tab1, tab2 = st.tabs(["✏️ Editar Receta", "📋 Ver Todas las Recetas"])

with tab1:
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("Agregar / Modificar Insumo")
        with st.form("form_insumo", clear_on_submit=True):
            insumo_sel = st.selectbox("Insumo (Materia Prima)", df_insumos['nombre'].tolist() if not df_insumos.empty else ["Sin insumos"])
            cant = st.number_input("Cantidad por unidad producida", min_value=0.001, step=0.001, format="%.3f")
            
            if st.form_submit_button("💾 Agregar / Actualizar Insumo", type="primary"):
                if insumo_sel and cant > 0:
                    ins_id = int(df_insumos[df_insumos['nombre'] == insumo_sel]['id'].values[0])
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO recetas (plato_id, insumo_id, cantidad)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (plato_id, insumo_id) DO UPDATE SET cantidad = EXCLUDED.cantidad
                        """, (plato_id, ins_id, cant))
                        conn.commit()
                        st.success(f"✅ {insumo_sel} actualizado ({cant})")
                        st.rerun()
                    finally:
                        cur.close()
                        conn.close()

    with col2:
        st.subheader("Receta Actual")
        if df_receta.empty:
            st.info("Esta receta aún no tiene insumos.")
        else:
            for _, row in df_receta.iterrows():
                cols = st.columns([5, 2, 1])
                with cols[0]:
                    st.write(f"**{row['insumo']}**")
                with cols[1]:
                    st.write(f"{row['cantidad']:.3f}")
                with cols[2]:
                    if st.button("🗑️", key=f"del_{row['receta_id']}", help="Eliminar"):
                        conn = get_connection()
                        cur = conn.cursor()
                        try:
                            cur.execute("DELETE FROM recetas WHERE id = %s", (int(row['receta_id']),))
                            conn.commit()
                            st.rerun()
                        finally:
                            cur.close()
                            conn.close()
                st.divider()

with tab2:
    st.subheader("Todas las Recetas del Sistema")
    df_todas = pd.read_sql("""
        SELECT 
            p.nombre as plato,
            p.subcategoria,
            i.nombre as insumo,
            r.cantidad
        FROM recetas r
        JOIN productos p ON r.plato_id = p.id
        JOIN productos i ON r.insumo_id = i.id
        ORDER BY p.nombre, i.nombre
    """, engine)

    if df_todas.empty:
        st.info("Aún no hay recetas cargadas.")
    else:
        for plato in df_todas['plato'].unique():
            st.write(f"**{plato}**")
            df_p = df_todas[df_todas['plato'] == plato][['insumo', 'cantidad']]
            st.dataframe(df_p, use_container_width=True, hide_index=True)
            st.divider()
