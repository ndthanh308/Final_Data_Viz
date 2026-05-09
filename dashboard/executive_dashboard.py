# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px


# =========================
# 0) CẤU HÌNH CHUNG
# =========================
st.set_page_config(layout="wide", page_title="Executive Insights Dashboard")

BASE_DIR = Path(r"D:\Vscode\Self\Data Science\Book Notes\Data Visualization\final\Final_Data_Viz")
DATA_DIR = BASE_DIR / "data" / "main" / "raw"

# Bảng màu an toàn cho người mù màu
COLOR_GOOD = "#0072B2"  # Xanh dương - Tốt
COLOR_WARN = "#D55E00"  # Cam đậm - Cảnh báo
COLOR_PINK = "#E91E63"  # Hồng cánh sen cho traffic
COLOR_BG = "#F7F7F7"
COLOR_GRID = "rgba(0,0,0,0.08)"

# Bảng màu treemap (Cam -> Trắng -> Xanh)
TREEMAP_SCALE = [
    [0.0, COLOR_WARN],
    [0.5, "#F1E6DD"],
    [1.0, COLOR_GOOD],
]


# =========================
# 1) HÀM TIỆN ÍCH
# =========================
def dinh_dang_vnd(x):
    if pd.isna(x):
        return "—"
    return f"{x:,.0f}".replace(",", ".") + " VNĐ"


def dinh_dang_ty_le(x):
    if pd.isna(x):
        return "—"
    return f"{x * 100:.2f}%".replace(".", ",")


def mau_theo_nguong(gia_tri, nguong, dao_nguoc=False):
    if pd.isna(gia_tri):
        return "#808080"
    if dao_nguoc:
        return COLOR_GOOD if gia_tri <= nguong else COLOR_WARN
    return COLOR_GOOD if gia_tri >= nguong else COLOR_WARN


def render_kpi_card(col, tieu_de, gia_tri, mau, value_align="left"):
    html = f"""
    <div style="background-color:{COLOR_BG}; padding:16px; border-radius:10px; border:1px solid #E5E7EB;">
        <div style="font-size:14px; color:#555; font-weight:600; text-align:center;">{tieu_de}</div>
        <div style="font-size:28px; font-weight:700; color:{mau}; margin-top:6px; text-align:{value_align};">{gia_tri}</div>
    </div>
    """
    col.markdown(html, unsafe_allow_html=True)


def apply_plot_style(fig):
    main_color = "#111827"
    text_color = "#1f2937"
    fig.update_layout(
        font=dict(color=text_color, size=13),
        title_font=dict(color=main_color, size=18),
        legend=dict(font=dict(color=text_color, size=12), title_font=dict(color=main_color, size=12)),
    )
    fig.update_xaxes(tickfont=dict(color=text_color, size=12), title_font=dict(color=main_color, size=13))
    fig.update_yaxes(tickfont=dict(color=text_color, size=12), title_font=dict(color=main_color, size=13))
    return fig


# =========================
# 2) NẠP DỮ LIỆU
# =========================
@st.cache_data
def nap_du_lieu(data_dir: Path):
    # Đọc dữ liệu và chuẩn hóa cột
    df_products = pd.read_csv(data_dir / "products.csv")
    df_orders = pd.read_csv(data_dir / "orders.csv", parse_dates=["order_date"])
    df_order_items = pd.read_csv(data_dir / "order_items.csv")
    df_returns = pd.read_csv(data_dir / "returns.csv", parse_dates=["return_date"])
    df_web_traffic = pd.read_csv(data_dir / "web_traffic.csv", parse_dates=["date"])

    for df in [df_products, df_orders, df_order_items, df_returns, df_web_traffic]:
        df.columns = df.columns.str.strip()

    # Xử lý ZIP code: luôn là chuỗi để tránh mất số 0 ở đầu
    if "zip" in df_orders.columns:
        df_orders["zip"] = df_orders["zip"].astype("string")

    # Ép kiểu số
    num_cols = {
        "products": ["price", "cogs"],
        "order_items": ["quantity", "unit_price", "discount_amount"],
        "returns": ["return_quantity", "refund_amount"],
        "web_traffic": ["sessions", "unique_visitors"],
    }
    for col in num_cols["products"]:
        if col in df_products.columns:
            df_products[col] = pd.to_numeric(df_products[col], errors="coerce")

    for col in num_cols["order_items"]:
        if col in df_order_items.columns:
            df_order_items[col] = pd.to_numeric(df_order_items[col], errors="coerce")

    for col in num_cols["returns"]:
        if col in df_returns.columns:
            df_returns[col] = pd.to_numeric(df_returns[col], errors="coerce")

    for col in num_cols["web_traffic"]:
        if col in df_web_traffic.columns:
            df_web_traffic[col] = pd.to_numeric(df_web_traffic[col], errors="coerce")

    return df_products, df_orders, df_order_items, df_returns, df_web_traffic


