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


st.set_page_config(page_title="Punto de Venta", layout="wide")

st.header("🛒 Punto de Venta")

engine = get_engine()
try:
    df_p = pd.read_sql("""
        SELECT id, nombre, precio_venta, stock, unidad
        FROM productos
        WHERE stock > 0 AND subcategoria = 'Producto Final'
        ORDER BY nombre
    """, engine)
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

if df_p.empty:
    st.warning("No hay Productos Finales con stock disponible para vender.")
else:
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Seleccionar Productos")
        with st.form("form_venta"):
            producto_sel = st.selectbox("Producto", df_p['nombre'].tolist())
            prod_info = df_p[df_p['nombre'] == producto_sel].iloc[0]
            st.caption(f"Disponible: {prod_info['stock']} {prod_info['unidad']}")
            cantidad = st.number_input("Cantidad", min_value=0.5, step=0.5)

            if st.form_submit_button("🛒 Agregar al Carrito"):
                if cantidad > prod_info['stock']:
                    st.error(f"Stock insuficiente. Solo quedan {prod_info['stock']} {prod_info['unidad']}.")
                else:
                    precio = float(prod_info['precio_venta'])
                    cant = float(cantidad)
                    existe = False
                    for item in st.session_state.carrito:
                        if item['id'] == int(prod_info['id']):
                            item['cantidad'] += cant
                            item['subtotal'] = round(item['cantidad'] * item['precio'], 2)
                            existe = True
                            break
                    if not existe:
                        st.session_state.carrito.append({
                            "id": int(prod_info['id']),
                            "nombre": str(producto_sel),
                            "cantidad": cant,
                            "precio": precio,
                            "subtotal": round(cant * precio, 2)
                        })
                    st.success(f"✅ {producto_sel} agregado.")
                    st.rerun()

    with col2:
        st.subheader("Resumen de Venta")
        if not st.session_state.carrito:
            st.info("El carrito está vacío.")
        else:
            df_carrito = pd.DataFrame(st.session_state.carrito)
            st.table(df_carrito[['nombre', 'cantidad', 'precio', 'subtotal']])

            total_venta = round(sum(item['subtotal'] for item in st.session_state.carrito), 2)
            st.write(f"### Total: ${total_venta:,.2f}")

            medio_pago = st.selectbox("Medio de Pago", ["Efectivo", "Transferencia", "Tarjeta"])

            if st.button("✅ Finalizar Venta", type="primary", use_container_width=True):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute(
                        "INSERT INTO ventas (total, medio_pago, fecha) VALUES (%s, %s, NOW()) RETURNING id",
                        (total_venta, medio_pago)
                    )
                    venta_id = cur.fetchone()[0]

                    for item in st.session_state.carrito:
                        id_prod = int(item['id'])
                        cant = float(item['cantidad'])
                        precio = float(item['precio'])
                        subtotal = float(item['subtotal'])

                        cur.execute(
                            "INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)",
                            (venta_id, id_prod, cant, precio, subtotal)
                        )
                        cur.execute(
                            "UPDATE productos SET stock = stock - %s WHERE id = %s",
                            (cant, id_prod)
                        )
                        cur.execute(
                            "INSERT INTO movimientos (tipo, producto_id, cantidad, detalle, fecha) VALUES ('venta', %s, %s, %s, NOW())",
                            (id_prod, cant, f"Venta #{venta_id}")
                        )

                    conn.commit()
                    st.session_state.carrito = []
                    st.success("✅ Venta registrada con éxito.")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error al procesar la venta: {e}")
                finally:
                    conn.close()

            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
                    
