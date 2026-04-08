import psycopg2
import os
import streamlit as st

def get_connection():
    # Intentamos obtener la URL de Render, si no, usamos una por defecto (o local)
    # En Render, configurarás una variable llamada DATABASE_URL
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    
    if not db_url:
        st.error("No se encontró la configuración de la base de datos.")
        st.stop()
        
    return psycopg2.connect(db_url)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Usamos sintaxis estándar de PostgreSQL
    cur.execute('''CREATE TABLE IF NOT EXISTS productos (
        id SERIAL PRIMARY KEY,
        nombre TEXT UNIQUE NOT NULL,
        categoria TEXT DEFAULT 'General',
        precio_venta REAL NOT NULL,
        precio_costo REAL NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        stock_minimo INTEGER DEFAULT 5
    )''')
    # ... (el resto de las tablas con SERIAL en lugar de AUTOINCREMENT)
    conn.commit()
    cur.close()
    conn.close()