# ... (Todo el código anterior de selección y PDF igual) ...

if st.session_state.cart:
    st.subheader("🛒 Items en Carrito")
    st.table(pd.DataFrame(st.session_state.cart)[["nombre", "cantidad", "subtotal"]])
    
    total_v = sum(i['subtotal'] for i in st.session_state.cart)
    metodo = st.selectbox("💳 Medio de Pago", ["Efectivo", "Tarjeta", "Transferencia", "QR"])
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("🗑️ Vaciar Carrito", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
            
    with col_c2:
        if st.button("✅ FINALIZAR VENTA", type="primary", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            try:
                # Guardamos una copia local para el PDF
                items_ticket = list(st.session_state.cart)
                
                for i in st.session_state.cart:
                    # Descontar Insumos y Producto (Conversión a tipos nativos)
                    cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (int(i['cantidad']), int(i['id'])))
                    
                    # Descontar Recetas si existen
                    cur.execute("SELECT insumo_id, cantidad FROM recetas WHERE plato_id = %s", (int(i['id']),))
                    for ins_id, cant_r in cur.fetchall():
                        cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (float(cant_r * i['cantidad']), ins_id))
                    
                    cur.execute("INSERT INTO movimientos (tipo, producto_id, cantidad, precio_unitario, total) VALUES ('venta',%s,%s,%s,%s)",
                              (int(i['id']), int(i['cantidad']), float(i['precio']), float(i['subtotal'])))
                
                cur.execute("INSERT INTO ventas (cajero, total, medio_pago, items) VALUES (%s,%s,%s,%s) RETURNING ticket_num",
                          (st.session_state.username, float(total_v), metodo, str(items_ticket)))
                
                n_ticket = cur.fetchone()[0]
                conn.commit()
                
                # --- AQUÍ ESTÁ EL CAMBIO ---
                # Generamos el PDF y lo guardamos ANTES de vaciar el carrito
                st.session_state.ticket_listo = generar_ticket_pdf(items_ticket, total_v, n_ticket, metodo)
                st.session_state.cart = [] 
                st.success(f"Venta registrada! Ticket #{n_ticket}")
                # No usamos st.rerun() aquí para que el flujo alcance el botón de abajo
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                conn.close()

# --- BLOQUE DE DESCARGA (Fuera de cualquier IF de carrito) ---
if st.session_state.ticket_listo is not None:
    st.divider()
    st.balloons()
    st.subheader("📄 Ticket Generado")
    
    # El botón de descarga
    st.download_button(
        label="📥 DESCARGAR / IMPRIMIR TICKET",
        data=st.session_state.ticket_listo,
        file_name=f"ticket_{datetime.now().strftime('%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )
    
    if st.button("🔄 Preparar Nueva Venta", use_container_width=True):
        st.session_state.ticket_listo = None
        st.rerun()
