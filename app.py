from __future__ import annotations

from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st


DATA_PATH = Path(__file__).with_name("zillow.csv")
CURRENT_YEAR = datetime.now().year
PRIMARY = "#2563eb"
TEAL = "#0f766e"
AMBER = "#d97706"
ROSE = "#be123c"
SLATE = "#334155"
PALETTE = [PRIMARY, TEAL, AMBER, ROSE, "#7c3aed", "#0891b2", "#65a30d", "#475569"]


st.set_page_config(
    page_title="Greater Savannah Housing Market Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --accent: #2563eb;
            --ink: #0f172a;
            --muted: #64748b;
            --line: #e2e8f0;
            --panel: #ffffff;
            --soft: #f8fafc;
        }

        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
            color: var(--ink);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1440px;
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--ink);
        }

        .dashboard-hero {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1.15rem 1.25rem;
            background: var(--panel);
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
            margin-bottom: 1rem;
        }

        .eyebrow {
            color: var(--accent);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }

        .dashboard-title {
            color: var(--ink);
            font-size: 2rem;
            font-weight: 750;
            line-height: 1.18;
            margin: 0;
        }

        .dashboard-subtitle {
            color: var(--muted);
            font-size: 1rem;
            margin-top: 0.45rem;
            max-width: 900px;
        }

        .kpi-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.95rem 1rem;
            background: var(--panel);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            min-height: 104px;
        }

        .kpi-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 650;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .kpi-value {
            color: var(--ink);
            font-size: 1.62rem;
            font-weight: 750;
            line-height: 1.1;
        }

        .kpi-note {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 0.4rem;
        }

        .section-title {
            color: var(--ink);
            font-size: 1.2rem;
            font-weight: 725;
            margin: 1.25rem 0 0.35rem;
        }

        .section-copy {
            color: var(--muted);
            font-size: 0.92rem;
            margin: 0 0 0.85rem;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.85rem 0.95rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
            border-bottom: 1px solid var(--line);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 6px 6px 0 0;
            padding: 0.65rem 0.9rem;
            color: var(--muted);
        }

        .stTabs [aria-selected="true"] {
            color: var(--accent);
            background: #ffffff;
            border: 1px solid var(--line);
            border-bottom: 1px solid #ffffff;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, copy: str) -> None:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<p class='section-copy'>{copy}</p>", unsafe_allow_html=True)


def render_hero(df: pd.DataFrame) -> None:
    price_min = money(df["price"].min())
    price_max = money(df["price"].max())
    city_count = df["city"].nunique(dropna=True)
    st.markdown(
        f"""
        <div class="dashboard-hero">
            <div class="eyebrow">Greater Savannah Market Intelligence</div>
            <h1 class="dashboard-title">Housing Market Dashboard</h1>
            <div class="dashboard-subtitle">
                Explore {len(df):,} for-sale listings across {city_count:,} cities, with prices from {price_min} to {price_max}.
                Use the sidebar filters to narrow the market by city, ZIP code, property type, price, size, and listing age.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(column, label: str, value: str, note: str = "") -> None:
    note_html = f"<div class='kpi-note'>{note}</div>" if note else ""
    column.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_config(chart: alt.Chart) -> alt.Chart:
    return chart.configure_axis(
        gridColor="#e2e8f0",
        labelColor=SLATE,
        titleColor=SLATE,
        domainColor="#cbd5e1",
        tickColor="#cbd5e1",
    ).configure_title(
        color="#0f172a",
        fontSize=15,
        fontWeight=700,
        anchor="start",
        offset=12,
    ).configure_view(
        strokeWidth=0,
    ).configure_legend(
        labelColor=SLATE,
        titleColor=SLATE,
        orient="bottom",
    )


@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.rename(
        columns={
            "address.streetAddress": "street",
            "address.city": "city",
            "address.state": "state",
            "address.zipcode": "zipcode",
            "propertyTypeDimension": "property_type",
            "livingArea": "living_area",
            "resoFacts.daysOnZillow": "days_on_zillow",
        }
    )

    numeric_columns = [
        "price",
        "living_area",
        "rentZestimate",
        "rentAverage",
        "monthlyHoaFee",
        "days_on_zillow",
        "bedrooms",
        "bathrooms",
        "yearBuilt",
        "latitude",
        "longitude",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["datePosted"] = pd.to_datetime(df["datePosted"], errors="coerce")
    df["zipcode"] = df["zipcode"].astype("string").str.replace(r"\.0$", "", regex=True)
    df["price_per_sqft"] = df["price"] / df["living_area"].where(df["living_area"] > 0)
    df["property_age"] = CURRENT_YEAR - df["yearBuilt"]
    df["listing_age_band"] = pd.cut(
        df["days_on_zillow"],
        bins=[-1, 14, 30, 60, 90, float("inf")],
        labels=["0-14 days", "15-30 days", "31-60 days", "61-90 days", "90+ days"],
    )
    df["listing_url"] = "https://www.zillow.com" + df["url"].astype(str)
    return df


def money(value: float | int | None) -> str:
    if pd.isna(value):
        return "N/A"
    return f"${value:,.0f}"


def number(value: float | int | None) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def get_range(series: pd.Series, fallback: tuple[int, int]) -> tuple[float, float]:
    clean = series.dropna()
    if clean.empty:
        return fallback
    low = float(clean.min())
    high = float(clean.max())
    if low == high:
        high = low + 1
    return low, high


def filtered_options(series: pd.Series) -> list[str]:
    return sorted(series.dropna().astype(str).unique().tolist())


def clipped_frame(df: pd.DataFrame, columns: list[str], upper_quantile: float = 0.99) -> pd.DataFrame:
    clipped = df.copy()
    for column in columns:
        if column in clipped and clipped[column].notna().any():
            upper = clipped[column].quantile(upper_quantile)
            clipped = clipped[clipped[column].isna() | (clipped[column] <= upper)]
    return clipped


def bar_chart(data: pd.DataFrame, x: str, y: str, title: str, *, horizontal: bool = False) -> alt.Chart:
    x_encoding = alt.X(f"{x}:Q", title=x.replace("_", " ").title()) if horizontal else alt.X(f"{x}:N", title="")
    y_encoding = alt.Y(f"{y}:N", title="", sort="-x") if horizontal else alt.Y(f"{y}:Q", title=y.replace("_", " ").title())
    return chart_config(
        alt.Chart(data)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=PRIMARY)
        .encode(
            x=x_encoding,
            y=y_encoding,
            tooltip=list(data.columns),
        )
        .properties(title=title, height=320)
    )


def histogram(data: pd.DataFrame, column: str, title: str, bins: int = 45) -> alt.Chart:
    return chart_config(
        alt.Chart(data.dropna(subset=[column]))
        .mark_bar(color=TEAL, opacity=0.88)
        .encode(
            x=alt.X(f"{column}:Q", bin=alt.Bin(maxbins=bins), title=column.replace("_", " ").title()),
            y=alt.Y("count():Q", title="Listings"),
            tooltip=[alt.Tooltip("count():Q", title="Listings")],
        )
        .properties(title=title, height=320)
    )


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.header("Refine Listings")
        st.caption("Filter the market before exploring the charts and map.")

        selected_cities = st.multiselect("City", filtered_options(df["city"]))
        selected_counties = st.multiselect("County", filtered_options(df["county"]))
        selected_zips = st.multiselect("ZIP code", filtered_options(df["zipcode"]))
        selected_types = st.multiselect("Property type", filtered_options(df["property_type"]))

        price_min, price_max = get_range(df["price"], (0, 1))
        price_range = st.slider(
            "Price range",
            min_value=int(price_min),
            max_value=int(price_max),
            value=(int(price_min), int(price_max)),
            step=10_000,
            format="$%d",
        )

        beds_min, beds_max = get_range(df["bedrooms"], (0, 10))
        bed_range = st.slider(
            "Bedrooms",
            min_value=int(beds_min),
            max_value=int(beds_max),
            value=(int(beds_min), int(beds_max)),
        )

        baths_min, baths_max = get_range(df["bathrooms"], (0, 10))
        bath_range = st.slider(
            "Bathrooms",
            min_value=int(baths_min),
            max_value=int(baths_max),
            value=(int(baths_min), int(baths_max)),
        )

        days_min, days_max = get_range(df["days_on_zillow"], (0, 365))
        days_range = st.slider(
            "Days on Zillow",
            min_value=int(days_min),
            max_value=int(days_max),
            value=(int(days_min), int(days_max)),
        )

        year_min, year_max = get_range(df["yearBuilt"], (1900, CURRENT_YEAR))
        year_range = st.slider(
            "Year built",
            min_value=int(year_min),
            max_value=int(year_max),
            value=(int(year_min), int(year_max)),
        )

    filtered = df.copy()
    if selected_cities:
        filtered = filtered[filtered["city"].astype(str).isin(selected_cities)]
    if selected_counties:
        filtered = filtered[filtered["county"].astype(str).isin(selected_counties)]
    if selected_zips:
        filtered = filtered[filtered["zipcode"].astype(str).isin(selected_zips)]
    if selected_types:
        filtered = filtered[filtered["property_type"].astype(str).isin(selected_types)]

    filtered = filtered[
        filtered["price"].between(*price_range, inclusive="both")
        & filtered["bedrooms"].between(*bed_range, inclusive="both")
        & filtered["bathrooms"].between(*bath_range, inclusive="both")
        & filtered["days_on_zillow"].between(*days_range, inclusive="both")
        & filtered["yearBuilt"].between(*year_range, inclusive="both")
    ]
    return filtered


def render_kpis(df: pd.DataFrame) -> None:
    fresh_count = int((df["days_on_zillow"] <= 14).sum())
    stale_count = int((df["days_on_zillow"] > 90).sum())
    cols = st.columns(6)
    kpi_card(cols[0], "Listings", number(len(df)), "Filtered properties")
    kpi_card(cols[1], "Median Price", money(df["price"].median()), "Typical asking price")
    kpi_card(cols[2], "Median $/Sqft", money(df["price_per_sqft"].median()), "Value benchmark")
    kpi_card(cols[3], "Median Days", number(df["days_on_zillow"].median()), "Time on Zillow")
    kpi_card(cols[4], "Median Sqft", number(df["living_area"].median()), "Interior area")
    kpi_card(cols[5], "Fresh Listings", number(fresh_count), f"{stale_count:,} stale over 90 days")


def render_inventory(df: pd.DataFrame) -> None:
    section("Inventory", "Compare where listings are concentrated and how the property mix changes across the filtered market.")
    left, right = st.columns(2)

    city_counts = df["city"].value_counts().head(15).reset_index()
    city_counts.columns = ["city", "listings"]
    left.altair_chart(bar_chart(city_counts, "listings", "city", "Listings by City", horizontal=True), use_container_width=True)

    type_counts = df["property_type"].value_counts().reset_index()
    type_counts.columns = ["property_type", "listings"]
    type_chart = (
        alt.Chart(type_counts)
        .mark_arc(innerRadius=55)
        .encode(
            theta=alt.Theta("listings:Q"),
            color=alt.Color("property_type:N", title="Property type", scale=alt.Scale(range=PALETTE)),
            tooltip=["property_type", "listings"],
        )
        .properties(title="Property Type Mix", height=320)
    )
    right.altair_chart(chart_config(type_chart), use_container_width=True)

    left, right = st.columns(2)
    county_counts = df["county"].value_counts().head(15).reset_index()
    county_counts.columns = ["county", "listings"]
    left.altair_chart(bar_chart(county_counts, "county", "listings", "Listings by County"), use_container_width=True)

    zip_counts = df["zipcode"].value_counts().head(15).reset_index()
    zip_counts.columns = ["zipcode", "listings"]
    right.altair_chart(bar_chart(zip_counts, "zipcode", "listings", "Top ZIP Codes by Listings"), use_container_width=True)


def render_pricing(df: pd.DataFrame) -> None:
    section("Pricing", "Review price distribution, price per square foot, and the cities commanding the strongest median values.")
    chart_df = clipped_frame(df, ["price", "price_per_sqft", "living_area"])
    left, right = st.columns(2)
    left.altair_chart(histogram(chart_df, "price", "Price Distribution"), use_container_width=True)
    right.altair_chart(histogram(chart_df, "price_per_sqft", "Price per Sqft Distribution"), use_container_width=True)

    by_city = (
        df.groupby("city", as_index=False)
        .agg(
            listings=("zpid", "count"),
            median_price=("price", "median"),
            median_price_per_sqft=("price_per_sqft", "median"),
        )
        .query("listings >= 5")
        .sort_values("median_price", ascending=False)
    )

    left, right = st.columns(2)
    left.altair_chart(
        bar_chart(by_city, "median_price", "city", "Median Price by City", horizontal=True),
        use_container_width=True,
    )
    right.altair_chart(
        bar_chart(
            by_city.sort_values("median_price_per_sqft", ascending=False),
            "median_price_per_sqft",
            "city",
            "Median Price per Sqft by City",
            horizontal=True,
        ),
        use_container_width=True,
    )


def render_days_and_scatter(df: pd.DataFrame) -> None:
    section("Listing Freshness and Size", "Spot new inventory, aging listings, and the relationship between home size and asking price.")
    chart_df = clipped_frame(df, ["price", "living_area"])
    left, right = st.columns(2)
    age_counts = df["listing_age_band"].value_counts(sort=False).reset_index()
    age_counts.columns = ["listing_age_band", "listings"]
    left.altair_chart(bar_chart(age_counts, "listing_age_band", "listings", "Days on Zillow Bands"), use_container_width=True)

    scatter = (
        alt.Chart(chart_df.dropna(subset=["living_area", "price"]))
        .mark_circle(size=55, opacity=0.7)
        .encode(
            x=alt.X("living_area:Q", title="Living Area"),
            y=alt.Y("price:Q", title="Price"),
            color=alt.Color("property_type:N", title="Property type", scale=alt.Scale(range=PALETTE)),
            tooltip=["street", "city", "property_type", "price", "living_area", "bedrooms", "bathrooms", "days_on_zillow"],
        )
        .properties(title="Price vs Living Area", height=320)
    )
    right.altair_chart(chart_config(scatter), use_container_width=True)


def render_map(df: pd.DataFrame) -> None:
    section("Map Explorer", "Use the map to see where higher prices, stronger price-per-square-foot values, and older listings cluster.")
    map_df = df.dropna(subset=["latitude", "longitude"]).copy()
    map_df = map_df[map_df["price"].notna()]
    if map_df.empty:
        st.info("No filtered listings have usable latitude and longitude.")
        return

    metric = st.radio(
        "Color map by",
        ["price", "price_per_sqft", "days_on_zillow"],
        horizontal=True,
        format_func=lambda value: {
            "price": "Price",
            "price_per_sqft": "Price per sqft",
            "days_on_zillow": "Days on Zillow",
        }[value],
    )
    map_df = map_df.dropna(subset=[metric])
    if map_df.empty:
        st.info("No filtered listings have the selected map metric.")
        return

    low = map_df[metric].quantile(0.05)
    high = map_df[metric].quantile(0.95)
    denom = high - low if high != low else 1
    map_df["metric_scaled"] = ((map_df[metric].clip(low, high) - low) / denom).fillna(0.5)
    map_df["fill_color"] = map_df["metric_scaled"].apply(
        lambda value: [int(37 + 180 * value), int(99 - 40 * value), int(235 - 165 * value), 185]
    )
    map_df["radius"] = 45 + (map_df["metric_scaled"] * 125)
    map_df["tooltip_price"] = map_df["price"].map(money)
    map_df["tooltip_ppsf"] = map_df["price_per_sqft"].map(money)
    map_df["tooltip_days"] = map_df["days_on_zillow"].map(number)
    map_df["tooltip_sqft"] = map_df["living_area"].map(number)

    view_state = pdk.ViewState(
        latitude=float(map_df["latitude"].mean()),
        longitude=float(map_df["longitude"].mean()),
        zoom=9,
        pitch=0,
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[longitude, latitude]",
        get_fill_color="fill_color",
        get_radius="radius",
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
        "html": (
            "<b>{street}</b><br/>"
            "{city}, {state} {zipcode}<br/>"
            "Price: {tooltip_price}<br/>"
            "$/sqft: {tooltip_ppsf}<br/>"
            "Beds/Baths: {bedrooms}/{bathrooms}<br/>"
            "Sqft: {tooltip_sqft}<br/>"
            "Days on Zillow: {tooltip_days}"
        ),
        "style": {"backgroundColor": "#0f172a", "color": "white", "borderRadius": "6px", "padding": "10px"},
    }

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip=tooltip,
            map_style=None,
        ),
        use_container_width=True,
    )


def render_listing_table(df: pd.DataFrame) -> None:
    section("Filtered Listings", "Scan the matching properties and open Zillow links for listing-level detail.")
    table = df[
        [
            "street",
            "city",
            "county",
            "zipcode",
            "property_type",
            "price",
            "price_per_sqft",
            "living_area",
            "bedrooms",
            "bathrooms",
            "yearBuilt",
            "days_on_zillow",
            "listing_url",
        ]
    ].sort_values(["city", "price"], ascending=[True, True])

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "price": st.column_config.NumberColumn("Price", format="$%d"),
            "price_per_sqft": st.column_config.NumberColumn("$/sqft", format="$%.0f"),
            "living_area": st.column_config.NumberColumn("Sqft", format="%d"),
            "listing_url": st.column_config.LinkColumn("Zillow"),
        },
    )


def main() -> None:
    inject_theme()

    if not DATA_PATH.exists():
        st.error(f"Could not find {DATA_PATH.name} next to this app.")
        st.stop()

    df = load_data(DATA_PATH)
    render_hero(df)
    filtered = apply_filters(df)

    if filtered.empty:
        st.warning("No listings match the selected filters.")
        return

    render_kpis(filtered)

    overview_tab, pricing_tab, map_tab, listings_tab = st.tabs(
        ["Market Overview", "Pricing", "Map Explorer", "Listings"]
    )
    with overview_tab:
        render_inventory(filtered)
        render_days_and_scatter(filtered)
    with pricing_tab:
        render_pricing(filtered)
    with map_tab:
        render_map(filtered)
    with listings_tab:
        render_listing_table(filtered)


if __name__ == "__main__":
    main()
