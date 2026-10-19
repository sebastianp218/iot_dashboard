import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
import time

# ---------------------------
# CONFIG
# ---------------------------
url = "https://us-east-1-1.aws.cloud2.influxdata.com"
token = "5FESPQw5t4qA4GgZmyeZ9mu7u1sbtauo4Hh8tjRi1E8sdrIgzXAX5ESk4n5MmcpAjJWEGgEKklFX0LNasnUmng=="
org = "miguelcmo"
bucket = "iot_telemetry_data"

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="IoT Dashboard",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ IoT Telemetry Dashboard")
st.markdown("Monitoreo de temperatura y humedad en tiempo real")

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.header("⚙️ Configuración")

time_range = st.sidebar.selectbox(
    "Rango de tiempo",
    ["-1h", "-6h", "-12h", "-24h", "-7d"],
    index=3
)

refresh = st.sidebar.slider(
    "Auto-refresh (segundos)",
    0,
    60,
    10
)

st.sidebar.subheader("🚨 Límites de temperatura")

temp_min = st.sidebar.slider(
    "Temperatura mínima",
    10.0,
    30.0,
    20.0
)

temp_max = st.sidebar.slider(
    "Temperatura máxima",
    20.0,
    40.0,
    28.0
)

# ---------------------------
# DATA FUNCTION
# ---------------------------
@st.cache_data(ttl=10)
def load_data(time_range):

    client = InfluxDBClient(
        url=url,
        token=token,
        org=org
    )

    query_api = client.query_api()

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {time_range})
      |> filter(fn: (r) =>
          r["_field"] == "temperature" or
          r["_field"] == "humidity"
      )
      |> pivot(
          rowKey:["_time"],
          columnKey: ["_field"],
          valueColumn: "_value"
      )
      |> keep(
          columns: [
              "_time",
              "temperature",
              "humidity"
          ]
      )
    '''

    result = query_api.query_data_frame(query)

    if isinstance(result, list):
        df = pd.concat(result)
    else:
        df = result

    if df.empty:
        return df

    df["_time"] = pd.to_datetime(df["_time"])

    df["temperature"] = pd.to_numeric(
        df["temperature"],
        errors="coerce"
    )

    df["humidity"] = pd.to_numeric(
        df["humidity"],
        errors="coerce"
    )

    df = df.sort_values("_time")

    return df


# ---------------------------
# LOAD DATA
# ---------------------------
df = load_data(time_range)

if not df.empty:

    temperatura_actual = df["temperature"].iloc[-1]
    humedad_actual = df["humidity"].iloc[-1]

    # ---------------------------
    # ESTADO
    # ---------------------------
    if temperatura_actual < temp_min:
        estado = "🔵 TEMPERATURA BAJA"

    elif temperatura_actual > temp_max:
        estado = "🔴 TEMPERATURA ALTA"

    else:
        estado = "🟢 OPERACIÓN NORMAL"

    st.subheader("Estado del sistema")

    st.info(estado)

    # ---------------------------
    # METRICS
    # ---------------------------
    st.subheader("📊 Variables actuales")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "🌡️ Temperatura actual",
        f"{temperatura_actual:.2f} °C"
    )

    col2.metric(
        "💧 Humedad actual",
        f"{humedad_actual:.2f} %"
    )

    col3.metric(
        "📈 Temperatura promedio",
        f"{df['temperature'].mean():.2f} °C"
    )

    col4.metric(
        "📈 Humedad promedio",
        f"{df['humidity'].mean():.2f} %"
    )

    # ---------------------------
    # TEMPERATURE CHART
    # ---------------------------
    st.subheader("🌡️ Temperatura")

    fig_temp = px.line(
        df,
        x="_time",
        y="temperature",
        title="Evolución de la temperatura"
    )

    st.plotly_chart(
        fig_temp,
        use_container_width=True
    )

    # ---------------------------
    # HUMIDITY CHART
    # ---------------------------
    st.subheader("💧 Humedad")

    fig_hum = px.line(
        df,
        x="_time",
        y="humidity",
        title="Evolución de la humedad"
    )

    st.plotly_chart(
        fig_hum,
        use_container_width=True
    )

    # ---------------------------
    # RESAMPLING
    # ---------------------------
    st.subheader("⏱️ Promedio cada 10 minutos")

    df_resampled = (
        df.set_index("_time")[
            ["temperature", "humidity"]
        ]
        .resample("10min")
        .mean()
        .dropna()
    )

    fig_avg = px.line(
        df_resampled,
        x=df_resampled.index,
        y=["temperature", "humidity"],
        title="Promedio de temperatura y humedad cada 10 minutos"
    )

    st.plotly_chart(
        fig_avg,
        use_container_width=True
    )

    # ---------------------------
    # RAW DATA
    # ---------------------------
    st.subheader("📋 Datos almacenados")

    st.dataframe(
        df.tail(50),
        use_container_width=True
    )

    # ---------------------------
    # DOWNLOAD
    # ---------------------------
    csv = df.to_csv(index=False)

    st.download_button(
        label="📥 Descargar datos CSV",
        data=csv,
        file_name="datos_iot.csv",
        mime="text/csv"
    )

else:

    st.warning(
        "No hay datos disponibles para el rango seleccionado."
    )

# ---------------------------
# AUTO REFRESH
# ---------------------------
if refresh > 0:
    time.sleep(refresh)
    st.rerun()
