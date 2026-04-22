import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="Turbo 20 — Burn Extra Simulator",
    layout="wide",
)

# ── Constantes ───────────────────────────────────────────────────────────────
RATE_ATUAL = 2.00
MIN_EARNING_CITIES = {
    "B. Rio De Janeiro",
    "C. Belo Horizonte",
    "J. Porto Alegre",
    "E. Curitiba",
}
MIN_EARNING_VALUE = 8.0

RANGE_ORDER = ["4.0 KM < 5", "5.0 KM <=6", "6.0 KM <=7", "7.0 KM <=8", "8.0 KM <=9", "7.0 KM >9"]

# ── Helpers ──────────────────────────────────────────────────────────────────
def fmt_brl(v): return f"R$ {v:,.2f}"
def fmt_usd(v): return f"$ {v:,.2f}"
def fmt_dual(v, fx): return f"R$ {v:,.2f}  |  $ {v/fx:,.2f}"

def burn_card(col, label, brl, fx, sub=""):
    col.markdown(
        f"<div style='background:#1e1e2e;padding:16px;border-radius:10px;"
        f"border-left:4px solid #FF4B4B;margin-bottom:8px'>"
        f"<div style='color:#aaa;font-size:12px;margin-bottom:4px'>{label}</div>"
        f"<div style='color:#FF4B4B;font-size:22px;font-weight:700'>R$ {brl:,.2f}</div>"
        f"<div style='color:#888;font-size:14px'>$ {brl/fx:,.2f} USD</div>"
        f"<div style='color:#555;font-size:11px;margin-top:4px'>{sub}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Carregar dados ───────────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["KM_TO_USER"] = pd.to_numeric(df["KM_TO_USER"], errors="coerce")
    df["Soma de ORDER_EARNING"] = pd.to_numeric(df["Soma de ORDER_EARNING"], errors="coerce")
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["KM_TO_USER", "Soma de ORDER_EARNING", "Data"])
    return df

# ── Simulação por faixa ──────────────────────────────────────────────────────
def simulate(df: pd.DataFrame, rate_map: dict) -> pd.DataFrame:
    df = df.copy()
    df["rate_increase"] = df["RANGE_KM"].map(rate_map).fillna(0)
    df["new_rate"] = RATE_ATUAL + df["rate_increase"]
    df["earning_simulado"] = df["KM_TO_USER"] * df["new_rate"]
    mask = df["CITY"].isin(MIN_EARNING_CITIES)
    df.loc[mask, "earning_simulado"] = df.loc[mask, "earning_simulado"].clip(lower=MIN_EARNING_VALUE)
    df["burn_extra"] = (df["earning_simulado"] - df["Soma de ORDER_EARNING"]).clip(lower=0)
    df["impactado"] = df["burn_extra"] > 0
    return df

