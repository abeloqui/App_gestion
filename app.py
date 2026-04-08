import streamlit as st
from database import init_db

st.set_page_config(page_title="Sistema Pro", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso al Sistema")
    user = st.text_input("Usuario")
    pw = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if user == "admin" and pw == "1234":
            st.session_state.logged_in = True
            st.session_state.username = user
            st.session_state.role = "admin"
            init_db() # Inicializa tablas si no existen
            st.rerun()
        else:
            st.error("Error de credenciales")
else:
    st.title(f"Bienvenido, {st.session_state.username}")
    st.info("Selecciona una opción en el menú de la izquierda para comenzar.")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()