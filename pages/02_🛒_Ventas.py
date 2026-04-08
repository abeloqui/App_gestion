# --- SELECCIÓN DE PRODUCTOS ---
engine = get_engine()
df_p = pd.read_sql("""
    SELECT id, nombre, precio_venta, stock 
    FROM productos 
    WHERE stock > 0 AND subcategoria = 'Producto Final' 
    ORDER BY nombre
""", engine)