def chuan_bi_order_items(df_orders, df_order_items, df_products):
    # Merge order_items + products + orders để có category/segment và ngày đặt
    df_items = df_order_items.merge(
        df_products[["product_id", "category", "segment", "price", "cogs"]],
        on="product_id",
        how="left",
    ).merge(
        df_orders[["order_id", "order_date"]],
        on="order_id",
        how="left",
    )

    # Ưu tiên unit_price, fallback sang price
    if "unit_price" not in df_items.columns:
        df_items["unit_price"] = df_items["price"]
    else:
        df_items["unit_price"] = df_items["unit_price"].fillna(df_items["price"])

    df_items["quantity"] = pd.to_numeric(df_items["quantity"], errors="coerce")
    df_items["cogs"] = pd.to_numeric(df_items["cogs"], errors="coerce")

    df_items["revenue"] = df_items["quantity"] * df_items["unit_price"]
    df_items["cogs_value"] = df_items["quantity"] * df_items["cogs"]
    df_items["gross_profit"] = df_items["revenue"] - df_items["cogs_value"]

    df_items["category"] = df_items["category"].fillna("Không xác định")
    df_items["segment"] = df_items["segment"].fillna("Không xác định")

    return df_items


def chuan_bi_returns(df_returns, df_orders, df_products):
    df_ret = df_returns.merge(
        df_orders[["order_id", "order_date"]],
        on="order_id",
        how="left",
    ).merge(
        df_products[["product_id", "category", "segment", "price"]],
        on="product_id",
        how="left",
    )

    df_ret["return_quantity"] = pd.to_numeric(df_ret["return_quantity"], errors="coerce")
    df_ret["refund_amount"] = pd.to_numeric(df_ret["refund_amount"], errors="coerce")

    # Ưu tiên refund_amount, fallback theo giá
    df_ret["return_value"] = df_ret["refund_amount"].fillna(df_ret["return_quantity"] * df_ret["price"])

    df_ret["category"] = df_ret["category"].fillna("Không xác định")
    df_ret["segment"] = df_ret["segment"].fillna("Không xác định")

    return df_ret


# =========================
# 3) BỘ LỌC
# =========================
# def apply_filters(df_items, df_returns, df_orders, df_web_traffic, start_date, end_date, categories, segments):
#     # Lọc theo ngày
#     mask_items = (df_items["order_date"] >= start_date) & (df_items["order_date"] <= end_date)
#     df_items_f = df_items.loc[mask_items].copy()

#     if categories:
#         df_items_f = df_items_f[df_items_f["category"].isin(categories)]
#     if segments:
#         df_items_f = df_items_f[df_items_f["segment"].isin(segments)]

#     # Orders chỉ lấy những đơn có item phù hợp
#     order_ids = df_items_f["order_id"].dropna().unique()
#     df_orders_f = df_orders[
#         (df_orders["order_date"] >= start_date) &
#         (df_orders["order_date"] <= end_date) &
#         (df_orders["order_id"].isin(order_ids))
#     ].copy()

#     # Returns lọc theo order_date + category/segment
#     mask_ret = (df_returns["order_date"] >= start_date) & (df_returns["order_date"] <= end_date)
#     df_returns_f = df_returns.loc[mask_ret].copy()
#     if categories:
#         df_returns_f = df_returns_f[df_returns_f["category"].isin(categories)]
#     if segments:
#         df_returns_f = df_returns_f[df_returns_f["segment"].isin(segments)]

#     # Web traffic chỉ lọc theo thời gian
#     df_web_f = df_web_traffic[
#         (df_web_traffic["date"] >= start_date) &
#         (df_web_traffic["date"] <= end_date)
#     ].copy()

