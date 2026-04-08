import psycopg2
import streamlit as st
import os
from sqlalchemy import create_engine

# --- CONFIGURACIÓN DE CONEXIÓN ---

@st.cache_resource
def get_engine():
    """Crea y cachea el engine de SQLAlchemy"""
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("❌ DATABASE_URL no configurado en Secrets o Variables de Entorno.")
        st.stop()
    
    # Ajuste para compatibilidad con Render / Railway / etc.
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return create_engine(db_url, pool_pre_ping=True)


def get_connection():
    """Retorna una conexión cruda (psycopg2)"""
    engine = get_engine()
    return engine.raw_connection()

ALTER TABLE recetas ADD COLUMN IF NOT EXISTS unidad TEXT DEFAULT 'kg';
# --- INICIALIZACIÓN DE TABLAS ---
def init_db():
    """
    Crea las tablas si no existen y realiza migraciones automáticas.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Tabla de Productos
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY, 
            nombre TEXT UNIQUE NOT NULL, 
            categoria TEXT DEFAULT 'General',
            subcategoria TEXT DEFAULT 'Materia Prima',
            precio_venta REAL DEFAULT 0, 
            precio_costo REAL DEFAULT 0,
            stock REAL NOT NULL DEFAULT 0, 
            stock_minimo REAL DEFAULT 5,
            es_producido BOOLEAN DEFAULT FALSE
        )''')

        # 2. Tabla de Movimientos
        cur.execute('''CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY, 
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT, 
            producto_id INTEGER REFERENCES productos(id),
            cantidad REAL, 
            precio_unitario REAL DEFAULT 0, 
            total REAL DEFAULT 0,
            detalle TEXT
        )''')

        # 3. Tabla de Ventas
        cur.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY, 
            ticket_num SERIAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cajero TEXT, 
            total REAL, 
            medio_pago TEXT DEFAULT 'Efectivo', 
            items TEXT
        )''')

        # 4. Tabla de Recetas
        cur.execute('''CREATE TABLE IF NOT EXISTS recetas (
            id SERIAL PRIMARY KEY, 
            plato_id INTEGER REFERENCES productos(id), 
            insumo_id INTEGER REFERENCES productos(id), 
            cantidad REAL
        )''')

        # --- Migraciones automáticas (agregar columnas si no existen) ---
        migrations = [
            "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS medio_pago TEXT DEFAULT 'Efectivo';",
            "ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS detalle TEXT;",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_producido BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS subcategoria TEXT DEFAULT 'Materia Prima';"
        ]

        for mig in migrations:
            try:
                cur.execute(mig)
            except:
                pass  # Si ya existe, ignorar el error

        conn.commit()
        # st.success("Base de datos inicializada correctamente")  # descomentar solo para debug

    except Exception as e:
        conn.rollback()
        st.error(f"Error al inicializar la base de datos: {e}")
    finally:
        cur.close()
        conn.close()
