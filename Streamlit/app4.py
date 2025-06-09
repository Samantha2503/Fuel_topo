import streamlit as st
import pandas as pd
import altair as alt
import joblib
import folium
from streamlit_folium import st_folium
import random


# Configuración inicial
st.set_page_config(page_title="Predicción Flotilla", layout="centered")

# Cargar modelos y datos históricos (ajusta rutas)
modelo_principal = joblib.load('modelo_rf.pkl')
vin_encoder = joblib.load('vin_encoder.pkl')
cc_encoder = joblib.load('cc_encoder.pkl')

modelos_secundarios = {
    'KG C02': joblib.load('modelo_KG C02.pkl'),
    'TON C02': joblib.load('modelo_TON C02.pkl'),
    'Arboles': joblib.load('modelo_Arboles.pkl'),
    'Importe Transacción': joblib.load('modelo_Importe Transacción.pkl'),
    'Rendimiento': joblib.load('modelo_Rendimiento.pkl'),
}

precio_por_defecto = 20.0

df_hist = pd.read_csv('data_processed.csv', parse_dates=['mes'])  # Ajusta columna fecha

def mostrar_historial_ambiental(vin_code, cc_code, df_hist):
    df_filtrado = df_hist[(df_hist['VIN_CODE'] == vin_code) & (df_hist['CC_CODE'] == cc_code)]
    
    if df_filtrado.empty:
        st.warning("No hay datos históricos para este vehículo y región.")
        return
    
    base = alt.Chart(df_filtrado).encode(x='mes:T')

    chart_kg = base.mark_line(color='green').encode(
        y='KG C02:Q',
        tooltip=['mes', 'KG C02']
    ).properties(title='KG CO2 Histórico')

    chart_ton = base.mark_line(color='blue').encode(
        y='TON C02:Q',
        tooltip=['mes', 'TON C02']
    ).properties(title='TON CO2 Histórico')

    chart_arboles = base.mark_line(color='brown').encode(
        y='Arboles:Q',
        tooltip=['mes', 'Arboles']
    ).properties(title='Árboles equivalentes históricos')

    st.altair_chart(chart_kg, use_container_width=True)
    st.altair_chart(chart_ton, use_container_width=True)
    st.altair_chart(chart_arboles, use_container_width=True)

# Sidebar con iframes de precios (mantener si quieres)

st.sidebar.header("Precios de Gasolina por Tipo - Tabasco")
st.sidebar.markdown("""
**Regular**
<iframe src="https://petrointelligence.com/api/api_precios.html?consulta=estado&estado=TAB&tipo=REG" 
        width="300" height="200" frameborder="0"></iframe>
""", unsafe_allow_html=True)
st.sidebar.markdown("""
**Premium**
<iframe src="https://petrointelligence.com/api/api_precios.html?consulta=estado&estado=TAB&tipo=PRE" 
        width="300" height="200" frameborder="0"></iframe>
""", unsafe_allow_html=True)
st.sidebar.markdown("""
**Diesel**
<iframe src="https://petrointelligence.com/api/api_precios.html?consulta=estado&estado=TAB&tipo=DIE" 
        width="300" height="200" frameborder="0"></iframe>
""", unsafe_allow_html=True)

# Crear pestañas
tab1, tab2 = st.tabs(["Predicción", "Análisis Flotilla"])

with tab1:
    st.title("🚛 Predicción de Desempeño por Vehículo")

    recorrido = st.number_input("Recorrido estimado (km)", min_value=0.0)
    precio = st.number_input("Precio unitario del combustible", min_value=0.0, value=precio_por_defecto)
    mes = st.slider("Mes", 1, 12, 6)
    dia_semana = st.slider("Día de la semana (0=lunes)", 0, 6, 2)
    vin_input = st.text_input("VIN NUMBER")
    cc_input = st.text_input("CC (ej. MX10001)")

    if st.button("🔍 Predecir desempeño"):
        try:
            vin_code = vin_encoder.transform([vin_input])[0]
            cc_code = cc_encoder.transform([cc_input])[0]

            entrada = pd.DataFrame([{
                'Recorrido': recorrido,
                'Precio Unitario': precio,
                'mes': mes,
                'dia_semana': dia_semana,
                'VIN_CODE': vin_code,
                'CC_CODE': cc_code
            }])

            cantidad_pred = modelo_principal.predict(entrada)[0]
            st.success(f"📦 Cantidad de mercancía estimada: **{cantidad_pred:.2f} unidades**")

            entrada_impacto = pd.DataFrame([{
                'Cantidad Mercancía': cantidad_pred,
                'Recorrido': recorrido,
                'VIN_CODE': vin_code,
                'CC_CODE': cc_code
            }])

            st.markdown("---")
            st.subheader("🌿 Impacto Ambiental y 💰 Costos Estimados")
            for nombre, modelo in modelos_secundarios.items():
                valor = modelo.predict(entrada_impacto)[0]
                st.metric(label=nombre, value=f"{valor:.2f}")

            st.markdown("---")
            st.subheader("📈 Desempeño Ambiental Histórico para este Vehículo y Región")
            mostrar_historial_ambiental(vin_code, cc_code, df_hist)

        except Exception as e:
            st.error(f"❌ VIN o CC no reconocidos o error en la predicción. {e}")

