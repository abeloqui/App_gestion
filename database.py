import psycopg2
import streamlit as st
import os

def get_connection():
    # Intenta obtener la URL de los Secrets de Streamlit o variables de entorno
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("❌ No se encontró DATABASE_URL en los Secrets de Streamlit.")
        st.stop()
    return psycopg2.connect(db_url)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Tabla de Productos
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            categoria TEXT DEFAULT 'General',
            precio_venta REAL NOT NULL,
            precio_costo REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER DEFAULT 5
        )''')

        # 2. Tabla de Movimientos (La que te daba error)
        cur.execute('''CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT, 
            producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER, 
            precio_unitario REAL, 
            total REAL
        )''')

        # 3. Tabla de Ventas
        cur.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY, 
            ticket_num SERIAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cajero TEXT, 
            total REAL, 
            items TEXT
        )''')
        
        # 4. Tabla de Configuración
        cur.execute('''CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY, 
            valor INTEGER
        )''')
        
        # Insertar valor inicial de ticket si no existe
        cur.execute("INSERT INTO config (clave, valor) VALUES ('ultimo_ticket', 0) ON CONFLICT DO NOTHING")
        
        conn.commit()
    except Exception as e:
        st.error(f"Error al inicializar la base de datos: {e}")
    finally:
        cur.close()
        conn.close()
