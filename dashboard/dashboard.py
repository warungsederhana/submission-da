import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium, folium_static
from babel.numbers import format_currency
sns.set(style='dark')

def create_category_orders_df(df): 
    category_orders_df = df.groupby(by="product_category_name_english").agg(
        total_order=("order_id", "nunique"),
    ).sort_values(by="total_order", ascending=False).reset_index()
    category_orders_df.rename(columns={"product_category_name_english": "category"}, inplace=True)

    return category_orders_df

def create_monthly_orders_df(df):
    monthly_orders_df = df.resample(rule="M", on="order_purchase_timestamp").agg({
        "order_id": "nunique",
        "price": "sum"
    })
    monthly_orders_df.index = monthly_orders_df.index.strftime("%Y-%m")
    monthly_orders_df = monthly_orders_df.reset_index()
    monthly_orders_df.rename(columns={
    "order_purchase_timestamp": "order_date",
    "order_id": "total_order",
    "price": "revenue"
    }, inplace=True)

    return monthly_orders_df

def create_rfm_df(df):
    rfm_df = df.groupby(by="seller_id", as_index=False).agg({
        "order_purchase_timestamp": "max",
        "order_id": "nunique",
        "price": "sum"
    })
    rfm_df.columns = ["seller_id", "max_purchase_timestamp", "frequency", "monetary"]
    rfm_df["max_purchase_timestamp"] = rfm_df["max_purchase_timestamp"].dt.date
    recent_date = df["order_purchase_timestamp"].dt.date.max()
    rfm_df["recency"] = rfm_df["max_purchase_timestamp"].apply(lambda x: (recent_date - x).days)
    rfm_df.drop("max_purchase_timestamp", axis=1, inplace=True)
    rfm_df['identifier'] = [f"{i+1}" for i in range(len(rfm_df))]

    return rfm_df

def create_sales_by_state_df(df):
    sales_by_state_df = df.groupby(by="geolocation_state").agg({
        "order_id": "nunique",
        "geolocation_lat": "median",
        "geolocation_lng": "median"
    }).reset_index().sort_values(by="order_id", ascending=False).head(10)
    sales_by_state_df.rename(columns={"order_id": "total_order"}, inplace=True)

    return sales_by_state_df

def create_sales_by_city_df(df, state_filter):
    sales_by_city_df = df.groupby(by="geolocation_city").agg({
        "order_id": "nunique",
        "geolocation_state": "first",
        "geolocation_lat": "median",
        "geolocation_lng": "median"
    }).reset_index()
    sales_by_city_df.rename(columns={"order_id": "total_order"}, inplace=True)
    sales_by_city_df = sales_by_city_df[sales_by_city_df["geolocation_state"].isin(state_filter)]
    
    min_order = sales_by_city_df["total_order"].min()
    max_order = sales_by_city_df["total_order"].max()
    sales_by_city_df["normalized_order"] = (sales_by_city_df["total_order"] - min_order) / (max_order - min_order)

    return sales_by_city_df

