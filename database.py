import psycopg2
import streamlit as st
import os
from sqlalchemy import create_engine

def get_connection():
    """Conexión clásica para INSERT/UPDATE/DELETE (psycopg2)."""
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("❌ DATABASE_URL no configurado en los Secrets de Streamlit.")
        st.stop()
    return psycopg2.connect(db_url)

def get_engine():
    """Motor para que Pandas lea sin Warnings (SQLAlchemy)."""
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)

def init_db():
    """Inicializa todas las tablas necesarias en PostgreSQL."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Tabla de Productos (con precio_costo para el CMP)
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            categoria TEXT DEFAULT 'General',
            precio_venta REAL NOT NULL,
            precio_costo REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER DEFAULT 5
        )''')

        # 2. Tabla de Movimientos (Historial de entradas y salidas)
        cur.execute('''CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT, 
            producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER, 
            precio_unitario REAL, 
            total REAL
        )''')

        # 3. Tabla de Ventas (Cabecera de tickets)
        cur.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY, 
            ticket_num SERIAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cajero TEXT, 
            total REAL, 
            medio_pago TEXT,
            items TEXT
        )''')
        
        # 4. Tabla de Configuración (Para estados globales del sistema)
        cur.execute('''CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY, 
            valor INTEGER
        )''')
        
        # Insertar valor inicial de ticket si la tabla está vacía
        cur.execute("INSERT INTO config (clave, valor) VALUES ('ultimo_ticket', 0) ON CONFLICT DO NOTHING")
        
        conn.commit()
    except Exception as e:
        st.error(f"Error al inicializar la base de datos: {e}")
    finally:
        cur.close()
        conn.close()