#     return df_items_f, df_returns_f, df_orders_f, df_web_f


def apply_filters(df_items, df_returns, df_orders, df_web_traffic, start_date, end_date, categories, segments):
    # Lọc theo category/segment (không lọc thời gian)
    df_items_cs = df_items.copy()
    if categories:
        df_items_cs = df_items_cs[df_items_cs["category"].isin(categories)]
    if segments:
        df_items_cs = df_items_cs[df_items_cs["segment"].isin(segments)]

    df_returns_cs = df_returns.copy()
    if categories:
        df_returns_cs = df_returns_cs[df_returns_cs["category"].isin(categories)]
    if segments:
        df_returns_cs = df_returns_cs[df_returns_cs["segment"].isin(segments)]

    order_ids_cs = df_items_cs["order_id"].dropna().unique()
    df_orders_cs = df_orders[df_orders["order_id"].isin(order_ids_cs)].copy()

    # Lọc theo thời gian cho KPI / Treemap / Traffic
    df_items_f = df_items_cs[(df_items_cs["order_date"] >= start_date) & (df_items_cs["order_date"] <= end_date)].copy()
    df_returns_f = df_returns_cs[(df_returns_cs["order_date"] >= start_date) & (df_returns_cs["order_date"] <= end_date)].copy()
    df_orders_f = df_orders_cs[(df_orders_cs["order_date"] >= start_date) & (df_orders_cs["order_date"] <= end_date)].copy()

    df_web_f = df_web_traffic[
        (df_web_traffic["date"] >= start_date) &
        (df_web_traffic["date"] <= end_date)
    ].copy()

    return df_items_f, df_returns_f, df_orders_f, df_web_f, df_items_cs, df_returns_cs, df_orders_cs

# =========================
# 4) KPI
# =========================
def create_kpis(df_items_f, df_returns_f, margin_threshold, return_threshold):
    revenue = df_items_f["revenue"].sum()
    cogs = df_items_f["cogs_value"].sum()
    gross_profit = revenue - cogs
    return_value = df_returns_f["return_value"].sum()
    net_profit = gross_profit - return_value

    gross_margin = gross_profit / revenue if revenue > 0 else np.nan

    total_qty = df_items_f["quantity"].sum()
    return_qty = df_returns_f["return_quantity"].sum()
    return_rate = return_qty / total_qty if total_qty > 0 else np.nan

    col1, col2, col3, col4 = st.columns([1.25, 1.15, 1, 1])

    render_kpi_card(col1, "Doanh thu", dinh_dang_vnd(revenue), COLOR_GOOD, value_align="center")
    render_kpi_card(col2, "Lợi nhuận thuần", dinh_dang_vnd(net_profit), COLOR_GOOD if net_profit >= 0 else COLOR_WARN, value_align="center")
    render_kpi_card(
        col3,
        "Biên lợi nhuận gộp",
        dinh_dang_ty_le(gross_margin),
        mau_theo_nguong(gross_margin, margin_threshold),
        value_align="center",
    )
    render_kpi_card(
        col4,
        "Tỷ lệ trả hàng",
        dinh_dang_ty_le(return_rate),
        mau_theo_nguong(return_rate, return_threshold, dao_nguoc=True),
        value_align="center",
    )

# =========================
# 5) TIME SERIES (TẦNG 2)
# =========================
def build_daily_metrics(df_items_f, df_returns_f, df_orders_f, start_date, end_date):
    df_items_daily = (
        df_items_f.groupby("order_date", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            cogs_value=("cogs_value", "sum"),
            gross_profit=("gross_profit", "sum"),
            quantity=("quantity", "sum"),
        )
        .rename(columns={"order_date": "date"})
    )

    df_returns_daily = (
        df_returns_f.groupby("order_date", as_index=False)
        .agg(return_qty=("return_quantity", "sum"), return_value=("return_value", "sum"))
        .rename(columns={"order_date": "date"})
    )

    df_orders_daily = (
        df_orders_f.groupby("order_date", as_index=False)
        .agg(orders=("order_id", "count"))
        .rename(columns={"order_date": "date"})
    )

    df_daily = df_items_daily.merge(df_returns_daily, on="date", how="left").merge(
        df_orders_daily, on="date", how="left"
    )

    # Bổ sung ngày thiếu để mạch thời gian liền mạch
    date_index = pd.date_range(start_date, end_date, freq="D")
    df_daily = df_daily.set_index("date").reindex(date_index).reset_index().rename(columns={"index": "date"})

    df_daily[["revenue", "cogs_value", "gross_profit", "quantity", "return_qty", "return_value", "orders"]] = (
        df_daily[["revenue", "cogs_value", "gross_profit", "quantity", "return_qty", "return_value", "orders"]]
        .fillna(0)
    )

    # Tỷ lệ trả hàng theo ngày (%)
    df_daily["return_rate"] = np.where(
        df_daily["quantity"] > 0,
        df_daily["return_qty"] / df_daily["quantity"] * 100,
        np.nan,
    )

    # Lợi nhuận thuần theo ngày
    df_daily["net_profit"] = df_daily["gross_profit"] - df_daily["return_value"]

    # MA7
    for col in ["revenue", "cogs_value", "net_profit", "return_rate"]:
        df_daily[f"{col}_ma7"] = df_daily[col].rolling(window=7, min_periods=1).mean()

    return df_daily