with tab2:
    st.title("📊 Análisis Estadístico de la Flotilla")

    # 1. Cantidad promedio de mercancía repartida por zona
    zona_promedio = df_hist.groupby('CC')['Cantidad Mercancía'].mean().sort_values(ascending=False).reset_index()

    st.subheader("Cantidad promedio de mercancía repartida por zona")
    st.markdown("Este gráfico muestra el promedio de mercancía que se entrega en cada zona.")

    chart1 = alt.Chart(zona_promedio).mark_bar(color='#4CAF50').encode(
        x=alt.X('CC:N', title='Zona (CC)', sort='-y'),
        y=alt.Y('Cantidad Mercancía:Q', title='Promedio Cantidad Mercancía'),
        tooltip=[alt.Tooltip('CC:N', title='Zona'), alt.Tooltip('Cantidad Mercancía:Q', title='Promedio')]
    ).properties(width=700, height=350)

    st.altair_chart(chart1, use_container_width=True)


    # 2. Top 5 vehículos con mayor promedio de mercancía (sin distinguir zona para simplificar)
    vin_placa_promedio = df_hist.groupby(['VIN NUMBER', 'Placa'])['Cantidad Mercancía'].mean().reset_index()

    # Ordenar y tomar top 5
    top5_vehiculos = vin_placa_promedio.sort_values(by='Cantidad Mercancía', ascending=False).head(5)

    st.subheader("Top 5 vehículos con mayor promedio de mercancía entregada (VIN + Placa)")
    st.markdown("Estos son los vehículos (identificados por VIN y Placa) que entregan más mercancía en promedio.")

    chart_top5 = alt.Chart(top5_vehiculos).mark_bar(color='#2196F3').encode(
        x=alt.X('Placa:N', title='Placa', sort='-y'),
        y=alt.Y('Cantidad Mercancía:Q', title='Promedio Cantidad Mercancía'),
        tooltip=[
            alt.Tooltip('VIN NUMBER:N', title='VIN Number'),
            alt.Tooltip('Placa:N', title='Placa'),
            alt.Tooltip('Cantidad Mercancía:Q', title='Promedio')
        ]
    ).properties(width=700, height=350)

    st.altair_chart(chart_top5, use_container_width=True)


    # Agrupar frecuencia por Estado, VIN NUMBER, Placa y CC
    freq_df = df_hist.groupby(['Estado', 'VIN NUMBER', 'Placa', 'CC']).size().reset_index(name='Frecuencia')

    # Diccionario de colores para diferenciar vehículos (puedes mejorar asignación)
    random.seed(42)
    vehiculos = freq_df['VIN NUMBER'].unique()
    colores = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 
            'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue',
            'lightgreen', 'gray', 'black', 'lightgray']
    color_map = {v: colores[i % len(colores)] for i, v in enumerate(vehiculos)}

    # Centrar mapa en México
    mapa = folium.Map(location=[23.6345, -102.5528], zoom_start=5)

    # Puedes crear un diccionario con coordenadas por Estado (simplificado con capitales)
    coordenadas_estados = {
        'Tabasco': [17.9894, -92.9470],
        'Tamaulipas': [23.7369, -99.1411],
        'Veracruz': [19.1738, -96.1342],
        'Cd Mexico': [19.4326, -99.1332],
        # Agrega más estados si tienes
    }

    # Agregar círculos por frecuencia
    for _, row in freq_df.iterrows():
        estado = row['Estado']
        vin = row['VIN NUMBER']
        placa = row['Placa']
        cc = row['CC']
        freq = row['Frecuencia']
        color = color_map[vin]

        if estado in coordenadas_estados:
            lat, lon = coordenadas_estados[estado]
            folium.CircleMarker(
                location=[lat, lon],
                radius=5 + freq * 0.5,  # tamaño relativo a frecuencia
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=f"Vehículo: {vin}\nPlaca: {placa}\nCC: {cc}\nEstado: {estado}\nFrecuencia: {freq}"
            ).add_to(mapa)

    st.subheader("Mapa de frecuencia por estado y vehículo")
    st.markdown("Cada círculo representa la frecuencia de entregas o registros por estado para cada vehículo. El tamaño está relacionado con la frecuencia.")

    # Mostrar mapa en Streamlit
    st_data = st_folium(mapa, width=700, height=500)


