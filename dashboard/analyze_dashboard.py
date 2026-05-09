import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# CẤU HÌNH TRANG & BẢNG MÀU CHỦ ĐẠO
# ==========================================
st.set_page_config(page_title="Chất Lượng Tăng Trưởng E-Commerce", page_icon="🛒", layout="wide")

MAIN_BLUE = '#1f77b4'       
LIGHT_BLUE = '#aec7e8'      
DARK_BLUE = '#08306b'       
ORANGE_WARN = '#ff7f0e'     
COLOR_BG = "#ffffff"
COLOR_GRID = "rgba(0,0,0,0.05)"

# ==========================================
# CUSTOM CSS LÀM ĐẸP THẺ KPI (CARDS)
# Đã cập nhật tag "stMetric" chuẩn của Streamlit mới nhất
# ==========================================
st.markdown("""
<style>
div[data-testid="stMetric"] {
    background-color: #f8fbfd;
    border: 2px solid #aec7e8;
    padding: 15px 20px;
    border-radius: 10px;
    box-shadow: 2px 2px 10px rgba(31, 119, 180, 0.15);
    transition: transform 0.2s, border-color 0.2s;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    border-color: #1f77b4;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# HÀM ĐỌC DỮ LIỆU THỰC TẾ
# ==========================================
@st.cache_data
def load_and_prep_data():
    current_file_path = Path(__file__).resolve()
    DATA_RAW_PATH = current_file_path.parent.parent / 'data' / 'main' / 'raw'
    
    orders = pd.read_csv(DATA_RAW_PATH / 'orders.csv', parse_dates=['order_date'])
    order_items = pd.read_csv(DATA_RAW_PATH / 'order_items.csv')
    products = pd.read_csv(DATA_RAW_PATH / 'products.csv')
    geography = pd.read_csv(DATA_RAW_PATH / 'geography.csv')
    traffic = pd.read_csv(DATA_RAW_PATH / 'web_traffic.csv', parse_dates=['date'])
    
    products['category'] = products['category'].fillna('Chưa phân loại')
    geography['region'] = geography['region'].fillna('Chưa xác định')
    orders['order_source'] = orders['order_source'].fillna('Chưa xác định')
    
    orders_geo = orders.merge(geography[['zip', 'region']], on='zip', how='left')
    items_prod = order_items.merge(products[['product_id', 'category', 'cogs']], on='product_id', how='left')
    
    items_prod['item_revenue'] = (items_prod['quantity'] * items_prod['unit_price']) - items_prod['discount_amount'].fillna(0)
    items_prod['item_cogs'] = items_prod['quantity'] * items_prod['cogs']
    items_prod['item_profit'] = items_prod['item_revenue'] - items_prod['item_cogs']
    items_prod['has_promo'] = items_prod['promo_id'].notna().astype(int)
    
    df_master = items_prod.merge(orders_geo, on='order_id', how='inner')
    
    return df_master, traffic, orders

try:
    df_master, traffic, orders = load_and_prep_data()
except Exception as e:
    st.error(f"Lỗi hệ thống khi đọc dữ liệu: {e}")
    st.stop()

# ==========================================
# SIDEBAR - BỘ LỌC TỰ ĐỘNG
# ==========================================
with st.sidebar:
    st.markdown("## 🛒 Bộ Lọc Phân Tích")
    
    min_date = df_master['order_date'].min().date()
    max_date = df_master['order_date'].max().date()
    start_date, end_date = st.date_input("Khoảng thời gian", [min_date, max_date], min_value=min_date, max_value=max_date)
    
    categories = sorted(df_master['category'].astype(str).unique().tolist())
    selected_cats = st.multiselect("Danh mục sản phẩm", categories, default=categories)
    
    regions = sorted(df_master['region'].astype(str).unique().tolist())
    selected_regions = st.multiselect("Khu vực địa lý", regions, default=regions)

mask = (
    (df_master['order_date'].dt.date >= start_date) & 
    (df_master['order_date'].dt.date <= end_date) &
    (df_master['category'].isin(selected_cats)) &
    (df_master['region'].isin(selected_regions))
)
df_filtered = df_master[mask]

if df_filtered.empty:
    st.warning("Không có dữ liệu cho bộ lọc hiện tại. Vui lòng chọn lại!")
    st.stop()

# ==========================================
# THẺ ĐIỂM KPI (METRICS CARDS)
# ==========================================
st.title("🛒 Đánh Giá Chất Lượng Tăng Trưởng Toàn Diện")
st.markdown("*Phân tích chuyên sâu sự cân bằng giữa Doanh thu, Lợi nhuận và hiệu quả Khuyến mãi.*")

total_revenue = df_filtered['item_revenue'].sum()
gross_profit = df_filtered['item_profit'].sum()
profit_margin = (gross_profit / total_revenue) * 100 if total_revenue > 0 else 0
promo_rate = (df_filtered['has_promo'].sum() / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0

t_mask = (traffic['date'].dt.date >= start_date) & (traffic['date'].dt.date <= end_date)
total_sessions = traffic[t_mask]['sessions'].sum()
unique_orders = df_filtered['order_id'].nunique()
conversion_rate = (unique_orders / total_sessions) * 100 if total_sessions > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
with col1: st.metric("💰 TỔNG DOANH THU", f"₫{total_revenue / 1e9:.2f} Tỷ")
with col2: st.metric("📈 LỢI NHUẬN GỘP", f"₫{gross_profit / 1e9:.2f} Tỷ")
with col3: st.metric("🎯 BIÊN LỢI NHUẬN", f"{profit_margin:.1f}%")
with col4: st.metric("🎁 TỶ LỆ KHUYẾN MÃI", f"{promo_rate:.1f}%")
with col5: st.metric("🔄 CHUYỂN ĐỔI (CR)", f"{conversion_rate:.2f}%")

st.divider()

# ==========================================
# RENDER LAYOUT 2x2
# ==========================================
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

# ------------------------------------------
# BIỂU ĐỒ 1: TỔNG QUAN DOANH THU & LỢI NHUẬN
# ------------------------------------------
with row1_col1:
    st.subheader("1. Tương quan Doanh thu & Khuyến mãi (Theo Năm)")
    df_trend = df_filtered.copy()
    df_trend['Year'] = df_trend['order_date'].dt.year
    df_trend = df_trend.groupby('Year').agg({'item_revenue':'sum', 'item_profit':'sum', 'has_promo':'mean'}).reset_index()
    df_trend['Biên lợi nhuận (%)'] = (df_trend['item_profit'] / df_trend['item_revenue']) * 100
    df_trend['Tỷ lệ Khuyến mãi (%)'] = df_trend['has_promo'] * 100

    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Bar(x=df_trend['Year'], y=df_trend['item_revenue'], name='Doanh Thu (VNĐ)', marker_color=LIGHT_BLUE, opacity=0.8), secondary_y=False)
    fig1.add_trace(go.Scatter(x=df_trend['Year'], y=df_trend['Biên lợi nhuận (%)'], name='Biên Lợi Nhuận (%)', mode='lines+markers', marker=dict(symbol='square', size=8), line=dict(color=DARK_BLUE, width=3)), secondary_y=True)
    fig1.add_trace(go.Scatter(x=df_trend['Year'], y=df_trend['Tỷ lệ Khuyến mãi (%)'], name='Tỷ lệ Khuyến mãi (%)', mode='lines+markers', marker=dict(symbol='circle', size=8), line=dict(color=ORANGE_WARN, width=3, dash='dash')), secondary_y=True)

    fig1.update_layout(plot_bgcolor=COLOR_BG, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), margin=dict(t=40, b=20, l=0, r=0))
    fig1.update_xaxes(type='category', title_text="Năm")
    fig1.update_yaxes(title_text="Doanh thu (VNĐ)", gridcolor=COLOR_GRID, secondary_y=False)
    
    max_pct = max(df_trend['Biên lợi nhuận (%)'].max(), df_trend['Tỷ lệ Khuyến mãi (%)'].max())
    fig1.update_yaxes(title_text="Phần trăm (%)", showgrid=False, secondary_y=True, range=[0, max_pct * 1.3])
    st.plotly_chart(fig1, use_container_width=True)

# ------------------------------------------
# BIỂU ĐỒ 2: PHÂN PHỐI KDE PLOT (TÔ MÀU MIỀN)
# ------------------------------------------
with row1_col2:
    st.subheader("2. Phân Phối Biên Lợi Nhuận Gộp")
    df_order_prof = df_filtered.groupby(['order_id', 'has_promo']).agg({'item_revenue':'sum', 'item_profit':'sum'}).reset_index()
    df_order_prof = df_order_prof[df_order_prof['item_revenue'] > 0]
    df_order_prof['margin'] = (df_order_prof['item_profit'] / df_order_prof['item_revenue']) * 100
    df_order_prof = df_order_prof[(df_order_prof['margin'] >= -50) & (df_order_prof['margin'] <= 100)]
    
    promo_margins = df_order_prof[df_order_prof['has_promo'] == 1]['margin'].tolist()
    nopromo_margins = df_order_prof[df_order_prof['has_promo'] == 0]['margin'].tolist()
    
    hist_data = [nopromo_margins, promo_margins]
    group_labels = ['Không Khuyến Mãi', 'Có Khuyến Mãi']
    colors = [MAIN_BLUE, ORANGE_WARN]

    fig2 = ff.create_distplot(hist_data, group_labels, show_hist=False, show_rug=False, colors=colors)
    
    # Kỹ thuật tô màu miền (Fill area) với độ trong suốt nhạt
    for trace in fig2.data:
        trace.update(fill='tozeroy')
        if trace.name == 'Không Khuyến Mãi':
            trace.fillcolor = 'rgba(31, 119, 180, 0.2)' # Xanh dương nhạt
        elif trace.name == 'Có Khuyến Mãi':
            trace.fillcolor = 'rgba(255, 127, 14, 0.2)' # Cam nhạt
            
    mean_promo = np.mean(promo_margins)
    mean_nopromo = np.mean(nopromo_margins)
    
    fig2.add_vline(x=mean_promo, line_dash="dash", line_color=ORANGE_WARN, line_width=2)
    fig2.add_vline(x=mean_nopromo, line_dash="dash", line_color=MAIN_BLUE, line_width=2)
    
    fig2.add_annotation(x=mean_promo - 2, y=0.015, text=f"Trung bình:<br>{mean_promo:.1f}%", showarrow=False, font=dict(color=ORANGE_WARN, size=12), xanchor="right")
    fig2.add_annotation(x=mean_nopromo + 2, y=0.015, text=f"Trung bình:<br>{mean_nopromo:.1f}%", showarrow=False, font=dict(color=MAIN_BLUE, size=12), xanchor="left")

    fig2.update_layout(plot_bgcolor=COLOR_BG, margin=dict(t=40, b=20, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig2.update_xaxes(title_text="Biên Lợi Nhuận Gộp (%)", gridcolor=COLOR_GRID)
    fig2.update_yaxes(title_text="Mật độ đơn hàng", gridcolor=COLOR_GRID)
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------
# BIỂU ĐỒ 3: TRAFFIC & CONVERSION RATE (FIX LỖI NGÀY THÁNG)
# ------------------------------------------
with row2_col1:
    st.subheader("3. Lưu Lượng & Tỷ Lệ Chuyển Đổi")
    
    traffic_filtered = traffic[t_mask].groupby(traffic['date'].dt.to_period('M'))['sessions'].sum().reset_index()
    # Fix: Chỉ giữ lại đúng Ngày mùng 1 của tháng để làm Timestamp sạch
    traffic_filtered['Month'] = traffic_filtered['date'].dt.to_timestamp()
    
    orders_filtered = orders[(orders['order_date'].dt.date >= start_date) & (orders['order_date'].dt.date <= end_date)]
    monthly_orders = orders_filtered.groupby(orders_filtered['order_date'].dt.to_period('M'))['order_id'].nunique().reset_index()
    monthly_orders['Month'] = monthly_orders['order_date'].dt.to_timestamp()
    
    df_pred = traffic_filtered.merge(monthly_orders, on='Month', how='left').fillna(0)
    df_pred['CR (%)'] = (df_pred['order_id'] / df_pred['sessions']) * 100

    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
    fig3.add_trace(go.Bar(x=df_pred['Month'], y=df_pred['CR (%)'], name='CR (%)', marker_color=LIGHT_BLUE, opacity=0.6), secondary_y=True)
    fig3.add_trace(go.Scatter(x=df_pred['Month'], y=df_pred['sessions'], name='Lượt truy cập', mode='lines', line=dict(color=DARK_BLUE, width=3)), secondary_y=False)

    # Fix: Ép định dạng tick format là Tháng-Năm (Ví dụ: 04-2013)
    fig3.update_xaxes(
        title_text="Tháng - Năm", 
        dtick="M4", # Nhảy bước 4 tháng 1 lần
        tickformat="%m-%Y", # Format chuỗi rõ ràng, không hiện giờ phút
        tickangle=-45, 
        gridcolor=COLOR_GRID
    )
    
    fig3.update_layout(plot_bgcolor=COLOR_BG, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), margin=dict(t=40, b=20, l=0, r=0))
    fig3.update_yaxes(title_text="Lượt truy cập", gridcolor=COLOR_GRID, secondary_y=False)
    fig3.update_yaxes(title_text="Tỷ lệ chuyển đổi (%)", showgrid=False, secondary_y=True)
    st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------
# BIỂU ĐỒ 4: MA TRẬN KÊNH TIẾP THỊ
# ------------------------------------------
with row2_col2:
    st.subheader("4. Ma Trận Tối Ưu Kênh Tiếp Thị")
    df_channel = df_filtered.groupby('order_source').agg({'item_revenue':'sum', 'item_profit':'sum', 'order_id':'nunique'}).reset_index()
    df_channel = df_channel[df_channel['item_revenue'] > 0] 
    df_channel['Biên Lợi Nhuận TB (%)'] = (df_channel['item_profit'] / df_channel['item_revenue']) * 100
    df_channel['Doanh Thu (Tỷ VNĐ)'] = df_channel['item_revenue'] / 1e9

    fig4 = px.scatter(df_channel, x="Doanh Thu (Tỷ VNĐ)", y="Biên Lợi Nhuận TB (%)", size="order_id", color="order_source",
                      hover_name="order_source", text="order_source", size_max=60,
                      color_discrete_sequence=px.colors.sequential.Blues_r)

    fig4.update_traces(textposition='top center', 
                       textfont=dict(color=DARK_BLUE, size=11, family="Arial Black"),
                       marker=dict(line=dict(width=1.5, color=DARK_BLUE)))

    mean_margin = df_channel['Biên Lợi Nhuận TB (%)'].mean()
    if not pd.isna(mean_margin):
        fig4.add_hline(y=mean_margin, line_dash="dash", line_color=DARK_BLUE, opacity=0.6, annotation_text="Trung bình Sàn", annotation_position="bottom right", annotation_font=dict(color=DARK_BLUE, style='italic'))

    fig4.update_layout(plot_bgcolor=COLOR_BG, margin=dict(t=40, b=20, l=0, r=0), showlegend=True, legend=dict(title="Kênh Tiếp Thị", yanchor="top", y=1, xanchor="left", x=1.02))
    fig4.update_xaxes(title_text="Quy mô Doanh thu Thực tế (Tỷ VNĐ)", gridcolor=COLOR_GRID)
    fig4.update_yaxes(title_text="Biên Lợi Nhuận Gộp (%)", gridcolor=COLOR_GRID)
    
    st.plotly_chart(fig4, use_container_width=True)