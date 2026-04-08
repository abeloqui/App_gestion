import streamlit as st
import pandas as pd
from database import get_engine

st.header("🏁 Cierre de Caja")
engine = get_engine()
hoy = pd.Timestamp.now().date()

df = pd.read_sql(f"SELECT medio_pago, SUM(total) as total FROM ventas WHERE fecha >= '{hoy}' GROUP BY medio_pago", engine)

if not df.empty:
    st.subheader(f"Resumen de Hoy: {hoy}")
    st.dataframe(df, use_container_width=True)
    
    efectivo = df[df['medio_pago'] == 'Efectivo']['total'].sum() if 'Efectivo' in df['medio_pago'].values else 0
    st.info(f"💵 Efectivo esperado en caja: **${efectivo:,.2f}**")
    
    contado = st.number_input("Monto contado físicamente", min_value=0.0)
    if st.button("Finalizar Turno"):
        diff = contado - efectivo
        if diff == 0: st.success("Caja cuadrada.")
        else: st.warning(f"Diferencia: ${diff:,.2f}")
else:
    st.write("No hay ventas registradas hoy.")
