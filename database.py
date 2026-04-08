import psycopg2
import streamlit as st
import os
from sqlalchemy import create_engine

def get_connection():
    """Conexión clásica para INSERT/UPDATE/DELETE."""
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL no configurado.")
        st.stop()
    return psycopg2.connect(db_url)

def get_engine():
    """Motor para que Pandas lea sin Warnings."""
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    # SQLAlchemy requiere que la URL empiece con postgresql:// no postgres://
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Aquí van tus CREATE TABLE que ya tienes...
        cur.execute('''CREATE TABLE IF NOT EXISTS productos (...)''')
        # ... resto de las tablas ...
        conn.commit()
    finally:
        cur.close()
        conn.close()
