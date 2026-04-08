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
st.markdown("Define las recetas y calcula insumos necesarios según la cantidad a producir.")

engine = get_engine()

# Solo mostramos productos que se pueden elaborar (Preelaborado y Producto Final)
df_platos = pd.read_sql("""
    SELECT id, nombre, subcategoria 
    FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final')
    ORDER BY nombre
""", engine)

if df_platos.empty:
    st.error("No hay productos configurados como Preelaborado o Producto Final.")
    st.stop()

# Selector principal
plato_seleccionado = st.selectbox(
    "🔍 Selecciona el producto a elaborar", 
    df_platos['nombre'].tolist()
)

plato_id = int(df_platos[df_platos['nombre'] == plato_seleccionado]['id'].values[0])
subcat = df_platos[df_platos['nombre'] == plato_seleccionado]['subcategoria'].values[0]

st.subheader(f"Receta para: **{plato_seleccionado}** ({subcat})")

# Cantidad a producir (esto es lo nuevo que pediste)
cantidad_producir = st.number_input(
    "Cantidad a producir (kg o unidades)", 
    min_value=0.1, 
    step=0.1, 
    value=1.0,
    help="Ej: 5 = 5 kg de masa, o 50 unidades de cookies"
)

# Cargar receta base (por unidad)
df_receta_base = pd.read_sql("""
    SELECT 
        i.nombre as insumo,
        r.cantidad as cantidad_por_unidad
    FROM recetas r
    JOIN productos i ON r.insumo_id = i.id
    WHERE r.plato_id = %s
    ORDER BY i.nombre
""", engine, params=(plato_id,))

# Calcular insumos necesarios según cantidad a producir
if not df_receta_base.empty:
    df_receta_base['cantidad_necesaria'] = df_receta_base['cantidad_por_unidad'] * cantidad_producir
    df_receta_base = df_receta_base.round(3)

# ====================== EXPORTAR PDF ======================
def generar_receta_pdf(plato_nombre, cantidad, df_insumos):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"<b>RECETA: {plato_nombre.upper()}</b>", styles['Title']))
    elements.append(Paragraph(f"Cantidad a producir: {cantidad:.2f} kg/unidades", styles['Normal']))
    elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    if not df_insumos.empty:
        data = [["Insumo", "Cantidad Necesaria"]]
        for _, row in df_insumos.iterrows():
            data.append([row['insumo'], f"{row['cantidad_necesaria']:.3f}"])
        
        t = Table(data, colWidths=[280, 120])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 10),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("Esta receta aún no tiene insumos definidos.", styles['Normal']))

    doc.build(elements)
    return buffer.getvalue()

if st.button("📄 Exportar Receta a PDF", type="primary", use_container_width=True):
    if df_receta_base.empty:
        st.warning("Primero debes agregar insumos a esta receta.")
    else:
        pdf_bytes = generar_receta_pdf(plato_seleccionado, cantidad_producir, df_receta_base)
        st.download_button(
            label="⬇️ Descargar PDF",
            data=pdf_bytes,
            file_name=f"Receta_{plato_seleccionado.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

st.divider()

# ====================== EDICIÓN DE RECETA ======================
st.subheader("Editar Receta Base (por 1 unidad)")

col1, col2 = st.columns([3, 2])

with col1:
    with st.form("agregar_insumo", clear_on_submit=True):
        # Solo Materia Prima + Preelaborados como insumos
        df_posibles_insumos = pd.read_sql("""
            SELECT id, nombre FROM productos 
            WHERE subcategoria IN ('Materia Prima', 'Preelaborado')
            ORDER BY nombre
        """, engine)
        
        insumo_sel = st.selectbox("Insumo", df_posibles_insumos['nombre'].tolist())
        cantidad_base = st.number_input("Cantidad por 1 unidad producida", min_value=0.001, step=0.001, format="%.3f")
        
        if st.form_submit_button("💾 Agregar / Actualizar Insumo", type="primary"):
            ins_id = int(df_posibles_insumos[df_posibles_insumos['nombre'] == insumo_sel]['id'].values[0])
            conn = get_connection()
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO recetas (plato_id, insumo_id, cantidad)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (plato_id, insumo_id) DO UPDATE SET cantidad = EXCLUDED.cantidad
                """, (plato_id, ins_id, cantidad_base))
                conn.commit()
                st.success(f"✅ {insumo_sel} guardado")
                st.rerun()
            finally:
                cur.close()
                conn.close()

with col2:
    st.subheader("Receta Base Actual (por 1 unidad)")
    if df_receta_base.empty:
        st.info("Aún no tiene insumos cargados.")
    else:
        st.dataframe(
            df_receta_base[['insumo', 'cantidad_por_unidad']], 
            column_config={"cantidad_por_unidad": "Cantidad por unidad"},
            use_container_width=True, 
            hide_index=True
        )

# Mostrar cálculo según cantidad a producir
if not df_receta_base.empty:
    st.divider()
    st.subheader(f"Insumos necesarios para producir **{cantidad_producir:.2f}** de {plato_seleccionado}")
    st.dataframe(
        df_receta_base[['insumo', 'cantidad_necesaria']], 
        column_config={"cantidad_necesaria": f"Cantidad necesaria para {cantidad_producir:.2f}"},
        use_container_width=True, 
        hide_index=True
    )
