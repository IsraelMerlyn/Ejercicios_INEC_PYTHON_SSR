from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import (
    DEFAULT_COIN_IDS,
    SUPPORTED_CURRENCIES,
    settings,
)
from repositories.data_manager import DataManager
from services.analytics_engine import (
    add_moving_average,
    calculate_asset_kpis,
    format_money,
    latest_per_asset,
    top_gainers,
)
from services.data_fetcher import CoinGeckoClient
from utils.exceptions import DataSourceError

st.set_page_config(
    page_title="DataViz Dynamics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #E2E8F0;
            padding: 1rem;
            border-radius: 14px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
        }
        .subtitle {color: #475569; margin-top: -0.6rem;}
        .status-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 0.8rem 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_manager(database_path: str) -> DataManager:
    manager = DataManager(Path(database_path))
    manager.initialize_database()
    return manager


@st.cache_resource
def get_api_client(api_key: str) -> CoinGeckoClient:
    return CoinGeckoClient(
        base_url=settings.coingecko_base_url,
        api_key=api_key,
        timeout_seconds=settings.request_timeout_seconds,
        cache_ttl_seconds=settings.api_cache_ttl_seconds,
        minimum_request_interval_seconds=(
            settings.minimum_request_interval_seconds
        ),
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_assets(database_path: str) -> pd.DataFrame:
    return DataManager(Path(database_path)).get_assets()


@st.cache_data(ttl=30, show_spinner=False)
def load_history(database_path: str, currency: str) -> pd.DataFrame:
    return DataManager(Path(database_path)).get_history(currency=currency)


manager = get_manager(str(settings.database_path))

st.title("📊 DataViz Dynamics")
st.markdown(
    '<p class="subtitle">Dashboard de monitoreo de criptomonedas: API REST → SQLite → Analítica → Visualización.</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Controles")

    api_key = st.text_input(
        "CoinGecko Demo API Key",
        value=settings.coingecko_api_key,
        type="password",
        help="Se utiliza únicamente desde el backend Python y no se guarda en SQLite.",
    )

    currency = st.selectbox(
        "Moneda de consulta",
        options=list(SUPPORTED_CURRENCIES),
        index=list(SUPPORTED_CURRENCIES).index(settings.default_currency)
        if settings.default_currency in SUPPORTED_CURRENCIES
        else 0,
        format_func=lambda value: value.upper(),
    )

    update_clicked = st.button(
        "🔄 Actualizar desde CoinGecko",
        type="primary",
        width="stretch",
    )

    load_demo_clicked = st.button(
        "🧪 Cargar datos demo USD",
        width="stretch",
        help="Solo inserta datos cuando la base está completamente vacía.",
    )

    st.divider()
    st.caption(f"Base SQLite: `{settings.database_path.name}`")

if update_clicked:
    if not api_key:
        st.error(
            "Agrega una API Key Demo de CoinGecko en el sidebar o en tu archivo .env."
        )
    else:
        with st.spinner("Consultando CoinGecko y persistiendo el snapshot..."):
            try:
                client = get_api_client(api_key)
                fetch_result = client.fetch_markets(
                    coin_ids=DEFAULT_COIN_IDS,
                    currency=currency,
                    force_refresh=True,
                )
                save_result = manager.save_market_snapshot(
                    fetch_result.data,
                    currency,
                )
                manager.log_sync(
                    status="OK",
                    received_records=save_result["received_records"],
                    inserted_records=save_result["inserted_records"],
                    message=(
                        "Respuesta obtenida desde caché local del cliente."
                        if fetch_result.from_cache
                        else "Respuesta obtenida desde CoinGecko."
                    ),
                )
                st.cache_data.clear()
                st.success(
                    "Actualización completada: "
                    f"{save_result['inserted_records']} nuevos y "
                    f"{save_result['ignored_duplicates']} duplicados ignorados."
                )
            except (DataSourceError, ValueError) as exc:
                manager.log_sync(status="ERROR", message=str(exc))
                st.error(str(exc))

if load_demo_clicked:
    inserted = manager.seed_sample_data()
    st.cache_data.clear()
    if inserted:
        st.success(f"Se cargaron {inserted} registros de demostración en USD.")
    else:
        st.info("La base ya contiene datos; no se duplicó la carga demo.")

assets = load_assets(str(settings.database_path))
history = load_history(str(settings.database_path), currency)
last_sync = manager.get_last_sync()

if last_sync:
    st.markdown(
        f"""
        <div class="status-card">
            <strong>Última sincronización:</strong> {last_sync['synced_at']} ·
            <strong>Estado:</strong> {last_sync['status']} ·
            <strong>Insertados:</strong> {last_sync['inserted_records']}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

if history.empty:
    st.info(
        f"Aún no hay datos históricos en {currency.upper()}. "
        "Carga los datos demo en USD o agrega tu API Key y presiona Actualizar."
    )
    st.stop()

available_assets = (
    history[["asset_id", "name", "symbol", "market_cap_rank"]]
    .drop_duplicates("asset_id")
    .sort_values(["market_cap_rank", "name"], na_position="last")
)
asset_label_to_id = {
    f"{row['name']} ({row['symbol']})": row["asset_id"]
    for _, row in available_assets.iterrows()
}

with st.sidebar:
    default_labels = list(asset_label_to_id.keys())[:3]
    selected_labels = st.multiselect(
        "Activos",
        options=list(asset_label_to_id.keys()),
        default=default_labels,
    )

    minimum_date = history["recorded_at"].min().date()
    maximum_date = history["recorded_at"].max().date()
    selected_date_range = st.date_input(
        "Rango de fechas",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )

    moving_average_window = st.slider(
        "Ventana de media móvil",
        min_value=2,
        max_value=14,
        value=7,
    )

    use_log_scale = st.checkbox(
        "Escala logarítmica para precios",
        value=False,
    )

if not selected_labels:
    st.warning("Selecciona al menos un activo en el sidebar.")
    st.stop()

selected_asset_ids = [asset_label_to_id[label] for label in selected_labels]

if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
    selected_start_date, selected_end_date = selected_date_range
else:
    selected_start_date = selected_end_date = selected_date_range

filtered_history = history.loc[
    history["asset_id"].isin(selected_asset_ids)
    & (history["recorded_at"].dt.date >= selected_start_date)
    & (history["recorded_at"].dt.date <= selected_end_date)
].copy()

if filtered_history.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

primary_label = st.selectbox(
    "Activo principal para los KPIs",
    options=selected_labels,
)
primary_asset_id = asset_label_to_id[primary_label]
kpis = calculate_asset_kpis(filtered_history, primary_asset_id)

metric_columns = st.columns(4)
metric_columns[0].metric(
    "Precio actual",
    format_money(kpis["current_price"], currency),
    delta=f"{kpis['change_24h']:+.2f}% en 24 h",
)
metric_columns[1].metric(
    "Capitalización",
    format_money(kpis["market_cap"], currency),
)
metric_columns[2].metric(
    "Volumen 24 h",
    format_money(kpis["total_volume"], currency),
)
metric_columns[3].metric(
    "Volatilidad histórica",
    f"{kpis['volatility']:.2f}%",
    help="Desviación estándar de los rendimientos entre snapshots disponibles.",
)

st.subheader("Evolución temporal del precio")
history_with_average = add_moving_average(
    filtered_history,
    window=moving_average_window,
)

line_figure = px.line(
    history_with_average,
    x="recorded_at",
    y="current_price",
    color="name",
    markers=True,
    labels={
        "recorded_at": "Fecha y hora",
        "current_price": f"Precio ({currency.upper()})",
        "name": "Activo",
    },
    hover_data={
        "symbol": True,
        "price_change_percentage_24h": ":.2f",
        "recorded_at": "|%Y-%m-%d %H:%M UTC",
    },
)

primary_average = history_with_average.loc[
    history_with_average["asset_id"] == primary_asset_id
]
line_figure.add_trace(
    go.Scatter(
        x=primary_average["recorded_at"],
        y=primary_average["moving_average"],
        mode="lines",
        name=f"Media móvil {moving_average_window} · {kpis['name']}",
        line={"dash": "dash", "width": 3},
        hovertemplate="Media móvil: %{y:,.6f}<extra></extra>",
    )
)
line_figure.update_layout(
    hovermode="x unified",
    legend_title_text="Series",
    yaxis_type="log" if use_log_scale else "linear",
)
st.plotly_chart(line_figure, width="stretch")

chart_left, chart_right = st.columns([1, 1])

with chart_left:
    st.subheader("Cambio porcentual en 24 horas")
    latest = latest_per_asset(filtered_history)
    bar_figure = px.bar(
        latest.sort_values("price_change_percentage_24h"),
        x="name",
        y="price_change_percentage_24h",
        text_auto=".2f",
        labels={
            "name": "Activo",
            "price_change_percentage_24h": "Cambio 24 h (%)",
        },
        hover_data={"current_price": ":,.6f", "symbol": True},
    )
    bar_figure.update_layout(showlegend=False)
    st.plotly_chart(bar_figure, width="stretch")

with chart_right:
    st.subheader("Top de activos por ganancia")
    ranking = top_gainers(filtered_history, limit=5).copy()
    ranking["Cambio 24 h"] = ranking["price_change_percentage_24h"].map(
        lambda value: f"{value:+.2f}%" if pd.notna(value) else "N/D"
    )
    ranking["Precio"] = ranking["current_price"].map(
        lambda value: format_money(float(value), currency)
    )
    st.dataframe(
        ranking[["name", "symbol", "Precio", "Cambio 24 h"]].rename(
            columns={"name": "Activo", "symbol": "Símbolo"}
        ),
        width="stretch",
        hide_index=True,
    )

st.subheader("Datos integrados")
display_columns = [
    "recorded_at",
    "name",
    "symbol",
    "current_price",
    "market_cap",
    "total_volume",
    "price_change_percentage_24h",
    "currency",
]
st.dataframe(
    filtered_history[display_columns].sort_values(
        "recorded_at",
        ascending=False,
    ),
    width="stretch",
    hide_index=True,
)

csv_data = filtered_history[display_columns].to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Exportar datos filtrados a CSV",
    data=csv_data,
    file_name=f"crypto_dashboard_{currency}.csv",
    mime="text/csv",
)

st.caption(
    "Los datos demo son simulados. Los datos actualizados provienen de CoinGecko "
    "y se almacenan localmente en SQLite."
)