def create_trend_chart(df_daily, metrics_selected, start_date, end_date):
    if not metrics_selected:
        st.warning("Vui lòng chọn ít nhất 1 chỉ số để hiển thị biểu đồ.")
        return

    metric_map = {
        "Doanh thu": ("revenue_ma7", COLOR_GOOD),
        "Lợi nhuận": ("net_profit_ma7", "#56B4E9"),
        "COGS": ("cogs_value_ma7", COLOR_WARN),
        "Return Rate": ("return_rate_ma7", "#E69F00"),
    }

    df_period = df_daily[(df_daily["date"] >= start_date) & (df_daily["date"] <= end_date)].copy()

    fig = go.Figure()
    same_year = start_date.year == end_date.year
    same_month = same_year and (start_date.month == end_date.month)

    # So sánh YoY / MoM khi chỉ chọn 1 chỉ số
    if len(metrics_selected) == 1 and (same_month or same_year):
        metric_name = metrics_selected[0]
        col_name, color = metric_map[metric_name]

        if same_month:
            # So sánh tháng này vs tháng trước
            prev_start = pd.Timestamp(start_date) - pd.DateOffset(months=1)
            prev_end = pd.Timestamp(end_date) - pd.DateOffset(months=1)

            df_prev = df_daily[(df_daily["date"] >= prev_start) & (df_daily["date"] <= prev_end)].copy()
            df_period["key"] = df_period["date"].dt.day
            df_prev["key"] = df_prev["date"].dt.day

            df_prev = df_prev[["key", "date", col_name]].rename(
                columns={"date": "prev_date", col_name: f"{col_name}_prev"}
            )
            df_comp = df_period.merge(
                df_prev,
                on="key",
                how="left",
            )

            fig.add_trace(
                go.Scatter(
                    x=df_comp["date"],
                    y=df_comp[col_name],
                    mode="lines",
                    name=f"{metric_name} (Tháng này)",
                    line=dict(color=color, width=3),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_comp["date"],
                    y=df_comp[f"{col_name}_prev"],
                    mode="lines",
                    name=f"{metric_name} (Tháng trước)",
                    line=dict(color=color, width=2, dash="dash"),
                    opacity=0.6,
                    customdata=df_comp["prev_date"],
                    hovertemplate=(
                        "%{customdata|%b %d, %Y}<br>"
                        f"{metric_name}: "
                        + ("%{y:.2f}%" if metric_name == "Return Rate" else "%{y:,.0f}")
                        + "<extra></extra>"
                    ),
                )
            )
        else:
            # So sánh năm này vs năm trước
            prev_start = pd.Timestamp(start_date) - pd.DateOffset(years=1)
            prev_end = pd.Timestamp(end_date) - pd.DateOffset(years=1)

            df_prev = df_daily[(df_daily["date"] >= prev_start) & (df_daily["date"] <= prev_end)].copy()
            df_period["key"] = df_period["date"].dt.strftime("%m-%d")
            df_prev["key"] = df_prev["date"].dt.strftime("%m-%d")

            df_prev = df_prev[["key", "date", col_name]].rename(
                columns={"date": "prev_date", col_name: f"{col_name}_prev"}
            )
            df_comp = df_period.merge(
                df_prev,
                on="key",
                how="left",
            )

            fig.add_trace(
                go.Scatter(
                    x=df_comp["date"],
                    y=df_comp[col_name],
                    mode="lines",
                    name=f"{metric_name} (Năm nay)",
                    line=dict(color=color, width=3),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_comp["date"],
                    y=df_comp[f"{col_name}_prev"],
                    mode="lines",
                    name=f"{metric_name} (Năm trước)",
                    line=dict(color=color, width=2, dash="dash"),
                    opacity=0.6,
                    customdata=df_comp["prev_date"],
                    hovertemplate=(
                        "%{customdata|%b %d, %Y}<br>"
                        f"{metric_name} (Năm trước): "
                        + ("%{y:.2f}%" if metric_name == "Return Rate" else "%{y:,.0f}")
                        + "<extra></extra>"
                    ),
                )
            )

        # Ghi chú đỉnh - đáy
        series = df_period[col_name]
        if series.notna().any():
            idx_max = series.idxmax()
            idx_min = series.idxmin()
            fig.add_annotation(
                x=df_period.loc[idx_max, "date"],
                y=df_period.loc[idx_max, col_name],
                text="Đỉnh",
                showarrow=True,
                arrowcolor=color,
                font=dict(color=color),
            )
            fig.add_annotation(
                x=df_period.loc[idx_min, "date"],
                y=df_period.loc[idx_min, col_name],
                text="Đáy",
                showarrow=True,
                arrowcolor=color,
                font=dict(color=color),
            )

    else:
        # Nhiều chỉ số -> so sánh tương quan kỳ hiện tại
        for metric_name in metrics_selected:
            col_name, color = metric_map[metric_name]
            fig.add_trace(
                go.Scatter(
                    x=df_period["date"],
                    y=df_period[col_name],
                    mode="lines",
                    name=f"{metric_name} (MA7)",
                    line=dict(color=color, width=2.8),
                )
            )

            # Ghi chú đỉnh - đáy
            series = df_period[col_name]
            if series.notna().any():
                idx_max = series.idxmax()
                idx_min = series.idxmin()
                fig.add_annotation(
                    x=df_period.loc[idx_max, "date"],
                    y=df_period.loc[idx_max, col_name],
                    text=f"{metric_name} - Đỉnh",
                    showarrow=True,
                    arrowcolor=color,
                    font=dict(color=color),
                )
                fig.add_annotation(
                    x=df_period.loc[idx_min, "date"],
                    y=df_period.loc[idx_min, col_name],
                    text=f"{metric_name} - Đáy",
                    showarrow=True,
                    arrowcolor=color,
                    font=dict(color=color),
                )

    fig.update_layout(
        title="XU HƯỚNG THEO THỜI GIAN (MA7)",
        template="plotly_white",
        height=520,
        margin=dict(l=60, r=40, t=70, b=50),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(title="Chú thích", orientation="h", y=1.02, x=0.5, xanchor="center"),
    )

    fig.update_xaxes(title_text="Thời gian", rangeslider=dict(visible=True), showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLOR_GRID, title_text="Giá trị")

    apply_plot_style(fig)

    st.plotly_chart(fig, use_container_width=True)


