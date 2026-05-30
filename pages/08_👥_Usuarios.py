import streamlit as st
import pandas as pd
from database import get_connection, get_engine

from streamlit_cookies_manager import EncryptedCookieManager

# --- COOKIES: restaurar sesión ---
cookies = EncryptedCookieManager(prefix="dulcejazmin_", password="dj_secret_2024_$")
if not cookies.ready():
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = cookies.get("logged_in") == "true"
if "username" not in st.session_state:
    st.session_state.username = cookies.get("username") or None
if "rol" not in st.session_state:
    st.session_state.rol = cookies.get("rol") or None

if not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

if st.session_state.get("rol") != "admin":
    st.error("🔒 Acceso restringido. Solo administradores.")
    st.stop()


st.header("👥 Gestión de Usuarios")

engine = get_engine()

tab_lista, tab_nuevo, tab_cambiar_pass = st.tabs(["👥 Usuarios", "➕ Nuevo Usuario", "🔑 Cambiar Contraseña"])

with tab_lista:
    df = pd.read_sql("SELECT id, username, rol, activo, creado_en FROM usuarios ORDER BY creado_en DESC", engine)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Activar / Desactivar usuario")
    df_otros = df[df['username'] != 'admin']
    if df_otros.empty:
        st.info("No hay otros usuarios creados aún.")
    else:
        usuario_sel = st.selectbox("Seleccioná un usuario", df_otros['username'].tolist())
        fila = df_otros[df_otros['username'] == usuario_sel].iloc[0]
        estado_actual = fila['activo']
        label = "🔴 Desactivar" if estado_actual else "🟢 Activar"

        if st.button(label, use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            try:
                cur.execute("UPDATE usuarios SET activo = %s WHERE username = %s", (not estado_actual, usuario_sel))
                conn.commit()
                st.success(f"Usuario '{usuario_sel}' {'desactivado' if estado_actual else 'activado'}.")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"Error: {e}")
            finally:
                conn.close()

with tab_nuevo:
    with st.form("form_nuevo_usuario", clear_on_submit=True):
        nuevo_user = st.text_input("Nombre de usuario")
        nuevo_pass = st.text_input("Contraseña", type="password")
        nuevo_rol = st.selectbox("Rol", ["operador", "admin"],
                                  help="Operador: solo ventas, compras y producción. Admin: acceso completo.")

        if st.form_submit_button("💾 Crear Usuario"):
            if not nuevo_user.strip() or not nuevo_pass.strip():
                st.warning("Completá todos los campos.")
            else:
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("""
                        INSERT INTO usuarios (username, password, rol)
                        VALUES (%s, %s, %s)
                    """, (nuevo_user.strip(), nuevo_pass.strip(), nuevo_rol))
                    conn.commit()
                    st.success(f"✅ Usuario '{nuevo_user}' creado como {nuevo_rol}.")
                except Exception as e:
                    conn.rollback()
                    if "unique" in str(e).lower():
                        st.error(f"❌ Ya existe un usuario con ese nombre.")
                    else:
                        st.error(f"Error: {e}")
                finally:
                    conn.close()

with tab_cambiar_pass:
    st.write("Cambiá la contraseña de cualquier usuario.")
    with st.form("form_cambiar_pass", clear_on_submit=True):
        df_users = pd.read_sql("SELECT username FROM usuarios ORDER BY username", engine)
        user_edit = st.selectbox("Usuario", df_users['username'].tolist())
        nueva_pass = st.text_input("Nueva Contraseña", type="password")
        confirmar = st.text_input("Confirmar Contraseña", type="password")

        if st.form_submit_button("🔑 Actualizar Contraseña"):
            if not nueva_pass or not confirmar:
                st.warning("Completá ambos campos.")
            elif nueva_pass != confirmar:
                st.error("Las contraseñas no coinciden.")
            else:
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE usuarios SET password = %s WHERE username = %s", (nueva_pass, user_edit))
                    conn.commit()
                    st.success(f"✅ Contraseña de '{user_edit}' actualizada.")
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error: {e}")
                finally:
                    conn.close()
                        
