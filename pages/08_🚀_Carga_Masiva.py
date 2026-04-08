import streamlit as st
from database import get_connection

st.set_page_config(page_title="Carga Inicial Dulce Jazmín", layout="centered")

st.title("🚀 Carga Inicial: Dulce Jazmín")
st.info("Este script cargará los 93 productos con el stock actual, mínimo y **subcategoría** (Materia Prima / Producto Final).")

# Datos del PDF con subcategoría agregada
productos_data = [
    ("Manteca (5kg)", 1.0, 0.0, "Materia Prima", "Materia Prima"),
    ("Harina Leudante (1kg)", 95.0, 50.0, "Materia Prima", "Materia Prima"),
    ("Harina 000 (1kg)", 70.0, 50.0, "Materia Prima", "Materia Prima"),
    ("Sobre de levadura (10g)", 25.0, 10.0, "Materia Prima", "Materia Prima"),
    ("Kinder Bueno (42g)", 75.0, 30.0, "Golosinas", "Producto Final"),
    ("Kit kat (42g)", 65.0, 24.0, "Golosinas", "Producto Final"),
    ("Kinder común (12,5g)", 23.0, 24.0, "Golosinas", "Producto Final"),
    ("Bon o bon (15g)", 10.0, 30.0, "Golosinas", "Producto Final"),
    ("Chocolate Cadbury frutilla (29g)", 12.0, 12.0, "Golosinas", "Producto Final"),
    ("Chocolate Marroc (14g)", 50.0, 60.0, "Golosinas", "Producto Final"),
    ("Queso cremoso (3,5kg)", 6.0, 3.0, "Lácteos", "Materia Prima"),
    ("Crema de leche (10lts)", 3.0, 2.0, "Lácteos", "Materia Prima"),
    ("Pasas de Uva (500gr)", 2.0, 1.0, "Frutos Secos", "Materia Prima"),
    ("Chip de Chocolate negro (500gr)", 2.0, 1.0, "Reposteria", "Materia Prima"),
    ("Membrillo (5kg)", 4.0, 2.0, "Reposteria", "Materia Prima"),
    ("Leche entera (1lt)", 15.0, 10.0, "Lácteos", "Materia Prima"),
    ("Yerba (1kg)", 3.0, 1.0, "Almacén", "Materia Prima"),
    ("Mantecol untable (250gr)", 4.0, 1.0, "Reposteria", "Materia Prima"),
    ("Jugo Baggio (200ml)", 18.0, 18.0, "Bebidas", "Producto Final"),
    ("Chocolate Cobertura Blanco (12,8kg)", 1.0, 1.0, "Reposteria", "Materia Prima"),
    ("Chocolate Cobertura con Leche (12,8kg)", 1.0, 1.0, "Reposteria", "Materia Prima"),
    ("Chocolate Cobertura Semi amargo (12,8kg)", 1.0, 1.0, "Reposteria", "Materia Prima"),
    ("Bolsa de Mini Oreo (150gr)", 56.0, 25.0, "Golosinas", "Producto Final"),
    ("Aceite Natura Aerosol (120cc)", 14.0, 6.0, "Materia Prima", "Materia Prima"),
    ("Café instantáneo (160gr)", 2.0, 6.0, "Almacén", "Materia Prima"),
    ("Mantecol (235gr)", 6.0, 2.0, "Golosinas", "Producto Final"),
    ("Avena (350gr)", 10.0, 12.0, "Almacén", "Materia Prima"),
    ("Ferrero Roche (250gr)", 2.0, 1.0, "Golosinas", "Producto Final"),
    ("Ferrero Roche (300gr)", 1.0, 1.0, "Golosinas", "Producto Final"),
    ("Azúcar impalpable (10kg)", 4.0, 2.0, "Materia Prima", "Materia Prima"),
    ("Azúcar Rubia (10kg)", 3.0, 1.0, "Materia Prima", "Materia Prima"),
    ("Nueces (5kg)", 2.0, 1.0, "Frutos Secos", "Materia Prima"),
    ("Coco Rallado (5kg)", 1.0, 1.0, "Materia Prima", "Materia Prima"),
    ("Premezcla para Tiramisú (600gr)", 2.0, 1.0, "Reposteria", "Materia Prima"),
    ("Aceite Cañuelas (1,5lt)", 12.0, 6.0, "Materia Prima", "Materia Prima"),
    ("Aceite Cañuelas (900ml)", 12.0, 12.0, "Materia Prima", "Materia Prima"),
    ("Azúcar (1kg)", 100.0, 50.0, "Materia Prima", "Materia Prima"),
    ("Chocolate Mapsa con Leche (500gr)", 20.0, 10.0, "Reposteria", "Materia Prima"),
    ("Chocolate Mapsa Blanco (500gr)", 20.0, 10.0, "Reposteria", "Materia Prima"),
    ("Chocolate Mapsa Semi amargo (500gr)", 30.0, 10.0, "Reposteria", "Materia Prima"),
    ("Dulce de Leche (5kg)", 6.0, 3.0, "Reposteria", "Materia Prima"),
    ("Almidón de Maiz (25kg)", 1.0, 1.0, "Materia Prima", "Materia Prima"),
    ("Huevos (150 unidades)", 2.0, 1.0, "Materia Prima", "Materia Prima"),
    ("Semillas de Amapola (1kg)", 2.0, 1.0, "Reposteria", "Materia Prima"),
    ("Cacao Amargo Mapsa (1kg)", 3.0, 1.0, "Reposteria", "Materia Prima"),
    ("Mousse de Chocolate Amargo (1kg)", 2.0, 1.0, "Reposteria", "Materia Prima"),
    ("Mousse de Chocolate Mapsa (500gr)", 5.0, 2.0, "Reposteria", "Materia Prima"),
    ("Frutilla Mapsa (500gr)", 1.0, 1.0, "Reposteria", "Materia Prima"),
    ("Chocolate Blanco Alpino (1kg)", 2.0, 1.0, "Reposteria", "Materia Prima"),
    ("Pasta Ballina (500gr)", 2.0, 1.0, "Reposteria", "Materia Prima"),
    ("Almendra (1kg)", 2.0, 1.0, "Frutos Secos", "Materia Prima"),
    ("Granola (350gr)", 1.0, 1.0, "Almacén", "Materia Prima"),
    ("Oreo (350gr)", 20.0, 12.0, "Golosinas", "Producto Final"),
    ("Vocación (140gr)", 67.0, 50.0, "Golosinas", "Producto Final"),
    ("Chocolinas (250gr)", 20.0, 10.0, "Golosinas", "Producto Final"),
    ("Chocolinas (170gr)", 40.0, 20.0, "Golosinas", "Producto Final"),
    ("Bolsa 15x20 (u)", 5.0, 5.0, "Packaging", "Materia Prima"),
    ("Bolsa 12x15 (u)", 7.0, 5.0, "Packaging", "Materia Prima"),
    ("Bolsa 20x35 (u)", 2.0, 5.0, "Packaging", "Materia Prima"),
    ("Bolsa 17x30 (u)", 3.0, 5.0, "Packaging", "Materia Prima"),
    ("Pasta pistacho (250gr)", 4.0, 1.0, "Reposteria", "Materia Prima"),
    ("Pasta pistacho (1,25kg)", 1.0, 1.0, "Reposteria", "Materia Prima"),
    ("Nutella (3kg)", 1.0, 1.0, "Reposteria", "Materia Prima"),
    ("Nutella (140gr)", 13.0, 1.0, "Reposteria", "Materia Prima"),
    ("Pasta frambuesa (250gr)", 3.0, 1.0, "Reposteria", "Materia Prima"),
    ("Colorante rojo (15gr)", 12.0, 1.0, "Reposteria", "Materia Prima"),
    ("Leche condensada (395gr)", 1.0, 1.0, "Reposteria", "Materia Prima"),
    ("Esencia de Vainilla (2lts)", 3.0, 1.0, "Reposteria", "Materia Prima"),
    ("Gelatina sabor frutilla (40gr)", 14.0, 1.0, "Reposteria", "Materia Prima"),
    ("Vinagre (1lt)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Canela (30gr)", 4.0, 1.0, "Reposteria", "Materia Prima"),
    ("Café en saquitos (20u)", 1.0, 1.0, "Almacén", "Materia Prima"),
    ("Tia María (750ml)", 1.0, 1.0, "Reposteria", "Materia Prima"),
    ("Trapo de piso (u)", 4.0, 1.0, "Limpieza", "Materia Prima"),
    ("Papel higiénico (4u)", 2.0, 1.0, "Limpieza", "Materia Prima"),
    ("Servilleta en rollo (200u)", 3.0, 1.0, "Limpieza", "Materia Prima"),
    ("Alcohol (1lt)", 7.0, 1.0, "Limpieza", "Materia Prima"),
    ("Procenex para piso (900ml)", 2.0, 1.0, "Limpieza", "Materia Prima"),
    ("Lavandina en gel (700ml)", 3.0, 1.0, "Limpieza", "Materia Prima"),
    ("Detergente Magistral (750ml)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Cif (250ml)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Raid Matamosca (360ml)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Raid casa y jardín (360ml)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Desodorante aerosol Dove (250ml)", 2.0, 1.0, "Limpieza", "Materia Prima"),
    ("Toallitas nocturnas (16u)", 2.0, 1.0, "Varios", "Materia Prima"),
    ("Protectores (20u)", 2.0, 1.0, "Varios", "Materia Prima"),
    ("Jabón líquido manos (220ml)", 3.0, 1.0, "Limpieza", "Materia Prima"),
    ("Procenex limpia vidrios (420ml)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Líquido pisos brillo (450cm3)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Líquido para baños (420ml)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Blem cera para piso (420ml)", 1.0, 1.0, "Limpieza", "Materia Prima"),
    ("Esponja anti bacteria (u)", 12.0, 1.0, "Limpieza", "Materia Prima"),
    ("Esponja virulana (u)", 13.0, 1.0, "Limpieza", "Materia Prima"),
    ("Rollo aluminio (u)", 4.0, 1.0, "Packaging", "Materia Prima"),
    ("Rollo papel manteca (u)", 2.0, 1.0, "Packaging", "Materia Prima"),
    ("Papel film (u)", 1.0, 1.0, "Packaging", "Materia Prima"),
    ("Bolsa folex (u)", 2.0, 1.0, "Packaging", "Materia Prima"),
    ("Bolsa consorcio (60x90)", 3.0, 1.0, "Limpieza", "Materia Prima")
]

if st.button("🚀 Ejecutar Carga de 93 Productos"):
    conn = get_connection()
    cur = conn.cursor()
    success, skips = 0, 0
    
    for nom, stock, mini, cat, sub in productos_data:
        try:
            cur.execute("""
                INSERT INTO productos (nombre, stock, stock_minimo, categoria, subcategoria, precio_venta, precio_costo)
                VALUES (%s, %s, %s, %s, %s, 0, 0)
                ON CONFLICT (nombre) DO UPDATE SET 
                    stock = EXCLUDED.stock, 
                    stock_minimo = EXCLUDED.stock_minimo,
                    categoria = EXCLUDED.categoria,
                    subcategoria = EXCLUDED.subcategoria;
            """, (nom, stock, mini, cat, sub))
            success += 1
        except Exception as e:
            skips += 1
            st.error(f"Error en {nom}: {e}")
            
    conn.commit()
    cur.close()
    conn.close()
    st.success(f"¡Carga completa! {success} productos actualizados/creados con subcategoría.")