# =========================
# 6) TREEMAP
# =========================
def create_treemap(df_items_f, margin_threshold):
    if df_items_f.empty:
        st.info("Không có dữ liệu danh mục trong khoảng thời gian đã chọn.")
        return

    df_grouped = (
        df_items_f.groupby(["category", "segment"], as_index=False)
        .agg(revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum"))
    )
    df_grouped["gross_margin"] = np.where(
        df_grouped["revenue"] != 0,
        df_grouped["gross_profit"] / df_grouped["revenue"],
        np.nan,
    )

    df_grouped["revenue_str"] = df_grouped["revenue"].apply(dinh_dang_vnd)
    df_grouped["profit_str"] = df_grouped["gross_profit"].apply(dinh_dang_vnd)
    df_grouped["margin_str"] = df_grouped["gross_margin"].apply(dinh_dang_ty_le)

    fig = px.treemap(
        df_grouped,
        path=["category", "segment"],
        values="revenue",
        color="gross_margin",
        color_continuous_scale=TREEMAP_SCALE,
        color_continuous_midpoint=margin_threshold,
        custom_data=["revenue_str", "profit_str", "margin_str"],
    )

    fig.update_traces(
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>%{value:,.0f} VNĐ",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Doanh thu: %{customdata[0]}<br>"
            "Lợi nhuận gộp: %{customdata[1]}<br>"
            "Biên lợi nhuận: %{customdata[2]}<extra></extra>"
        ),
        marker=dict(line=dict(color="white", width=2)),
    )

    fig.update_layout(
        title="CƠ CẤU DOANH THU & BIÊN LỢI NHUẬN THEO DANH MỤC",
        template="plotly_white",
        height=600,
        margin=dict(t=70, l=20, r=20, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(font=dict(color="#111827", size=12)),
            tickfont=dict(color="#1f2937", size=11),
        )
    )
    apply_plot_style(fig)

    st.plotly_chart(fig, use_container_width=True)


