import streamlit as st
from database import get_connection

st.set_page_config(page_title="Carga Inicial Dulce Jazmín", layout="centered")

st.title("🚀 Carga Inicial: Dulce Jazmín")
st.info("Este script cargará los productos con el stock actual y mínimo extraído del PDF.")

# [span_0](start_span)Datos procesados del PDF[span_0](end_span)
productos_data = [
    # Nombre, Stock Actual, Mínimo, Categoría Sugerida
    ("Manteca (5kg)", 1.0, 0.0, "Materia Prima"),
    ("Harina Leudante (1kg)", 95.0, 50.0, "Materia Prima"),
    ("Harina 000 (1kg)", 70.0, 50.0, "Materia Prima"),
    ("Sobre de levadura (10g)", 25.0, 10.0, "Materia Prima"),
    ("Kinder Bueno (42g)", 75.0, 30.0, "Golosinas"),
    ("Kit kat (42g)", 65.0, 24.0, "Golosinas"),
    ("Kinder común (12,5g)", 23.0, 24.0, "Golosinas"),
    ("Bon o bon (15g)", 10.0, 30.0, "Golosinas"),
    ("Chocolate Cadbury frutilla (29g)", 12.0, 12.0, "Golosinas"),
    ("Chocolate Marroc (14g)", 50.0, 60.0, "Golosinas"),
    ("Queso cremoso (3,5kg)", 6.0, 3.0, "Lácteos"),
    ("Crema de leche (10lts)", 3.0, 2.0, "Lácteos"),
    ("Pasas de Uva (500gr)", 2.0, 1.0, "Frutos Secos"),
    ("Chip de Chocolate negro (500gr)", 2.0, 1.0, "Reposteria"),
    ("Membrillo (5kg)", 4.0, 2.0, "Reposteria"),
    ("Leche entera (1lt)", 15.0, 10.0, "Lácteos"),
    ("Yerba (1kg)", 3.0, 1.0, "Almacén"),
    ("Mantecol untable (250gr)", 4.0, 1.0, "Reposteria"),
    ("Jugo Baggio (200ml)", 18.0, 18.0, "Bebidas"),
    ("Chocolate Cobertura Blanco (12,8kg)", 1.0, 1.0, "Reposteria"),
    ("Chocolate Cobertura con Leche (12,8kg)", 1.0, 1.0, "Reposteria"),
    ("Chocolate Cobertura Semi amargo (12,8kg)", 1.0, 1.0, "Reposteria"),
    ("Bolsa de Mini Oreo (150gr)", 56.0, 25.0, "Golosinas"),
    ("Aceite Natura Aerosol (120cc)", 14.0, 6.0, "Materia Prima"),
    ("Café instantáneo (160gr)", 2.0, 6.0, "Almacén"),
    ("Mantecol (235gr)", 6.0, 2.0, "Golosinas"),
    ("Avena (350gr)", 10.0, 12.0, "Almacén"),
    ("Ferrero Roche (250gr)", 2.0, 1.0, "Golosinas"),
    ("Ferrero Roche (300gr)", 1.0, 1.0, "Golosinas"),
    ("Azúcar impalpable (10kg)", 4.0, 2.0, "Materia Prima"),
    ("Azúcar Rubia (10kg)", 3.0, 1.0, "Materia Prima"),
    ("Nueces (5kg)", 2.0, 1.0, "Frutos Secos"),
    ("Coco Rallado (5kg)", 1.0, 1.0, "Materia Prima"),
    ("Premezcla para Tiramisú (600gr)", 2.0, 1.0, "Reposteria"),
    ("Aceite Cañuelas (1,5lt)", 12.0, 6.0, "Materia Prima"),
    ("Aceite Cañuelas (900ml)", 12.0, 12.0, "Materia Prima"),
    ("Azúcar (1kg)", 100.0, 50.0, "Materia Prima"),
    ("Chocolate Mapsa con Leche (500gr)", 20.0, 10.0, "Reposteria"),
    ("Chocolate Mapsa Blanco (500gr)", 20.0, 10.0, "Reposteria"),
    ("Chocolate Mapsa Semi amargo (500gr)", 30.0, 10.0, "Reposteria"),
    ("Dulce de Leche (5kg)", 6.0, 3.0, "Reposteria"),
    ("Almidón de Maiz (25kg)", 1.0, 1.0, "Materia Prima"),
    ("Huevos (150 unidades)", 2.0, 1.0, "Materia Prima"),
    ("Semillas de Amapola (1kg)", 2.0, 1.0, "Reposteria"),
    ("Cacao Amargo Mapsa (1kg)", 3.0, 1.0, "Reposteria"),
    ("Mousse de Chocolate Amargo (1kg)", 2.0, 1.0, "Reposteria"),
    ("Mousse de Chocolate Mapsa (500gr)", 5.0, 2.0, "Reposteria"),
    ("Frutilla Mapsa (500gr)", 1.0, 1.0, "Reposteria"),
    ("Chocolate Blanco Alpino (1kg)", 2.0, 1.0, "Reposteria"),
    ("Pasta Ballina (500gr)", 2.0, 1.0, "Reposteria"),
    ("Almendra (1kg)", 2.0, 1.0, "Frutos Secos"),
    ("Granola (350gr)", 1.0, 1.0, "Almacén"),
    ("Oreo (350gr)", 20.0, 12.0, "Golosinas"),
    ("Vocación (140gr)", 67.0, 50.0, "Golosinas"),
    ("Chocolinas (250gr)", 20.0, 10.0, "Golosinas"),
    ("Chocolinas (170gr)", 40.0, 20.0, "Golosinas"),
    ("Bolsa 15x20 (u)", 5.0, 5.0, "Packaging"),
    ("Bolsa 12x15 (u)", 7.0, 5.0, "Packaging"),
    ("Bolsa 20x35 (u)", 2.0, 5.0, "Packaging"),
    ("Bolsa 17x30 (u)", 3.0, 5.0, "Packaging"),
    ("Pasta pistacho (250gr)", 4.0, 1.0, "Reposteria"),
    ("Pasta pistacho (1,25kg)", 1.0, 1.0, "Reposteria"),
    ("Nutella (3kg)", 1.0, 1.0, "Reposteria"),
    ("Nutella (140gr)", 13.0, 1.0, "Reposteria"),
    ("Pasta frambuesa (250gr)", 3.0, 1.0, "Reposteria"),
    ("Colorante rojo (15gr)", 12.0, 1.0, "Reposteria"),
    ("Leche condensada (395gr)", 1.0, 1.0, "Reposteria"),
    ("Esencia de Vainilla (2lts)", 3.0, 1.0, "Reposteria"),
    ("Gelatina sabor frutilla (40gr)", 14.0, 1.0, "Reposteria"),
    ("Vinagre (1lt)", 1.0, 1.0, "Limpieza"),
    ("Canela (30gr)", 4.0, 1.0, "Reposteria"),
    ("Café en saquitos (20u)", 1.0, 1.0, "Almacén"),
    ("Tia María (750ml)", 1.0, 1.0, "Reposteria"),
    ("Trapo de piso (u)", 4.0, 1.0, "Limpieza"),
    ("Papel higiénico (4u)", 2.0, 1.0, "Limpieza"),
    ("Servilleta en rollo (200u)", 3.0, 1.0, "Limpieza"),
    ("Alcohol (1lt)", 7.0, 1.0, "Limpieza"),
    ("Procenex para piso (900ml)", 2.0, 1.0, "Limpieza"),
    ("Lavandina en gel (700ml)", 3.0, 1.0, "Limpieza"),
    ("Detergente Magistral (750ml)", 1.0, 1.0, "Limpieza"),
    ("Cif (250ml)", 1.0, 1.0, "Limpieza"),
    ("Raid Matamosca (360ml)", 1.0, 1.0, "Limpieza"),
    ("Raid casa y jardín (360ml)", 1.0, 1.0, "Limpieza"),
    ("Desodorante aerosol Dove (250ml)", 2.0, 1.0, "Limpieza"),
    ("Toallitas nocturnas (16u)", 2.0, 1.0, "Varios"),
    ("Protectores (20u)", 2.0, 1.0, "Varios"),
    ("Jabón líquido manos (220ml)", 3.0, 1.0, "Limpieza"),
    ("Procenex limpia vidrios (420ml)", 1.0, 1.0, "Limpieza"),
    ("Líquido pisos brillo (450cm3)", 1.0, 1.0, "Limpieza"),
    ("Líquido para baños (420ml)", 1.0, 1.0, "Limpieza"),
    ("Blem cera para piso (420ml)", 1.0, 1.0, "Limpieza"),
    ("Esponja anti bacteria (u)", 12.0, 1.0, "Limpieza"),
    ("Esponja virulana (u)", 13.0, 1.0, "Limpieza"),
    ("Rollo aluminio (u)", 4.0, 1.0, "Packaging"),
    ("Rollo papel manteca (u)", 2.0, 1.0, "Packaging"),
    ("Papel film (u)", 1.0, 1.0, "Packaging"),
    ("Bolsa folex (u)", 2.0, 1.0, "Packaging"),
    ("Bolsa consorcio (60x90)", 3.0, 1.0, "Limpieza")
]

if st.button("🚀 Ejecutar Carga de 93 Productos"):
    conn = get_connection()
    cur = conn.cursor()
    success, skips = 0, 0
    
    for nom, stock, mini, cat in productos_data:
        try:
            cur.execute("""
                INSERT INTO productos (nombre, stock, stock_minimo, categoria, precio_venta, precio_costo)
                VALUES (%s, %s, %s, %s, 0, 0)
                ON CONFLICT (nombre) DO UPDATE SET 
                stock = EXCLUDED.stock, 
                stock_minimo = EXCLUDED.stock_minimo;
            """, (nom, stock, mini, cat))
            success += 1
        except Exception as e:
            skips += 1
            st.error(f"Error en {nom}: {e}")
            
    conn.commit()
    cur.close()
    conn.close()
    st.success(f"¡Carga completa! {success} productos actualizados/creados.")
