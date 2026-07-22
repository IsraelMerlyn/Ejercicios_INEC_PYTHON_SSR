from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import settings
from repositories.data_manager import DataManager
from services.analytics_engine import (
    METRIC_LABELS,
    build_type_distribution,
    calculate_pokemon_kpis,
    calculate_summary_kpis,
    enrich_pokemon_data,
    prepare_ranking,
)
from services.data_fetcher import PokeAPIClient
from utils.exceptions import DataSourceError, DataValidationError

st.set_page_config(
    page_title="PokéData Lab",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        .hero {
            padding: 1.5rem 1.75rem;
            border: 1px solid rgba(128,128,128,.22);
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(255,203,5,.16), rgba(61,125,202,.10));
            margin-bottom: 1rem;
        }
        .hero h1 {margin: 0 0 .35rem 0;}
        .muted {opacity: .75;}
        .sync-card {
            padding: .8rem 1rem;
            border-radius: 12px;
            border: 1px solid rgba(128,128,128,.20);
            margin-bottom: 1rem;
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
def get_api_client() -> PokeAPIClient:
    return PokeAPIClient(
        base_url=settings.pokeapi_base_url,
        timeout_seconds=settings.request_timeout_seconds,
        cache_ttl_seconds=settings.api_cache_ttl_seconds,
        minimum_request_interval_seconds=(
            settings.minimum_request_interval_seconds
        ),
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_data(database_path: str) -> pd.DataFrame:
    raw = DataManager(Path(database_path)).get_pokemon_data()
    return enrich_pokemon_data(raw)


manager = get_manager(str(settings.database_path))

st.markdown(
    """
    <section class="hero">
        <h1>⚡ PokéData Lab</h1>
        <div class="muted">
            Dashboard educativo: PokéAPI REST → validación Python → SQLite → analítica → Streamlit.
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Sincronización")
    fetch_limit = st.slider(
        "Cantidad a descargar",
        min_value=10,
        max_value=50,
        value=20,
        step=10,
        help="PokéAPI entrega una lista paginada y después consultamos el detalle de cada Pokémon.",
    )
    fetch_offset = st.number_input(
        "Desplazamiento (offset)",
        min_value=0,
        max_value=1000,
        value=0,
        step=10,
    )
    update_clicked = st.button(
        "🔄 Actualizar desde PokéAPI",
        type="primary",
        width="stretch",
    )
    demo_clicked = st.button(
        "🧪 Cargar datos demo",
        width="stretch",
        help="Carga información local si la base todavía está vacía.",
    )
    st.caption("No requiere cuenta, token ni API key.")
    st.divider()
    st.caption(f"SQLite: `{settings.database_path.name}`")

if update_clicked:
    with st.spinner(
        f"Descargando hasta {fetch_limit} Pokémon y guardando relaciones..."
    ):
        try:
            fetch_result = get_api_client().fetch_pokemon(
                limit=int(fetch_limit),
                offset=int(fetch_offset),
                force_refresh=True,
            )
            save_result = manager.save_pokemon_batch(fetch_result.data)
            manager.log_sync(
                status="OK",
                requested_records=save_result["requested_records"],
                valid_records=save_result["valid_records"],
                inserted_records=save_result["inserted_records"],
                updated_records=save_result["updated_records"],
                failed_resources=len(fetch_result.failed_resources),
                message=(
                    "Datos obtenidos desde caché."
                    if fetch_result.from_cache
                    else "Datos obtenidos desde PokéAPI."
                ),
            )
            st.cache_data.clear()
            st.success(
                "Sincronización completada: "
                f"{save_result['inserted_records']} nuevos, "
                f"{save_result['updated_records']} actualizados y "
                f"{len(fetch_result.failed_resources)} fallidos."
            )
        except (DataSourceError, DataValidationError, ValueError) as exc:
            manager.log_sync(status="ERROR", message=str(exc))
            st.error(str(exc))

if demo_clicked:
    inserted = manager.seed_sample_data()
    st.cache_data.clear()
    if inserted:
        st.success(f"Se insertaron {inserted} Pokémon de demostración.")
    else:
        st.info("La base ya tiene información; no se duplicaron los datos demo.")

data = load_data(str(settings.database_path))
last_sync = manager.get_last_sync()

if last_sync:
    st.markdown(
        f"""
        <div class="sync-card">
            <strong>Última sincronización:</strong> {last_sync['synced_at']} ·
            <strong>Estado:</strong> {last_sync['status']} ·
            <strong>Nuevos:</strong> {last_sync['inserted_records']} ·
            <strong>Actualizados:</strong> {last_sync['updated_records']}
        </div>
        """,
        unsafe_allow_html=True,
    )

if data.empty:
    st.info(
        "Aún no hay información. Presiona **Cargar datos demo** o "
        "**Actualizar desde PokéAPI** para comenzar."
    )
    st.stop()

available_types = sorted(
    {
        type_name
        for types_text in data["types"]
        for type_name in str(types_text).split(", ")
        if type_name
    }
)
available_generations = sorted(data["generation"].dropna().astype(int).unique())

with st.sidebar:
    st.header("Filtros")
    selected_types = st.multiselect(
        "Tipos",
        options=available_types,
        default=[],
        placeholder="Todos los tipos",
    )
    selected_generations = st.multiselect(
        "Generaciones",
        options=available_generations,
        default=available_generations,
        format_func=lambda value: f"Generación {value}",
    )
    metric = st.selectbox(
        "Métrica del ranking",
        options=list(METRIC_LABELS),
        format_func=lambda value: METRIC_LABELS[value],
    )
    ranking_limit = st.slider("Elementos del ranking", 5, 20, 10)

filtered = data.loc[data["generation"].isin(selected_generations)].copy()
if selected_types:
    filtered = filtered.loc[
        filtered["types"].apply(
            lambda text: bool(set(str(text).split(", ")) & set(selected_types))
        )
    ].copy()

if filtered.empty:
    st.warning("No hay Pokémon para los filtros seleccionados.")
    st.stop()

summary = calculate_summary_kpis(filtered)
summary_columns = st.columns(4)
summary_columns[0].metric("Pokémon analizados", summary["total"])
summary_columns[1].metric(
    "Experiencia promedio",
    f"{summary['average_experience']:.1f}",
)
summary_columns[2].metric(
    "Peso promedio",
    f"{summary['average_weight']:.1f} kg",
)
summary_columns[3].metric(
    "Mayor poder total",
    summary["strongest_name"],
    delta=f"{summary['strongest_total']} puntos",
)

st.divider()

pokemon_options = {
    f"#{int(row.id):03d} · {row.name}": int(row.id)
    for row in filtered[["id", "name"]].itertuples(index=False)
}
selected_label = st.selectbox(
    "Pokémon destacado",
    options=list(pokemon_options),
)
selected_id = pokemon_options[selected_label]
selected_kpis = calculate_pokemon_kpis(filtered, selected_id)
selected_row = filtered.loc[filtered["id"] == selected_id].iloc[0]

image_column, detail_column = st.columns([1, 4])
with image_column:
    if selected_kpis["image_url"]:
        st.image(selected_kpis["image_url"], width=180)
with detail_column:
    st.subheader(selected_kpis["name"])
    detail_metrics = st.columns(4)
    detail_metrics[0].metric(
        "Experiencia base",
        f"{selected_kpis['base_experience']:.0f}",
    )
    detail_metrics[1].metric("Altura", f"{selected_kpis['height_m']:.1f} m")
    detail_metrics[2].metric("Peso", f"{selected_kpis['weight_kg']:.1f} kg")
    detail_metrics[3].metric("Poder total", f"{selected_kpis['total_stats']:.0f}")
    st.caption(f"Tipos: {selected_kpis['types']}")

radar_labels = [
    "HP",
    "Ataque",
    "Defensa",
    "At. especial",
    "Def. especial",
    "Velocidad",
]
radar_values = [
    selected_row["hp"],
    selected_row["attack"],
    selected_row["defense"],
    selected_row["special_attack"],
    selected_row["special_defense"],
    selected_row["speed"],
]
radar_figure = go.Figure(
    data=[
        go.Scatterpolar(
            r=radar_values + [radar_values[0]],
            theta=radar_labels + [radar_labels[0]],
            fill="toself",
            name=selected_kpis["name"],
            hovertemplate="%{theta}: %{r}<extra></extra>",
        )
    ]
)
radar_figure.update_layout(
    polar={"radialaxis": {"visible": True, "range": [0, max(180, max(radar_values) + 10)]}},
    showlegend=False,
    height=420,
    margin={"l": 40, "r": 40, "t": 30, "b": 30},
)

ranking = prepare_ranking(filtered, metric, ranking_limit)
ranking_figure = px.bar(
    ranking.sort_values(metric),
    x=metric,
    y="name",
    orientation="h",
    text_auto=".1f",
    labels={metric: METRIC_LABELS[metric], "name": "Pokémon"},
    hover_data={"types": True, "generation": True},
    title=f"Top {ranking_limit}: {METRIC_LABELS[metric]}",
)

chart_left, chart_right = st.columns(2)
with chart_left:
    st.subheader("Perfil de estadísticas")
    st.plotly_chart(radar_figure, width="stretch")
with chart_right:
    st.plotly_chart(ranking_figure, width="stretch")

scatter_figure = px.scatter(
    filtered,
    x="height_m",
    y="weight_kg",
    size="total_stats",
    color="primary_type",
    hover_name="name",
    hover_data={
        "base_experience": True,
        "generation": True,
        "total_stats": True,
        "height_m": ":.1f",
        "weight_kg": ":.1f",
    },
    labels={
        "height_m": "Altura (m)",
        "weight_kg": "Peso (kg)",
        "primary_type": "Tipo principal",
    },
    title="Relación entre altura, peso y poder total",
)

type_distribution = build_type_distribution(filtered)
type_figure = px.pie(
    type_distribution,
    names="type",
    values="pokemon_count",
    hole=0.5,
    title="Distribución por tipo",
)

chart_left, chart_right = st.columns([1.35, 1])
with chart_left:
    st.plotly_chart(scatter_figure, width="stretch")
with chart_right:
    st.plotly_chart(type_figure, width="stretch")

st.subheader("Datos integrados desde SQLite")
display_columns = [
    "id",
    "name",
    "types",
    "generation",
    "base_experience",
    "height_m",
    "weight_kg",
    "hp",
    "attack",
    "defense",
    "special_attack",
    "special_defense",
    "speed",
    "total_stats",
]
st.dataframe(
    filtered[display_columns].sort_values("id"),
    width="stretch",
    hide_index=True,
)

csv_data = filtered[display_columns].to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Exportar selección a CSV",
    data=csv_data,
    file_name="pokemon_dashboard.csv",
    mime="text/csv",
)

st.caption(
    "Los datos demo permiten trabajar sin conexión. Al actualizar, los datos "
    "se obtienen desde PokéAPI y se persisten en SQLite."
)
