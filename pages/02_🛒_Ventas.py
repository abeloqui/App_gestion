import streamlit as st
import pandas as pd
from database import get_connection, get_engine  # <-- Aquí estaba el error, faltaba importar get_engine

st.set_page_config(page_title="Punto de Venta", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Inicia sesión en la página principal.")
    st.stop()

st.header("🛒 Punto de Venta")

# --- SELECCIÓN DE PRODUCTOS ---
engine = get_engine()
try:
    # Solo mostramos productos con stock y que sean 'Producto Final'
    df_p = pd.read_sql("""
        SELECT id, nombre, precio_venta, stock 
        FROM productos 
        WHERE stock > 0 AND subcategoria = 'Producto Final' 
        ORDER BY nombre
    """, engine)
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

if df_p.empty:
    st.warning("No hay 'Productos Finales' con stock disponible para vender.")
else:
    # Inicializar el carrito en la sesión si no existe
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Seleccionar Productos")
        with st.form("form_venta"):
            producto_sel = st.selectbox("Producto", df_p['nombre'].tolist())
            cantidad = st.number_input("Cantidad", min_value=1, step=1)
            
            if st.form_submit_button("Agregar al Carrito"):
                prod_info = df_p[df_p['nombre'] == producto_sel].iloc[0]
                
                # Verificar si hay stock suficiente antes de agregar
                if cantidad > prod_info['stock']:
                    st.error(f"Stock insuficiente. Solo quedan {prod_info['stock']} unidades.")
                else:
                    st.session_state.carrito.append({
                        "id": int(prod_info['id']),
                        "nombre": producto_sel,
                        "cantidad": cantidad,
                        "precio": float(prod_info['precio_venta']),
                        "subtotal": cantidad * float(prod_info['precio_venta'])
                    })
                    st.success(f"Agregado: {producto_sel}")
                    st.rerun()

    with col2:
        st.subheader("Resumen de Venta")
        if not st.session_state.carrito:
            st.info("El carrito está vacío.")
        else:
            df_carrito = pd.DataFrame(st.session_state.carrito)
            st.table(df_carrito[['nombre', 'cantidad', 'subtotal']])
            
            total_venta = df_carrito['subtotal'].sum()
            st.write(f"### Total: ${total_venta:,.2f}")
            
            medio_pago = st.selectbox("Medio de Pago", ["Efectivo", "Transferencia", "Tarjeta"])

            if st.button("Finalizar Venta", type="primary", use_container_width=True):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    # 1. Registrar la Venta (Cabecera)
                    cur.execute("""
                        INSERT INTO ventas (total, medio_pago, fecha) 
                        VALUES (%s, %s, NOW()) RETURNING id
                    """, (total_venta, medio_pago))
                    venta_id = cur.fetchone()[0]

                    # 2. Registrar Detalles y Descontar Stock
                    for item in st.session_state.carrito:
                        # Insertar detalle
                        cur.execute("""
                            INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (venta_id, item['id'], item['cantidad'], item['precio'], item['subtotal']))

                        # Descontar stock
                        cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", 
                                   (item['cantidad'], item['id']))
                        
                        # Registrar movimiento
                        cur.execute("""
                            INSERT INTO movimientos (tipo, producto_id, cantidad, detalle)
                            VALUES ('venta', %s, %s, %s)
                        """, (item['id'], item['cantidad'], f"Venta ID: {venta_id}"))

                    conn.commit()
                    st.session_state.carrito = [] # Limpiar carrito
                    st.success("✅ Venta realizada con éxito.")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error al procesar la venta: {e}")
                finally:
                    conn.close()

            if st.button("Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
