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
    
    # Corrección para compatibilidad con Render, Railway, etc.
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return create_engine(db_url, pool_pre_ping=True, echo=False)


def get_connection():
    """Retorna una conexión cruda psycopg2"""
    engine = get_engine()
    return engine.raw_connection()


# --- INICIALIZACIÓN DE TABLAS Y MIGRACIONES ---
def init_db():
    """
    Crea las tablas si no existen y aplica migraciones automáticas.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Tabla de Productos
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY, 
            nombre TEXT UNIQUE NOT NULL, 
            categoria TEXT DEFAULT 'Otros',
            subcategoria TEXT DEFAULT 'Materia Prima',
            precio_venta FLOAT DEFAULT 0,
            precio_costo FLOAT DEFAULT 0,
            stock FLOAT DEFAULT 0,
            stock_minimo FLOAT DEFAULT 5,
            es_producido BOOLEAN DEFAULT FALSE
        )''')

        # 2. Tabla de Ventas (Cabecera)
        cur.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY, 
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total FLOAT,
            medio_pago TEXT DEFAULT 'Efectivo'
        )''')

        # 3. Detalle de Ventas
        cur.execute('''CREATE TABLE IF NOT EXISTS detalle_ventas (
            id SERIAL PRIMARY KEY, 
            venta_id INTEGER REFERENCES ventas(id),
            producto_id INTEGER REFERENCES productos(id),
            cantidad FLOAT,
            precio_unitario FLOAT,
            subtotal FLOAT
        )''')

        # 4. Tabla de Recetas
        cur.execute('''CREATE TABLE IF NOT EXISTS recetas (
            id SERIAL PRIMARY KEY, 
            plato_id INTEGER REFERENCES productos(id),
            insumo_id INTEGER REFERENCES productos(id),
            cantidad FLOAT NOT NULL,
            unidad TEXT DEFAULT 'kg',
            notas TEXT
        )''')

        # 5. Tabla de Movimientos (Historial)
        cur.execute('''CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY, 
            tipo TEXT, -- 'compra', 'venta', 'produccion', 'ajuste'
            producto_id INTEGER REFERENCES productos(id),
            cantidad FLOAT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            detalle TEXT
        )''')

        # --- SECCIÓN DE MIGRACIONES (MODIFICADO PARA RENDER) ---

        migrations = [
            # 1. Asegurar que existe la restricción UNIQUE para evitar el error de ON CONFLICT
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_plato_insumo') THEN
                    ALTER TABLE recetas ADD CONSTRAINT unique_plato_insumo UNIQUE (plato_id, insumo_id);
                END IF;
            END $$;
            """,
            
            # 2. Otras columnas necesarias
            "ALTER TABLE recetas ADD COLUMN IF NOT EXISTS unidad TEXT DEFAULT 'kg';",
            "ALTER TABLE recetas ADD COLUMN IF NOT EXISTS notas TEXT;",
            "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS medio_pago TEXT DEFAULT 'Efectivo';",
            "ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS detalle TEXT;",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_producido BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE productos ALTER COLUMN subcategoria SET DEFAULT 'Materia Prima';"
        ]

        for migration in migrations:
            try:
                cur.execute(migration)
            except Exception as e:
                # Silenciamos errores de columnas existentes, pero podrías usar st.write(e) para debug
                pass

        conn.commit()

    except Exception as e:
        conn.rollback()
        st.error(f"Error al inicializar la base de datos: {e}")
    finally:
        cur.close()
        conn.close()


# Llamada automática al iniciar
if __name__ == "__main__":
    init_db()
