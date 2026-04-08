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
        # Productos e Insumos
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL, categoria TEXT,
            precio_venta REAL NOT NULL, precio_costo REAL DEFAULT 0,
            stock REAL NOT NULL DEFAULT 0, stock_minimo REAL DEFAULT 5
        )''')
        # Movimientos
        cur.execute('''CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT, producto_id INTEGER REFERENCES productos(id),
            cantidad REAL, precio_unitario REAL, total REAL
        )''')
        # Ventas
        cur.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY, ticket_num SERIAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cajero TEXT, total REAL, medio_pago TEXT, items TEXT
        )''')
        # Recetas (Insumos por Plato)
        cur.execute('''CREATE TABLE IF NOT EXISTS recetas (
            id SERIAL PRIMARY KEY, plato_id INTEGER REFERENCES productos(id),
            insumo_id INTEGER REFERENCES productos(id), cantidad REAL
        )''')
        # Migración: Agregar medio_pago si no existe
        cur.execute("""
            DO $$ BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ventas' AND column_name='medio_pago') 
            THEN ALTER TABLE ventas ADD COLUMN medio_pago TEXT DEFAULT 'Efectivo'; 
            END IF; END $$;
        """)
        conn.commit()
    finally:
        cur.close()
        conn.close()