# =========================
# 7) TRAFFIC VS ORDERS VS CR
# =========================
def create_traffic_chart(df_orders_f, df_web_f, start_date, end_date):
    if df_web_f.empty:
        st.info("Không có dữ liệu web traffic trong khoảng thời gian đã chọn.")
        return

    # Xác định cột visits
    visits_col = "sessions" if "sessions" in df_web_f.columns else "unique_visitors"

    traffic_daily = (
        df_web_f.groupby("date", as_index=False)
        .agg(luot_truy_cap=(visits_col, "sum"))
    )
    orders_daily = (
        df_orders_f.groupby("order_date", as_index=False)
        .agg(so_don_hang=("order_id", "count"))
        .rename(columns={"order_date": "date"})
    )

    df_conv = pd.merge(traffic_daily, orders_daily, on="date", how="left")
    df_conv["so_don_hang"] = df_conv["so_don_hang"].fillna(0)

    df_conv["ty_le_chuyen_doi"] = np.where(
        df_conv["luot_truy_cap"] != 0,
        df_conv["so_don_hang"] / df_conv["luot_truy_cap"] * 100,
        np.nan,
    )

    df_conv = df_conv.sort_values("date")

    df_conv["so_don_hang_ma7"] = df_conv["so_don_hang"].rolling(window=7, min_periods=1).mean()
    df_conv["cr_ma7"] = df_conv["ty_le_chuyen_doi"].rolling(window=7, min_periods=1).mean()

    fig = go.Figure()

    # Bar visits nền
    fig.add_trace(
        go.Bar(
            x=df_conv["date"],
            y=df_conv["luot_truy_cap"],
            name="Lượt truy cập",
            marker=dict(color=COLOR_PINK),
            hovertemplate="%{x|%d/%m/%Y}<br>Lượt truy cập: %{y:,.0f}<extra></extra>",
        )
    )

    # Line orders MA7
    fig.add_trace(
        go.Scatter(
            x=df_conv["date"],
            y=df_conv["so_don_hang_ma7"],
            mode="lines",
            name="Số đơn hàng (MA7)",
            line=dict(color=COLOR_GOOD, width=3),
            hovertemplate="%{x|%d/%m/%Y}<br>Đơn hàng (MA7): %{y:,.2f}<extra></extra>",
            yaxis="y",
        )
    )

    # Line CR MA7 (trục phải)
    fig.add_trace(
        go.Scatter(
            x=df_conv["date"],
            y=df_conv["cr_ma7"],
            mode="lines",
            name="Tỷ lệ chuyển đổi (MA7)",
            line=dict(color=COLOR_WARN, width=3),
            hovertemplate="%{x|%d/%m/%Y}<br>CR (MA7): %{y:,.2f}%<extra></extra>",
            yaxis="y2",
        )
    )

    fig.update_layout(
        title="TƯƠNG QUAN LƯU LƯỢNG TRUY CẬP VÀ HIỆU QUẢ CHUYỂN ĐỔI (MA7)",
        template="plotly_white",
        height=600,
        margin=dict(l=60, r=60, t=70, b=50),
        legend=dict(title="Chú thích", orientation="h", y=1.02, x=0.5, xanchor="center"),
        barmode="overlay",
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    fig.update_xaxes(title_text="Thời gian", rangeslider=dict(visible=True), showgrid=False)
    fig.update_yaxes(title_text="Lượt truy cập / Số đơn hàng", showgrid=True, gridcolor=COLOR_GRID)

    fig.update_layout(
        yaxis2=dict(
            title="Tỷ lệ chuyển đổi (%)",
            overlaying="y",
            side="right",
            tickformat=".2f",
            ticksuffix="%",
            showgrid=False,
        )
    )
    apply_plot_style(fig)

    st.plotly_chart(fig, use_container_width=True)


# =========================
# 8) APP
# =========================
def main():
    st.title("🏛️ BẢNG ĐIỀU HÀNH CẤP CAO")
    st.caption("Dashboard quản trị chiến lược, nhanh chóng nắm bắt tình hình sức khỏe doanh nghiệp.")

    # Nạp dữ liệu
    df_products, df_orders, df_order_items, df_returns, df_web_traffic = nap_du_lieu(DATA_DIR)

    # Chuẩn bị bảng trung gian
    df_items = chuan_bi_order_items(df_orders, df_order_items, df_products)
    df_ret = chuan_bi_returns(df_returns, df_orders, df_products)

    # Sidebar filters
    st.sidebar.header("⚙️ Bộ lọc điều hành")

    min_date = min(df_orders["order_date"].min(), df_web_traffic["date"].min()).date()
    max_date = max(df_orders["order_date"].max(), df_web_traffic["date"].max()).date()

    date_range = st.sidebar.date_input(
        "Khoảng thời gian",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(date_range, tuple):
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    categories = sorted(df_products["category"].dropna().unique().tolist())
    segments = sorted(df_products["segment"].dropna().unique().tolist())

    selected_categories = st.sidebar.multiselect("Danh mục", categories, default=[])
    selected_segments = st.sidebar.multiselect("Phân khúc", segments, default=[])

    margin_threshold_pct = st.sidebar.slider("Ngưỡng biên lợi nhuận (%)", 0, 60, 30, 1)
    return_threshold_pct = st.sidebar.slider("Ngưỡng tỷ lệ trả hàng (%)", 0, 50, 15, 1)

    margin_threshold = margin_threshold_pct / 100
    return_threshold = return_threshold_pct / 100

    # Áp dụng filters
    # df_items_f, df_ret_f, df_orders_f, df_web_f = apply_filters(
    #     df_items, df_ret, df_orders, df_web_traffic,
    #     pd.Timestamp(start_date), pd.Timestamp(end_date),
    #     selected_categories, selected_segments
    # )
    df_items_f, df_ret_f, df_orders_f, df_web_f, df_items_cs, df_ret_cs, df_orders_cs = apply_filters(
        df_items, df_ret, df_orders, df_web_traffic,
        pd.Timestamp(start_date), pd.Timestamp(end_date),
        selected_categories, selected_segments
    )

    st.subheader("💎 KPI cốt lõi")
    create_kpis(df_items_f, df_ret_f, margin_threshold, return_threshold)

    st.subheader("📈Phân tích xu hướng (Time-series)")
    metrics_selected = st.multiselect(
        "Chọn chỉ số phân tích",
        ["Doanh thu", "Lợi nhuận", "COGS", "Return Rate"],
        default=["Doanh thu", "COGS"],
    )

    # Xu hướng dùng dữ liệu full theo category/segment
    if df_orders_cs.empty:
        st.info("Không có dữ liệu phù hợp để vẽ xu hướng.")
    else:
        full_start = df_orders_cs["order_date"].min()
        full_end = df_orders_cs["order_date"].max()
        df_daily_full = build_daily_metrics(df_items_cs, df_ret_cs, df_orders_cs, full_start, full_end)
        create_trend_chart(df_daily_full, metrics_selected, pd.Timestamp(start_date), pd.Timestamp(end_date))
    
    # df_daily = build_daily_metrics(df_items_f, df_ret_f, df_orders_f, pd.Timestamp(start_date), pd.Timestamp(end_date))
    # create_trend_chart(df_daily, metrics_selected, pd.Timestamp(start_date), pd.Timestamp(end_date))

    st.subheader("📦 Cơ cấu & Lưu lượng")
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        st.markdown("**Cơ cấu doanh thu & Biên lợi nhuận theo danh mục**")
        create_treemap(df_items_f, margin_threshold)

    with col_right:
        st.markdown("**Lưu lượng web & Chuyển đổi**")
        create_traffic_chart(df_orders_f, df_web_f, pd.Timestamp(start_date), pd.Timestamp(end_date))


if __name__ == "__main__":
    main()