import psycopg2
import streamlit as st
import os
from sqlalchemy import create_engine

def get_connection():
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("❌ DATABASE_URL no configurado.")
        st.stop()
    return psycopg2.connect(db_url)

def get_engine():
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        # --- 1. CREACIÓN DE TABLAS (Si no existen) ---
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            categoria TEXT DEFAULT 'General',
            precio_venta REAL NOT NULL,
            precio_costo REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER DEFAULT 5
        )''')

        cur.execute('''CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT, producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER, precio_unitario REAL, total REAL
        )''')

        cur.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY, ticket_num SERIAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cajero TEXT, total REAL, items TEXT
        )''')

        # --- 2. MIGRACIÓN / REPARACIÓN (Por si la tabla es vieja) ---
        # Esto agrega la columna medio_pago a la tabla ventas si no existe
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='ventas' AND column_name='medio_pago') THEN 
                    ALTER TABLE ventas ADD COLUMN medio_pago TEXT DEFAULT 'Efectivo';
                END IF; 
            END $$;
        """)

        conn.commit()
    except Exception as e:
        st.error(f"Error en init_db: {e}")
    finally:
        cur.close()
        conn.close()