# ── CSV path ─────────────────────────────────────────────────────────────────
DEFAULT_PATH   = os.path.join(os.path.dirname(__file__), "Dados Orion.csv")
DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Downloads", "Dados Orion.csv")
csv_path = DEFAULT_PATH if os.path.exists(DEFAULT_PATH) else (
           DOWNLOADS_PATH if os.path.exists(DOWNLOADS_PATH) else None)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔥 Turbo 20")
    st.caption("Burn Extra Simulator")
    st.divider()

    if csv_path is None:
        uploaded = st.file_uploader("Carregar base de dados (CSV)", type="csv")
        if uploaded:
            df_raw = pd.read_csv(uploaded, encoding="utf-8-sig")
            df_raw["KM_TO_USER"] = pd.to_numeric(df_raw["KM_TO_USER"], errors="coerce")
            df_raw["Soma de ORDER_EARNING"] = pd.to_numeric(df_raw["Soma de ORDER_EARNING"], errors="coerce")
            df_raw["Data"] = pd.to_datetime(df_raw["Data"], errors="coerce")
            df_raw = df_raw.dropna(subset=["KM_TO_USER", "Soma de ORDER_EARNING", "Data"])
        else:
            st.info("📂 Faça upload da base de dados para começar.")
            st.markdown("**Colunas esperadas:** `CITY, NAME, Data, T. ORDERS, STORE_TYPE, ORDER_ID, Soma de ORDER_EARNING, KM_TO_USER, RANGE_KM`")
            st.stop()
    else:
        df_raw = load_data(csv_path)

    # ── Câmbio ────────────────────────────────────────────────────────────────
    st.markdown("### 💱 Câmbio USD/BRL")
    fx_rate = st.number_input("Cotação do Dólar (R$)", min_value=1.0, max_value=20.0,
                               value=5.50, step=0.05, format="%.2f")

    st.divider()

    # ── Rate por faixa de KM ─────────────────────────────────────────────────
    st.markdown("### 📍 Aumento por Faixa de KM")
    st.caption(f"Rate base: R$ {RATE_ATUAL:.2f}/km")

    rate_map = {}
    ranges_in_data = [r for r in RANGE_ORDER if r in df_raw["RANGE_KM"].unique()]
    for rng in ranges_in_data:
        default = (0.25 if "< 5" in rng else
                   0.35 if "<=6" in rng else
                   0.50 if "<=7" in rng else
                   1.00 if "<=8" in rng else 1.50)
        rate_map[rng] = st.slider(
            rng,
            min_value=0.0, max_value=3.0,
            value=float(default), step=0.10,
            format="R$ %.2f",
            key=f"rate_{rng}",
        )
        new = RATE_ATUAL + rate_map[rng]
        st.caption(f"R$ {RATE_ATUAL:.2f} → **R$ {new:.2f}**/km  |  **$ {new/fx_rate:.2f}**/km")

    st.divider()

    # ── Filtros ───────────────────────────────────────────────────────────────
    st.markdown("### Filtros")
    cities = sorted(df_raw["CITY"].dropna().unique())
    selected_cities = st.multiselect("Cidade", cities, default=cities)

    store_types = sorted(df_raw["STORE_TYPE"].dropna().unique())
    selected_store = st.multiselect("Store Type", store_types, default=store_types)

    date_min = df_raw["Data"].min().date()
    date_max = df_raw["Data"].max().date()
    date_range = st.date_input("Período", value=(date_min, date_max),
                                min_value=date_min, max_value=date_max)

# ── Filtro + simulação ───────────────────────────────────────────────────────
df = df_raw[df_raw["CITY"].isin(selected_cities) & df_raw["STORE_TYPE"].isin(selected_store)].copy()
if len(date_range) == 2:
    df = df[(df["Data"].dt.date >= date_range[0]) & (df["Data"].dt.date <= date_range[1])]
df = simulate(df, rate_map)

# ── Métricas base ────────────────────────────────────────────────────────────
total_burn        = df["burn_extra"].sum()
orders_impactados = int(df["impactado"].sum())
total_orders      = len(df)
pct_impactados    = orders_impactados / total_orders * 100 if total_orders else 0
burn_por_pedido   = total_burn / orders_impactados if orders_impactados else 0
days_in_range     = max((df["Data"].max() - df["Data"].min()).days, 1)
daily_burn        = total_burn / days_in_range

# ── Header ───────────────────────────────────────────────────────────────────
rate_summary = "  |  ".join([f"{r}: +R${v:.2f}" for r, v in rate_map.items()])
st.markdown(
    f"<h1 style='margin-bottom:2px'>🔥 Turbo 20 — Burn Extra Simulator</h1>"
    f"<p style='color:#888;margin-top:0;font-size:13px'>"
    f"{total_orders:,} pedidos · Câmbio R$ {fx_rate:.2f} · {rate_summary}</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── KPIs principais ──────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("🔥 Burn Extra Total",
          f"R$ {total_burn:,.2f}",
          f"$ {total_burn/fx_rate:,.2f} USD")
k2.metric("💸 Burn / Pedido Impactado",
          f"R$ {burn_por_pedido:.2f}",
          f"$ {burn_por_pedido/fx_rate:.2f} USD")
k3.metric("🎯 Orders Impactados",
          f"{orders_impactados:,}",
          f"{pct_impactados:.1f}% do total")
k4.metric("📦 Orders Não Impactados",
          f"{total_orders - orders_impactados:,}",
          f"{100-pct_impactados:.1f}% do total")

st.divider()

# ── Projeção de Burn ─────────────────────────────────────────────────────────
st.markdown("### 📅 Projeção de Burn Extra")
p1, p2, p3, p4 = st.columns(4)
burn_card(p1, "Diário (média)",    daily_burn,          fx_rate, f"base: {days_in_range} dias")
burn_card(p2, "Semanal",           daily_burn * 7,      fx_rate, "× 7 dias")
burn_card(p3, "Mensal",            daily_burn * 30,     fx_rate, "× 30 dias")
burn_card(p4, "Trimestral",        daily_burn * 90,     fx_rate, "× 90 dias")

