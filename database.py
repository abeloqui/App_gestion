import psycopg2
import streamlit as st
import os
from sqlalchemy import create_engine

# --- CONFIGURACIÓN DE CONEXIÓN ---

@st.cache_resource
def get_engine():
    """
    Crea y cachea el engine de SQLAlchemy para pooling de conexiones.
    Esto evita abrir y cerrar conexiones en cada clic del usuario.
    """
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("❌ DATABASE_URL no configurado en Secrets o Variables de Entorno.")
        st.stop()
    
    # Ajuste para compatibilidad con SQLAlchemy y Render/Heroku
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return create_engine(db_url)

def get_connection():
    """
    Retorna una conexión cruda (psycopg2) desde el engine.
    Útil para operaciones que requieren cursores manuales y transacciones.
    """
    engine = get_engine()
    return engine.raw_connection()

# --- INICIALIZACIÓN DE TABLAS ---

def init_db():
    """
    Crea la estructura de tablas si no existe. 
    Incluye lógica de migración automática para columnas nuevas.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Tabla de Productos (Insumos, Intermedios y Finales)
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY, 
            nombre TEXT UNIQUE NOT NULL, 
            categoria TEXT DEFAULT 'General',
            subcategoria TEXT DEFAULT 'Insumo', -- 'Insumo', 'Intermedio' o 'Final'
            precio_venta REAL DEFAULT 0, 
            precio_costo REAL DEFAULT 0,
            stock REAL NOT NULL DEFAULT 0, 
            stock_minimo REAL DEFAULT 5,
            es_producido BOOLEAN DEFAULT FALSE
        )''')

        # 2. Tabla de Movimientos (Historial de todo lo que entra y sale)
        cur.execute('''CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY, 
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT, -- 'venta', 'compra', 'produccion', 'ajuste'
            producto_id INTEGER REFERENCES productos(id),
            cantidad REAL, 
            precio_unitario REAL DEFAULT 0, 
            total REAL DEFAULT 0,
            detalle TEXT
        )''')

        # 3. Tabla de Ventas (Cabecera de los tickets)
        cur.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY, 
            ticket_num SERIAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cajero TEXT, 
            total REAL, 
            medio_pago TEXT DEFAULT 'Efectivo', 
            items TEXT -- Guardamos el JSON de los productos vendidos
        )''')

        # 4. Tabla de Recetas (Define la relación entre productos)
        cur.execute('''CREATE TABLE IF NOT EXISTS recetas (
            id SERIAL PRIMARY KEY, 
            plato_id INTEGER REFERENCES productos(id), -- El producto que se fabrica
            insumo_id INTEGER REFERENCES productos(id), -- El ingrediente que se usa
            cantidad REAL -- Cuánto del ingrediente se necesita
        )''')

        # --- LÓGICA DE MIGRACIÓN (Por si ya tenías tablas creadas) ---
        
        # Agregar columna medio_pago a ventas si no existe
        cur.execute("""
            DO $$ BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ventas' AND column_name='medio_pago') 
            THEN ALTER TABLE ventas ADD COLUMN medio_pago TEXT DEFAULT 'Efectivo'; 
            END IF; END $$;
        """)

        # Agregar columna detalle a movimientos si no existe
        cur.execute("""
            DO $$ BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='movimientos' AND column_name='detalle') 
            THEN ALTER TABLE movimientos ADD COLUMN detalle TEXT; 
            END IF; END $$;
        """)

        # Agregar columna es_producido a productos si no existe
        cur.execute("""
            DO $$ BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='es_producido') 
            THEN ALTER TABLE productos ADD COLUMN es_producido BOOLEAN DEFAULT FALSE; 
            END IF; END $$;
        """)

        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error al inicializar la base de datos: {e}")
    finally:
        cur.close()
        conn.close()
        
