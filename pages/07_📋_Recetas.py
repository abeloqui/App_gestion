import streamlit as st
import pandas as pd
from database import get_connection, get_engine
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime

st.set_page_config(page_title="Gestión de Recetas", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("📋 Gestión de Recetas Avanzada")
st.markdown("Unidades de medida + Historial de producciones")

engine = get_engine()

# Productos elaborables
df_platos = pd.read_sql("""
    SELECT id, nombre, subcategoria, precio_costo 
    FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final')
    ORDER BY nombre
""", engine)

if df_platos.empty:
    st.error("No hay productos como Preelaborado o Producto Final.")
    st.stop()

plato_seleccionado = st.selectbox("🔍 Selecciona el producto", df_platos['nombre'].tolist())
plato_row = df_platos[df_platos['nombre'] == plato_seleccionado].iloc[0]
plato_id = int(plato_row['id'])
precio_costo_actual = float(plato_row.get('precio_costo', 0) or 0)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    cantidad_producir = st.number_input("Cantidad a producir", min_value=0.1, value=1.0, step=0.1)
with col2:
    rinde_por_unidad = st.number_input("Rinde (unidades por 1 kg/lote)", min_value=1, value=1, step=1)
with col3:
    unidad_principal = st.selectbox("Unidad principal", ["kg", "unidades", "litros"], index=0)

# ====================== RECETA CON UNIDADES ======================
df_receta = pd.read_sql("""
    SELECT 
        r.id as receta_id,
        i.nombre as insumo,
        i.precio_costo,
        r.cantidad as cantidad_base,
        r.unidad,
        i.subcategoria
    FROM recetas r
    JOIN productos i ON r.insumo_id = i.id
    WHERE r.plato_id = %s AND r.insumo_id IS NOT NULL
    ORDER BY i.nombre
""", engine, params=(plato_id,))

# Cargar notas
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT notas FROM recetas WHERE plato_id = %s AND insumo_id IS NULL LIMIT 1", (plato_id,))
notas = cur.fetchone()
notas = notas[0] if notas else ""
cur.close()
conn.close()

# Cálculos
if not df_receta.empty:
    df_receta['cantidad_necesaria'] = (df_receta['cantidad_base'] * cantidad_producir).round(4)
    df_receta['costo_insumo'] = (df_receta['cantidad_necesaria'] * df_receta['precio_costo']).round(2)
    costo_total = df_receta['costo_insumo'].sum()
    costo_por_unidad = costo_total / cantidad_producir if cantidad_producir > 0 else 0
    unidades_totales = cantidad_producir * rinde_por_unidad
else:
    costo_total = costo_por_unidad = unidades_totales = 0

# ====================== PDF MEJORADO ======================
def generar_receta_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('Titulo', parent=styles['Title'], fontSize=18)

    elements.append(Paragraph(f"RECETA: {plato_seleccionado.upper()}", titulo_style))
    elements.append(Paragraph(f"Cantidad: {cantidad_producir:.2f} {unidad_principal} | Rinde: {unidades_totales:.0f} unidades", styles['Normal']))
    elements.append(Spacer(1, 15))

    if not df_receta.empty:
        data = [["Insumo", "Cantidad", "Unidad", "Costo Total"]]
        for _, row in df_receta.iterrows():
            data.append([row['insumo'], f"{row['cantidad_necesaria']:.3f}", row['unidad'] or 'kg', f"${row['costo_insumo']:.2f}"])
        
        t = Table(data, colWidths=[180, 80, 60, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        elements.append(t)

        elements.append(Spacer(1, 15))
        elements.append(Paragraph(f"<b>Costo Total: ${costo_total:.2f}</b>", styles['Heading2']))

    if notas:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>INSTRUCCIONES:</b>", styles['Heading3']))
        elements.append(Paragraph(notas.replace("\n", "<br/>"), styles['Normal']))

    doc.build(elements)
    return buffer.getvalue()

# ====================== VISUAL ======================
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Costo Total", f"${costo_total:.2f}")
c2.metric("Costo por Unidad", f"${costo_por_unidad:.3f}")
c3.metric("Unidades Estimadas", f"{unidades_totales:.0f}")
c4.metric("Costo Actual", f"${precio_costo_actual:.2f}")

# Instrucciones
st.divider()
st.subheader("📝 Instrucciones y Notas")
notas_nuevas = st.text_area("Pasos, temperatura, tiempo, tips...", value=notas, height=120)
if st.button("💾 Guardar Instrucciones"):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM recetas WHERE plato_id = %s AND insumo_id IS NULL", (plato_id,))
        if notas_nuevas.strip():
            cur.execute("INSERT INTO recetas (plato_id, insumo_id, cantidad, notas) VALUES (%s, NULL, 0, %s)", (plato_id, notas_nuevas))
        conn.commit()
        st.success("Instrucciones guardadas")
        st.rerun()
    finally:
        cur.close()
        conn.close()

# ====================== AGREGAR INGREDIENTE CON UNIDAD ======================
st.divider()
st.subheader("Agregar / Editar Ingrediente")

with st.form("form_ingrediente", clear_on_submit=True):
    df_insumos_posibles = pd.read_sql("""
        SELECT id, nombre FROM productos 
        WHERE subcategoria IN ('Materia Prima', 'Preelaborado')
        ORDER BY nombre
    """, engine)
    
    insumo_sel = st.selectbox("Insumo", df_insumos_posibles['nombre'].tolist())
    cantidad_base = st.number_input("Cantidad base (por 1 unidad producida)", min_value=0.0001, step=0.001, format="%.4f")
    unidad_sel = st.selectbox("Unidad de medida", ["kg", "g", "unidades", "litros", "cucharadas", "cucharaditas"], index=0)
    
    if st.form_submit_button("💾 Agregar / Actualizar", type="primary"):
        ins_id = int(df_insumos_posibles[df_insumos_posibles['nombre'] == insumo_sel]['id'].values[0])
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO recetas (plato_id, insumo_id, cantidad, unidad)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (plato_id, insumo_id) 
                DO UPDATE SET cantidad = EXCLUDED.cantidad, unidad = EXCLUDED.unidad
            """, (plato_id, ins_id, cantidad_base, unidad_sel))
            conn.commit()
            st.success(f"✅ {insumo_sel} ({cantidad_base} {unidad_sel}) guardado")
            st.rerun()
        finally:
            cur.close()
            conn.close()

# Mostrar receta actual con unidades
if not df_receta.empty:
    st.dataframe(
        df_receta[['insumo', 'cantidad_base', 'unidad', 'subcategoria']],
        column_config={
            "cantidad_base": "Cantidad por 1 unidad",
            "unidad": "Unidad"
        },
        use_container_width=True,
        hide_index=True
    )

# ====================== HISTORIAL DE PRODUCCIONES ======================
st.divider()
st.subheader("📊 Historial de Producciones de esta Receta")

df_historial = pd.read_sql("""
    SELECT 
        fecha,
        cantidad as cantidad_producida,
        total as costo_total_registrado
    FROM movimientos 
    WHERE tipo = 'produccion' 
      AND producto_id = %s
    ORDER BY fecha DESC
    LIMIT 20
""", engine, params=(plato_id,))

if df_historial.empty:
    st.info("Aún no hay producciones registradas para este producto.")
else:
    st.dataframe(
        df_historial,
        column_config={
            "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
            "cantidad_producida": "Cantidad Producida",
            "costo_total_registrado": st.column_config.NumberColumn("Costo Total ($)", format="$%.2f")
        },
        use_container_width=True,
        hide_index=True
    )

# ====================== ACCIONES ======================
st.divider()
col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("📄 Exportar Receta a PDF", type="primary", use_container_width=True):
        pdf_bytes = generar_receta_pdf()
        st.download_button("⬇️ Descargar PDF", pdf_bytes,
                          f"Receta_{plato_seleccionado.replace(' ','_')}.pdf", "application/pdf", use_container_width=True)

with col_b:
    if st.button("👩‍🍳 Registrar Producción", type="primary", use_container_width=True):
        if df_receta.empty:
            st.error("Agrega ingredientes primero.")
        else:
            conn = get_connection()
            cur = conn.cursor()
            try:
                for _, row in df_receta.iterrows():
                    insumo_id_df = pd.read_sql("SELECT id FROM productos WHERE nombre = %s", engine, params=(row['insumo'],))
                    insumo_id = int(insumo_id_df.iloc[0]['id'])
                    cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", 
                               (float(row['cantidad_necesaria']), insumo_id))
                
                cur.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", 
                           (float(cantidad_producir), plato_id))
                
                cur.execute("""
                    INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total)
                    VALUES ('produccion', %s, %s, %s, %s)
                """, (plato_id, float(cantidad_producir), costo_por_unidad, costo_total))
                
                conn.commit()
                st.success(f"Producción registrada: +{cantidad_producir:.2f} {unidad_principal} de {plato_seleccionado}")
                st.balloons()
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"Error: {e}")
            finally:
                cur.close()
                conn.close()

with col_c:
    if st.button("📋 Duplicar Receta", use_container_width=True):
        st.info("Funcionalidad de duplicar disponible en versión anterior. ¿Querés que la mantengamos?")

st.caption("💡 Las unidades se guardan por ingrediente. El sistema no convierte automáticamente entre unidades todavía (próxima mejora).")
