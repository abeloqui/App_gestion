import streamlit as st
from database import get_connection

st.set_page_config(page_title="Carga de Recetas Preset", layout="centered")

st.title("🔄 Carga Inicial de Recetas Preset")
st.info("Esto cargará varias recetas básicas predefinidas usando solo **Materia Prima** como insumos.")

recetas_preset = [
    # (plato_nombre, insumo_nombre, cantidad)
    ("Masa Base para Cookies", "Harina 000 (1kg)", 0.420),
    ("Masa Base para Cookies", "Manteca (5kg)", 0.225),
    ("Masa Base para Cookies", "Azúcar (1kg)", 0.330),
    ("Masa Base para Cookies", "Huevos (150 unidades)", 0.100),
    ("Masa Base para Cookies", "Esencia de Vainilla (2lts)", 0.010),

    ("Cookies con Chips", "Masa Base para Cookies", 1.000),   # ← Preelaborado como insumo
    ("Cookies con Chips", "Chip de Chocolate negro (500gr)", 0.240),

    ("Tiramisú Individual", "Crema de leche (10lts)", 0.150),
    ("Tiramisú Individual", "Leche condensada (395gr)", 0.100),
    ("Tiramisú Individual", "Café instantáneo (160gr)", 0.020),
    ("Tiramisú Individual", "Chocolate Cobertura con Leche (12,8kg)", 0.050),
    ("Tiramisú Individual", "Bizcochuelo", 0.080),   # si tienes bizcochuelo como preelaborado

    ("Budín de Limón", "Harina Leudante (1kg)", 0.350),
    ("Budín de Limón", "Manteca (5kg)", 0.180),
    ("Budín de Limón", "Azúcar (1kg)", 0.250),
    ("Budín de Limón", "Huevos (150 unidades)", 0.120),
    ("Budín de Limón", "Esencia de Vainilla (2lts)", 0.005),
]

if st.button("🚀 Cargar Recetas Preset (15 líneas)", type="primary", use_container_width=True):
    conn = get_connection()
    cur = conn.cursor()
    success = 0

    for plato_nom, insumo_nom, cant in recetas_preset:
        try:
            # Obtener IDs
            cur.execute("SELECT id FROM productos WHERE nombre = %s", (plato_nom,))
            plato_row = cur.fetchone()
            cur.execute("SELECT id FROM productos WHERE nombre = %s", (insumo_nom,))
            insumo_row = cur.fetchone()

            if plato_row and insumo_row:
                plato_id = plato_row[0]
                insumo_id = insumo_row[0]

                cur.execute("""
                    INSERT INTO recetas (plato_id, insumo_id, cantidad)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (plato_id, insumo_id) DO UPDATE SET cantidad = EXCLUDED.cantidad
                """, (plato_id, insumo_id, cant))
                success += 1
        except Exception as e:
            st.warning(f"Error con {plato_nom} + {insumo_nom}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    st.success(f"✅ ¡Carga completada! Se procesaron {success} líneas de receta.")

st.warning("⚠️ Asegúrate de tener creados los productos 'Masa Base para Cookies', 'Cookies con Chips', 'Tiramisú Individual', etc. como Preelaborado o Producto Final antes de cargar.")
