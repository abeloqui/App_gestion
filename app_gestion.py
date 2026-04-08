import streamlit as st
from database import init_db, get_engine
import pandas as pd

# Configuración inicial (DEBE SER LA PRIMERA LÍNEA DE STREAMLIT)
st.set_page_config(page_title="Sistema Gestión Pro", layout="wide")

# Inicializar base de datos
try:
    init_db()
except Exception as e:
    st.error(f"Error de conexión: {e}")

# Control de Sesión
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- LÓGICA DE PANTALLA ---
if not st.session_state.logged_in:
    # Si NO está logueado, muestra el formulario
    st.title("🔐 Acceso al Sistema")
    
    with st.container():
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar"):
            if user == "admin" and pw == "1234":
                st.session_state.logged_in = True
                st.session_state.username = user
                st.success("Cargando sistema...")
                st.rerun() # Esto refresca la página para mostrar el Dashboard
            else:
                st.error("Credenciales incorrectas")
else:
    # Si YA está logueado, muestra el Dashboard
    st.title(f"📊 Panel de Control - {st.session_state.username}")
    
    # Aquí va el código de los gráficos que pusimos antes...
    st.info("¡Bienvenido! Selecciona una opción en el menú lateral.")
    
    # Botón para cerrar sesión (opcional)
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()
