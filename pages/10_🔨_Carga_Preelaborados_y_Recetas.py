import streamlit as st
from database import get_connection

st.set_page_config(page_title="Carga Completa - Preelaborados, Finales y Recetas", layout="centered")

st.title("🔨 Carga Completa: Preelaborados + Productos Finales + Recetas Preset")
st.info("Esto creará productos de prueba y varias recetas listas para usar.")

if st.button("🚀 Ejecutar Carga Completa", type="primary", use_container_width=True):
    conn = get_connection()
    cur = conn.cursor()
    success_prod = 0
    success_rec = 0

    # ====================== 1. PRODUCTOS ======================
    productos = [
        # Preelaborados
        ("Masa Base para Cookies", "Reposteria", "Preelaborado", 0, 0, 0, 10),
        ("Masa Base para Brownies", "Reposteria", "Preelaborado", 0, 0, 0, 8),
        ("Bizcochuelo de Vainilla", "Reposteria", "Preelaborado", 0, 0, 0, 5),
        ("Bizcochuelo de Chocolate", "Reposteria", "Preelaborado", 0, 0, 0, 5),
        ("Crema Pastelera", "Reposteria", "Preelaborado", 0, 0, 0, 15),
        ("Crema de Chocolate", "Reposteria", "Preelaborado", 0, 0, 0, 12),
        ("Ganache de Chocolate", "Reposteria", "Preelaborado", 0, 0, 0, 10),

        # Productos Finales
        ("Cookies con Chips de Chocolate", "Reposteria", "Producto Final", 4500, 0, 20, 5),
        ("Brownies con Nueces", "Reposteria", "Producto Final", 3800, 0, 15, 5),
        ("Torta de Chocolate Individual", "Reposteria", "Producto Final", 6500, 0, 10, 3),
        ("Postre de Oreo en Vasito", "Reposteria", "Producto Final", 2800, 0, 12, 5),
        ("Alfajor de Maicena (unidad)", "Reposteria", "Producto Final", 1200, 0, 30, 10),
        ("Tiramisú en Copa", "Reposteria", "Producto Final", 3500, 0, 15, 5),
    ]

    for nombre, cat, subcat, p_venta, p_costo, stock, stock_min in productos:
        try:
            cur.execute("""
                INSERT INTO productos (nombre, categoria, subcategoria, precio_venta, precio_costo, stock, stock_minimo, es_producido)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (nombre) DO UPDATE SET 
                    subcategoria = EXCLUDED.subcategoria,
                    precio_venta = EXCLUDED.precio_venta,
                    es_producido = TRUE
            """, (nombre, cat, subcat, p_venta, p_costo, stock, stock_min, subcat != "Materia Prima"))
            success_prod += 1
        except:
            pass

    # ====================== 2. RECETAS PRESET ======================
    recetas_preset = [
        # Masa Base para Cookies
        ("Masa Base para Cookies", "Harina 000 (1kg)", 0.420, "kg"),
        ("Masa Base para Cookies", "Manteca (5kg)", 0.225, "kg"),
        ("Masa Base para Cookies", "Azúcar (1kg)", 0.330, "kg"),
        ("Masa Base para Cookies", "Huevos (150 unidades)", 0.100, "kg"),
        ("Masa Base para Cookies", "Esencia de Vainilla (2lts)", 0.010, "kg"),

        # Cookies con Chips
        ("Cookies con Chips de Chocolate", "Masa Base para Cookies", 1.000, "kg"),
        ("Cookies con Chips de Chocolate", "Chip de Chocolate negro (500gr)", 0.240, "kg"),

        # Brownies
        ("Brownies con Nueces", "Masa Base para Brownies", 1.000, "kg"),
        ("Brownies con Nueces", "Nueces (5kg)", 0.150, "kg"),

        # Tiramisú
        ("Tiramisú en Copa", "Crema de Chocolate", 0.300, "kg"),
        ("Tiramisú en Copa", "Café instantáneo (160gr)", 0.020, "kg"),
        ("Tiramisú en Copa", "Leche condensada (395gr)", 0.100, "kg"),
        ("Tiramisú en Copa", "Bizcochuelo de Vainilla", 0.080, "kg"),

        # Postre de Oreo
        ("Postre de Oreo en Vasito", "Oreo (350gr)", 0.150, "kg"),
        ("Postre de Oreo en Vasito", "Crema Pastelera", 0.250, "kg"),
    ]

    for plato_nom, insumo_nom, cantidad, unidad in recetas_preset:
        try:
            # Obtener IDs
            cur.execute("SELECT id FROM productos WHERE nombre = %s", (plato_nom,))
            plato_id = cur.fetchone()[0]
            
            cur.execute("SELECT id FROM productos WHERE nombre = %s", (insumo_nom,))
            insumo_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO recetas (plato_id, insumo_id, cantidad, unidad)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (plato_id, insumo_id) 
                DO UPDATE SET cantidad = EXCLUDED.cantidad, unidad = EXCLUDED.unidad
            """, (plato_id, insumo_id, cantidad, unidad))
            success_rec += 1
        except:
            pass

    # Agregar algunas instrucciones de ejemplo
    instrucciones_ejemplo = """
Pasos de elaboración:
1. Mezclar ingredientes secos
2. Incorporar manteca a temperatura ambiente
3. Hornear a 180°C por 12-15 minutos
4. Dejar enfriar antes de decorar

Consejo: No sobremezclar la masa para mantener textura suave.
    """

    try:
        cur.execute("SELECT id FROM productos WHERE nombre = %s", ("Cookies con Chips de Chocolate",))
        plato_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO recetas (plato_id, insumo_id, cantidad, notas)
            VALUES (%s, NULL, 0, %s)
            ON CONFLICT (plato_id, insumo_id) DO UPDATE SET notas = EXCLUDED.notas
        """, (plato_id, instrucciones_ejemplo))
    except:
        pass

    conn.commit()
    cur.close()
    conn.close()

    st.success(f"""
    ¡Carga completa exitosa!
    
    ✅ {success_prod} productos creados/actualizados
    ✅ {success_rec} líneas de receta cargadas
    """)
    
    st.balloons()
    st.info("Ahora puedes ir a la página **Gestión de Recetas** y probar todo el flujo.")

else:
    st.write("Presiona el botón para cargar los productos de prueba y las recetas preset.")
    st.caption("""
    Se cargarán:
    - 7 Preelaborados (bases)
    - 6 Productos Finales
    - Recetas completas para Cookies, Brownies, Tiramisú y Postre de Oreo
    """)