if __name__ == "__main__":
    all_df = pd.read_csv("main_data.csv")
    
    datetime_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
        "shipping_limit_date",
    ]
    all_df.sort_values(by="order_purchase_timestamp", inplace=True)
    all_df.reset_index(inplace=True)

    for column in datetime_columns:
        all_df[column] = pd.to_datetime(all_df[column])
    
    min_date = all_df["order_purchase_timestamp"].min()
    max_date = all_df["order_purchase_timestamp"].max()

    with st.sidebar:
        st.image("../id-camp-remove-bg.png")
        
        start_date, end_date = st.date_input(
            label="Rentang Waktu",
            min_value= min_date,
            max_value= max_date,
            value=[min_date, max_date]
        )

    main_df = all_df[(all_df["order_purchase_timestamp"] >= str(start_date)) & (all_df["order_purchase_timestamp"] <= str(end_date))]

    category_orders_df = create_category_orders_df(main_df)
    monthly_orders_df = create_monthly_orders_df(main_df)
    rfm_df = create_rfm_df(main_df)
    sales_by_state_df = create_sales_by_state_df(main_df)
    state_filter = sales_by_state_df["geolocation_state"].values
    sales_by_city_df = create_sales_by_city_df(main_df, state_filter)

    st.title("Project Analisis Data: Public E-Commerce Dashboard")
    tab_pertanyaan_utama, tab_analisis_lanjutan = st.tabs(["Pertanyaan Utama", "Analisis Lanjutan"])

    with tab_pertanyaan_utama:
        st.header("Monthly Orders and Revenue")
        col1, col2 = st.columns(2)

        with col1: 
            total_order = monthly_orders_df.total_order.sum()
            st.metric("Total Orders", value=total_order)
        
        with col2: 
            total_revenue = monthly_orders_df.revenue.sum()
            st.metric("Total Revenue", value=format_currency(total_revenue, "BRL", locale="pt_BR"))

        fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(35, 30))
        ax[0].plot(
            monthly_orders_df["order_date"], 
            monthly_orders_df["total_order"], 
            marker="o", 
            color="#3498db",
        )
        ax[0].set_title("Monthly Orders", fontsize=50)
        ax[0].tick_params(axis="y", labelsize=25)
        ax[0].tick_params(axis="x", labelsize=20, rotation=45)

        ax[1].plot(
            monthly_orders_df["order_date"], 
            monthly_orders_df["revenue"], 
            marker="o", 
            color="#3498db",
        )
        ax[1].set_title("Monthly Revenue", fontsize=50)
        ax[1].tick_params(axis="y", labelsize=25)
        ax[1].tick_params(axis="x", labelsize=20, rotation=45)
        st.pyplot(fig)


        st.header("Best and Worst Selling Product Categories")
        fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(35, 15))
        colors = ["#3498db", "#D3D3D3", "#D3D3D3", "#D3D3D3", "#D3D3D3"]
        sns.barplot(
            x="total_order", 
            y="category", 
            data=category_orders_df.head(5), 
            ax=ax[0], 
            palette=colors
        )
        ax[0].set_ylabel(None)
        ax[0].set_xlabel("Number of Orders", fontsize=30)
        ax[0].set_title("Best performing categories by total orders", loc="center", fontsize=50)
        ax[0].tick_params(axis="y", labelsize=35)
        ax[0].tick_params(axis='x', labelsize=30)

        sns.barplot(
            x="total_order", 
            y="category", 
            data=category_orders_df.sort_values(by="total_order", ascending=True).head(), 
            ax=ax[1], 
            palette=colors
        )
        ax[1].set_ylabel(None)
        ax[1].set_xlabel("Number of Orders", fontsize=30)
        ax[1].invert_xaxis()
        ax[1].yaxis.set_label_position("right")
        ax[1].yaxis.tick_right()
        ax[1].set_title("Worst performing categories by total orders", loc="center", fontsize=50)
        ax[1].tick_params(axis="y", labelsize=35)
        ax[1].tick_params(axis="x", labelsize=30)

        st.pyplot(fig)
    
    with tab_analisis_lanjutan:
        st.header("Best Sellers Based on RFM Analysis")
        col1, col2, col3 = st.columns(3)

        with col1: 
            avg_recency = round(rfm_df.recency.mean(), 1)
            st.metric("Average Recency", value=avg_recency)

        with col2: 
            avg_frequency = round(rfm_df.frequency.mean(), 1)
            st.metric("Average Frequency", value=avg_frequency)
        
        with col3:
            avg_monetary = round(rfm_df.monetary.mean(), 1)
            st.metric("Average Monetary", value=avg_monetary)
        
        fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(35, 30))
        colors = colors = ["#72BCD4", "#72BCD4", "#72BCD4", "#72BCD4", "#72BCD4"]

        sns.barplot(
            y="recency",
            x="identifier",
            data=rfm_df.sort_values(by="recency", ascending=True).head(),
            ax=ax[0],
            palette=colors
        )
        ax[0].set_ylabel(None)
        ax[0].set_xlabel("seller", fontsize=30)
        ax[0].set_title("By Recency (days)", loc="center", fontsize=50)
        ax[0].tick_params(axis='y', labelsize=30)
        ax[0].tick_params(axis='x', labelsize=35, rotation=45)

        sns.barplot(
            y="frequency", 
            x="identifier", 
            data=rfm_df.sort_values(by="frequency", ascending=False).head(), 
            ax=ax[1], 
            palette=colors
        )
        ax[1].set_ylabel(None)
        ax[1].set_xlabel("seller", fontsize=30)
        ax[1].set_title("By Frequency", loc="center", fontsize=50)
        ax[1].tick_params(axis='y', labelsize=30)
        ax[1].tick_params(axis='x', labelsize=35, rotation=45)

        sns.barplot(
            y="monetary", 
            x="identifier", 
            data=rfm_df.sort_values(by="monetary", ascending=False).head(), 
            ax=ax[2], 
            palette=colors
        )
        ax[2].set_ylabel(None)
        ax[2].set_xlabel("seller", fontsize=30)
        ax[2].set_title("By Monetary", loc="center", fontsize=50)
        ax[2].tick_params(axis='y', labelsize=30)
        ax[2].tick_params(axis='x', labelsize=35, rotation=45)

        legend_elements = [
            plt.Line2D([0], [0], color='b', lw=4, label=f'{row.identifier}: {row.seller_id}') 
            for _, row in rfm_df.sort_values(by="recency", ascending=True).head().iterrows()
        ] + [
            plt.Line2D([0], [0], color='g', lw=4, label=f'{row.identifier}: {row.seller_id}') 
            for _, row in rfm_df.sort_values(by="frequency", ascending=False).head().iterrows()
        ] + [
            plt.Line2D([0], [0], color='r', lw=4, label=f'{row.identifier}: {row.seller_id}') 
            for _, row in rfm_df.sort_values(by="monetary", ascending=False).head().iterrows()
        ]
        fig.legend(handles=legend_elements, loc='lower center', ncol=3, fontsize=40)
        plt.tight_layout(rect=[0, 0.2, 1, 1]) 

        st.pyplot(fig)

        st.header("Sales by State")
        map_center = [
            sales_by_state_df["geolocation_lat"].median(), 
            sales_by_state_df["geolocation_lng"].median()
        ]
        sales_map = folium.Map(location=map_center, zoom_start=4, max_zoom=7)
        marker_cluster = MarkerCluster().add_to(sales_map)

        for rank, (_, row) in enumerate(sales_by_state_df.iterrows(), 1):
            if not pd.isnull(row["geolocation_lat"]) and not pd.isnull(row["geolocation_lng"]):
                folium.Marker(
                    location=[row["geolocation_lat"], row["geolocation_lng"]],
                    popup=f"Rank: {rank}\nState: {row['geolocation_state']}\nTotal Orders: {row['total_order']}",
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(marker_cluster)

        heat_data = [
            [row["geolocation_lat"], 
            row["geolocation_lng"], 
            row["normalized_order"]] for _, row in sales_by_city_df.iterrows()
        ]
        HeatMap(
            heat_data, 
            radius=15,
            max_zoom=7,
            blur=15,
        ).add_to(sales_map)
        folium_static(sales_map, width=700, height=500 )

        fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(35, 20))
        colors = ["#3498db", "#D3D3D3", "#D3D3D3", "#D3D3D3", "#D3D3D3"]

        sns.barplot(
            x="total_order", 
            y="geolocation_state", 
            data=sales_by_state_df.head(), 
            ax=ax[0], 
            palette=colors
        )
        ax[0].set_ylabel(None)
        ax[0].set_xlabel(None)
        ax[0].set_title("Top 5 states by total orders", loc="center", fontsize=50)
        ax[0].tick_params(axis="y", labelsize=35)
        ax[0].tick_params(axis="x", labelsize=30)

        sns.barplot(
            x="total_order", 
            y="geolocation_state", 
            data=sales_by_state_df.sort_values(by="total_order", ascending=True).head(), 
            ax=ax[1], 
            palette=colors
        )
        ax[1].set_ylabel(None)
        ax[1].set_xlabel(None)
        ax[1].set_title("Bottom 5 states by total orders", loc="center", fontsize=50)
        ax[1].tick_params(axis="y", labelsize=35)
        ax[1].invert_xaxis()
        ax[1].yaxis.set_label_position("right")
        ax[1].yaxis.tick_right()
        ax[1].tick_params(axis="x", labelsize=30)

        st.pyplot(fig)