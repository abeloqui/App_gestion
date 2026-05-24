import psycopg2
import streamlit as st
import os
from sqlalchemy import create_engine

@st.cache_resource
def get_engine():
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("❌ DATABASE_URL no configurado en Secrets o Variables de Entorno.")
        st.stop()
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url, pool_pre_ping=True, echo=False)

def get_connection():
    engine = get_engine()
    return engine.raw_connection()

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Usuarios
        cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT DEFAULT 'operador',
            activo BOOLEAN DEFAULT TRUE,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Admin por defecto
        cur.execute("""
            INSERT INTO usuarios (username, password, rol)
            VALUES ('admin', '1234', 'admin')
            ON CONFLICT (username) DO NOTHING
        """)

        # 2. Productos
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            categoria TEXT DEFAULT 'Otros',
            subcategoria TEXT DEFAULT 'Materia Prima',
            unidad TEXT DEFAULT 'unidad',
            precio_venta FLOAT DEFAULT 0,
            precio_costo FLOAT DEFAULT 0,
            stock FLOAT DEFAULT 0,
            stock_minimo FLOAT DEFAULT 5,
            es_producido BOOLEAN DEFAULT FALSE
        )''')

        # 3. Ventas
        cur.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total FLOAT,
            medio_pago TEXT DEFAULT 'Efectivo',
            usuario TEXT DEFAULT 'admin'
        )''')

        # 4. Detalle de Ventas
        cur.execute('''CREATE TABLE IF NOT EXISTS detalle_ventas (
            id SERIAL PRIMARY KEY,
            venta_id INTEGER REFERENCES ventas(id),
            producto_id INTEGER REFERENCES productos(id),
            cantidad FLOAT,
            precio_unitario FLOAT,
            subtotal FLOAT
        )''')

        # 5. Movimientos
        cur.execute('''CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            tipo TEXT,
            producto_id INTEGER REFERENCES productos(id),
            cantidad FLOAT,
            costo_unitario FLOAT DEFAULT 0,
            total FLOAT DEFAULT 0,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            detalle TEXT,
            usuario TEXT DEFAULT 'admin'
        )''')

        migraciones = [
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS unidad TEXT DEFAULT 'unidad';",
            "ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS costo_unitario FLOAT DEFAULT 0;",
            "ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS total FLOAT DEFAULT 0;",
            "ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS detalle TEXT;",
            "ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS usuario TEXT DEFAULT 'admin';",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_producido BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS usuario TEXT DEFAULT 'admin';",
        ]
        for m in migraciones:
            try:
                cur.execute(m)
            except Exception:
                pass

        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error al inicializar la base de datos: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    init_db()
