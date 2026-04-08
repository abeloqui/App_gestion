engine = get_engine()
df_p = pd.read_sql("""
    SELECT id, nombre 
    FROM productos 
    WHERE subcategoria IN ('Preelaborado', 'Producto Final') 
    ORDER BY nombre
""", engine)