st.divider()

# ── Orders por semana + Valor investido ──────────────────────────────────────
st.markdown("### 📊 Orders & Investimento por Semana")

df["semana"] = df["Data"].dt.to_period("W").apply(lambda r: r.start_time.date())
weekly = df.groupby("semana").agg(
    orders_total=("ORDER_ID", "count"),
    orders_impactados=("impactado", "sum"),
    burn_extra=("burn_extra", "sum"),
    earning_atual=("Soma de ORDER_EARNING", "sum"),
).reset_index()
weekly["burn_usd"] = weekly["burn_extra"] / fx_rate

fig_weekly = go.Figure()
fig_weekly.add_bar(name="Orders Total",      x=weekly["semana"], y=weekly["orders_total"],
                   marker_color="#636EFA", opacity=0.6)
fig_weekly.add_bar(name="Orders Impactados", x=weekly["semana"], y=weekly["orders_impactados"],
                   marker_color="#FF4B4B", opacity=0.9)
fig_weekly.update_layout(
    barmode="overlay",
    yaxis=dict(title="Quantidade de Orders", showgrid=False),
    legend=dict(orientation="h", y=1.1),
    height=320, margin=dict(t=40, b=20),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_weekly, use_container_width=True)

wa, wb = st.columns(2)
with wa:
    st.markdown("#### Burn Extra por Semana (R$ e USD)")
    fig_w_burn = go.Figure()
    fig_w_burn.add_bar(name="Burn R$", x=weekly["semana"], y=weekly["burn_extra"],
                       marker_color="#FF4B4B",
                       text=weekly["burn_extra"].apply(lambda v: f"R${v:,.0f}"),
                       textposition="outside")
    fig_w_burn.add_scatter(name="Burn USD", x=weekly["semana"], y=weekly["burn_usd"],
                           mode="lines+markers", line=dict(color="#FECB52", width=2),
                           marker=dict(size=8), yaxis="y2",
                           text=weekly["burn_usd"].apply(lambda v: f"${v:,.0f}"),
                           textposition="top center")
    fig_w_burn.update_layout(
        yaxis=dict(title="R$", showgrid=False),
        yaxis2=dict(title="USD", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h"),
        height=320, margin=dict(t=30, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_w_burn, use_container_width=True)

with wb:
    st.markdown("#### Earning Atual vs Simulado por Semana")
    weekly["earning_simulado"] = weekly["earning_atual"] + weekly["burn_extra"]
    fig_w_earn = go.Figure()
    fig_w_earn.add_bar(name="Earning Atual", x=weekly["semana"], y=weekly["earning_atual"],
                       marker_color="#636EFA")
    fig_w_earn.add_bar(name="Burn Extra (incremento)", x=weekly["semana"], y=weekly["burn_extra"],
                       marker_color="#FF4B4B")
    fig_w_earn.update_layout(
        barmode="stack",
        yaxis=dict(title="R$", showgrid=False),
        legend=dict(orientation="h"),
        height=320, margin=dict(t=30, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_w_earn, use_container_width=True)

st.divider()

# ── Burn por Faixa de KM ─────────────────────────────────────────────────────
st.markdown("### 📍 Burn Extra & Orders por Faixa de KM")

range_agg = df.groupby("RANGE_KM").agg(
    burn_extra=("burn_extra", "sum"),
    orders_total=("ORDER_ID", "count"),
    orders_impactados=("impactado", "sum"),
).reset_index()
range_agg["pct_impactados"]  = (range_agg["orders_impactados"] / range_agg["orders_total"] * 100).round(1)
range_agg["burn_por_order"]  = (range_agg["burn_extra"] / range_agg["orders_impactados"].replace(0, 1)).round(2)
range_agg["burn_usd"]        = range_agg["burn_extra"] / fx_rate
# ordenar por faixa
range_agg["_sort"] = range_agg["RANGE_KM"].apply(lambda r: RANGE_ORDER.index(r) if r in RANGE_ORDER else 99)
range_agg = range_agg.sort_values("_sort").drop(columns="_sort")

fig_km = go.Figure()
fig_km.add_bar(
    name="Burn Extra (R$)", x=range_agg["RANGE_KM"], y=range_agg["burn_extra"],
    marker_color="#FF4B4B",
    text=range_agg["burn_extra"].apply(lambda v: f"R$ {v:,.0f}"),
    textposition="outside", yaxis="y1",
)
fig_km.add_bar(
    name="Burn Extra (USD)", x=range_agg["RANGE_KM"], y=range_agg["burn_usd"],
    marker_color="#FECB52", opacity=0.7,
    text=range_agg["burn_usd"].apply(lambda v: f"$ {v:,.0f}"),
    textposition="outside", yaxis="y1",
)
fig_km.add_scatter(
    name="Orders Impactados", x=range_agg["RANGE_KM"], y=range_agg["orders_impactados"],
    mode="lines+markers+text", marker=dict(size=10, color="#00CC96"),
    line=dict(color="#00CC96", width=2),
    text=range_agg["orders_impactados"].apply(lambda v: f"{v:,}"),
    textposition="top center", yaxis="y2",
)
fig_km.update_layout(
    barmode="group",
    yaxis=dict(title="Burn Extra", showgrid=False),
    yaxis2=dict(title="Orders Impactados", overlaying="y", side="right", showgrid=False),
    legend=dict(orientation="h", y=1.12),
    height=400, margin=dict(t=50, b=20),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_km, use_container_width=True)

range_table = range_agg[["RANGE_KM","burn_extra","burn_usd","orders_total","orders_impactados","pct_impactados","burn_por_order"]].copy()
range_table["burn_extra"]  = range_table["burn_extra"].round(2)
range_table["burn_usd"]    = range_table["burn_usd"].round(2)
range_table["burn_por_order"] = range_table["burn_por_order"]
range_table.columns = ["Faixa KM","Burn Extra R$","Burn Extra USD","Orders Total","Orders Impactados","% Impactados","Burn/Order R$"]
st.dataframe(range_table, use_container_width=True, hide_index=True)

st.divider()

# ── Store Type Impact ────────────────────────────────────────────────────────
st.markdown("### 🏪 Impacto por Store Type")
store_agg = df.groupby("STORE_TYPE").agg(
    burn_extra=("burn_extra", "sum"),
    orders_total=("ORDER_ID", "count"),
    orders_impactados=("impactado", "sum"),
).reset_index()
store_agg["pct_impactados"] = (store_agg["orders_impactados"] / store_agg["orders_total"] * 100).round(1)
store_agg["burn_usd"]       = (store_agg["burn_extra"] / fx_rate).round(2)
store_agg["burn_por_order"] = (store_agg["burn_extra"] / store_agg["orders_impactados"].replace(0,1)).round(2)
store_agg = store_agg.sort_values("burn_extra", ascending=False)

sc1, sc2 = st.columns([3, 2])
with sc1:
    fig_store = go.Figure()
    fig_store.add_bar(
        name="Burn Extra R$", x=store_agg["burn_extra"], y=store_agg["STORE_TYPE"],
        orientation="h", marker_color="#FF4B4B",
        text=store_agg["burn_extra"].apply(lambda v: f"R$ {v:,.0f}"),
        textposition="outside",
    )
    fig_store.update_layout(
        yaxis=dict(autorange="reversed"),
        height=max(420, len(store_agg) * 26),
        margin=dict(t=10, l=10, r=100, b=10),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_store, use_container_width=True)

with sc2:
    store_table = store_agg[["STORE_TYPE","burn_extra","burn_usd","orders_impactados","pct_impactados","burn_por_order"]].copy()
    store_table.columns = ["Store Type","Burn R$","Burn USD","Orders Imp.","% Imp.","Burn/Order"]
    st.dataframe(store_table, use_container_width=True, hide_index=True, height=500)

st.divider()

# ── Burn por Cidade ──────────────────────────────────────────────────────────
st.markdown("### 🏙️ Burn Extra por Cidade")
city_agg = df.groupby("CITY").agg(
    burn_extra=("burn_extra", "sum"),
    orders_total=("ORDER_ID", "count"),
    orders_impactados=("impactado", "sum"),
    earning_atual=("Soma de ORDER_EARNING", "sum"),
).reset_index()
city_agg["pct_impactados"]        = (city_agg["orders_impactados"] / city_agg["orders_total"] * 100).round(1)
city_agg["burn_usd"]              = (city_agg["burn_extra"] / fx_rate).round(2)
city_agg["pct_burn_sobre_earning"]= (city_agg["burn_extra"] / city_agg["earning_atual"] * 100).round(1)
city_agg = city_agg.sort_values("burn_extra", ascending=False)

fig_city = go.Figure()
fig_city.add_bar(name="Burn R$",  x=city_agg["CITY"], y=city_agg["burn_extra"],
                 marker_color="#FF4B4B",
                 text=city_agg["burn_extra"].apply(lambda v: f"R$ {v:,.0f}"),
                 textposition="outside")
fig_city.add_bar(name="Burn USD", x=city_agg["CITY"], y=city_agg["burn_usd"],
                 marker_color="#FECB52", opacity=0.8,
                 text=city_agg["burn_usd"].apply(lambda v: f"$ {v:,.0f}"),
                 textposition="outside")
fig_city.add_scatter(
    name="% Orders Impactados", x=city_agg["CITY"], y=city_agg["pct_impactados"],
    mode="lines+markers+text", marker=dict(size=10, color="#00CC96"),
    line=dict(color="#00CC96", width=2),
    text=city_agg["pct_impactados"].apply(lambda v: f"{v:.0f}%"),
    textposition="top center", yaxis="y2",
)
fig_city.update_layout(
    barmode="group",
    yaxis=dict(title="Burn Extra", showgrid=False),
    yaxis2=dict(title="% Orders Impactados", overlaying="y", side="right",
                showgrid=False, range=[0, 120]),
    legend=dict(orientation="h", y=1.12),
    height=420, margin=dict(t=50, b=20),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_city, use_container_width=True)

city_table = city_agg[["CITY","burn_extra","burn_usd","orders_impactados","pct_impactados","pct_burn_sobre_earning"]].copy()
city_table.columns = ["Cidade","Burn Extra R$","Burn Extra USD","Orders Impactados","% Impactados","Burn / Earning (%)"]
st.dataframe(city_table, use_container_width=True, hide_index=True)

st.divider()

# ── Evolução mensal ───────────────────────────────────────────────────────────
st.markdown("### 📈 Burn Extra por Mês")
df["mes"] = df["Data"].dt.to_period("M").astype(str)
monthly = df.groupby("mes").agg(
    burn_extra=("burn_extra", "sum"),
    orders_total=("ORDER_ID", "count"),
    orders_impactados=("impactado", "sum"),
).reset_index()
monthly["burn_usd"] = monthly["burn_extra"] / fx_rate

fig_month = go.Figure()
fig_month.add_bar(name="Burn R$",  x=monthly["mes"], y=monthly["burn_extra"],
                  marker_color="#FF4B4B",
                  text=monthly["burn_extra"].apply(lambda v: f"R$ {v:,.0f}"),
                  textposition="outside")
fig_month.add_bar(name="Burn USD", x=monthly["mes"], y=monthly["burn_usd"],
                  marker_color="#FECB52", opacity=0.8,
                  text=monthly["burn_usd"].apply(lambda v: f"$ {v:,.0f}"),
                  textposition="outside")
fig_month.update_layout(
    barmode="group",
    yaxis=dict(title="Burn Extra", showgrid=False),
    legend=dict(orientation="h"),
    height=340, margin=dict(t=40, b=10),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_month, use_container_width=True)

# ── Detalhamento ──────────────────────────────────────────────────────────────
with st.expander("Ver pedidos detalhados (apenas impactados)"):
    detail = df[df["impactado"]][["CITY","NAME","Data","ORDER_ID","STORE_TYPE",
                                   "KM_TO_USER","RANGE_KM","Soma de ORDER_EARNING",
                                   "earning_simulado","burn_extra"]].copy()
    detail["burn_usd"] = (detail["burn_extra"] / fx_rate).round(4)
    detail.columns = ["Cidade","Warehouse","Data","Order ID","Store Type",
                       "KM","Faixa KM","Earning Atual","Earning Simulado","Burn Extra R$","Burn Extra USD"]
    for c in ["Earning Atual","Earning Simulado","Burn Extra R$"]:
        detail[c] = detail[c].round(2)
    detail["KM"] = detail["KM"].round(4)
    st.dataframe(detail.sort_values("Burn Extra R$", ascending=False),
                 use_container_width=True, hide_index=True)
