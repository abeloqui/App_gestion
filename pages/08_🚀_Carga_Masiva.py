import streamlit as st
from database import get_connection

st.title("🔄 Corrección de Subcategoría - Golosinas como Materia Prima")

productos_a_corregir = [
    "Bolsa de Mini Oreo (150gr)",
    "Bon o bon (15g)",
    "Chocolate Cadbury frutilla (29g)",
    "Chocolate Marroc (14g)",
    "Chocolinas (170gr)",
    "Chocolinas (250gr)",
    "Ferrero Roche (250gr)",
    "Ferrero Roche (300gr)",
    "Jugo Baggio (200ml)",
    "Kinder Bueno (42g)",
    "Kinder común (12,5g)",
    "Kit kat (42g)",
    "Mantecol (235gr)",
    "Oreo (350gr)",
    "Vocación (140gr)"
]

if st.button("🚀 Cambiar estos productos a **Materia Prima**", type="primary"):
    conn = get_connection()
    cur = conn.cursor()
    actualizados = 0
    
    for nombre in productos_a_corregir:
        try:
            cur.execute("""
                UPDATE productos 
                SET subcategoria = 'Materia Prima',
                    es_producido = FALSE
                WHERE nombre = %s
            """, (nombre,))
            actualizados += cur.rowcount
        except Exception as e:
            st.error(f"Error con {nombre}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    st.success(f"✅ ¡Listo! Se actualizaron {actualizados} productos a **Materia Prima**.")
    st.info("Ahora ve a la página de Stock para verificar que aparezcan en la pestaña de Materia Prima.")

st.warning("Este cambio solo afecta los productos listados arriba. Los demás se mantienen como estaban.")
