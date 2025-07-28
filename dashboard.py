import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
from geopy.distance import geodesic
import random
import base64
import json
from gpt_risk_checker import analyze_risk_with_gpt
import streamlit as st
import time



def load_geojson_layer(file_path, color=[255, 255, 255]):
    with open(file_path, "r") as f:
        geojson_data = json.load(f)

    return pdk.Layer(
        "GeoJsonLayer",
        geojson_data,
        get_fill_color=color + [30],  
        get_line_color=color + [200], 
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False,
    )

# Encode each aircraft icon to Base64
def encode_image_to_base64(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# File paths 
green_plane = "icons/green_plane.png"
yellow_plane = "icons/yellow_plane.png"
red_plane = "icons/red_plane.png"

green_base64 = encode_image_to_base64(green_plane)
yellow_base64 = encode_image_to_base64(yellow_plane)
red_base64 = encode_image_to_base64(red_plane)


# === PAGE CONFIG ===
st.set_page_config(page_title="AeroLogic ATC Dashboard", layout="wide")
tab1, tab2 = st.tabs(["🗺️ Dashboard", "📋 Aircraft And Weather Overview"])
# === STYLE ===
st.markdown("""
    <style>
    body { background-color: #0f1117; color: white; }
    .group-box {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #333;
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 0.5rem;
        color: white;
    }
    .alert-good { color: #00FF7F; }
    .alert-warn { color: #FFD700; }
    .alert-bad  { color: #FF6347; }
    </style>
""", unsafe_allow_html=True)
@st.cache_resource
def get_geojson_layers():
    apt = load_geojson_layer("data/sa_apt.geojson", color=[0, 255, 0])     
    asp = load_geojson_layer("data/sa_asp.geojson", color=[255, 255, 0])   
    nav = load_geojson_layer("data/sa_nav.geojson", color=[0, 150, 255])   
    return apt, asp, nav

with tab1:
    st.title("🛫 AeroLogic – Air Traffic Control Dashboard")

    OWM_API_KEY = "c58e3fc9881cec96c41a3ff8d5b83089"

    # === Load aircraft data ===
    @st.cache_data(ttl=30)
    def load_opensky_data():
        url = "https://opensky-network.org/api/states/all"
        response = requests.get(url)
        if response.status_code != 200:
            return pd.DataFrame()
        data = response.json()
        if not data.get("states"):
            return pd.DataFrame()
        columns = [
            "icao24", "callsign", "origin_country", "time_position", "last_contact",
            "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
            "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
            "spi", "position_source"
        ]
        df = pd.DataFrame(data["states"], columns=columns)
        df = df.dropna(subset=["latitude", "longitude"])
        return df

    df = load_opensky_data()

    # === Filter to Saudi Arabia ===
    def is_within_saudi(lat, lon):
        return 16.0 <= lat <= 32.0 and 34.0 <= lon <= 56.0

    df_sa = df[df.apply(lambda row: is_within_saudi(row["latitude"], row["longitude"]), axis=1)]
    df_sa = df_sa.copy()
    df_sa = df_sa.head(20) 

    # === Weather ===
    def get_weather(lat, lon):
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric"
            response = requests.get(url)
            data = response.json()
            return {
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "description": data["weather"][0]["description"]
            }
        except:
            return None
# === [❌] Load frequency data from CSV — DISABLED TEMPORARILY ===
# @st.cache_data
# def load_frequencies_from_csv():
#     df_freq = pd.read_csv("data/frequencies.csv")
#     df_airports = pd.read_csv("data/airports.csv")
#     df_combined = df_freq.merge(df_airports, left_on="airport_ident", right_on="ident")
#     df_sa = df_combined[df_combined["iso_country"] == "SA"]

#     df_sa_cleaned = pd.DataFrame({
#         "lon": df_sa["longitude_deg"],
#         "lat": df_sa["latitude_deg"],
#         "frequency": df_sa["frequency_mhz"],
#         "icao": df_sa["ident"]
#     })

#     return df_sa_cleaned

    # === Alerts ===
    def detect_conflicts_and_warnings(df, min_distance_km=10, min_safe_altitude=500):
        alerts = []
        for _, row in df.iterrows():
            if row["baro_altitude"] is not None and row["baro_altitude"] < min_safe_altitude:
                alerts.append({"type": "MSAW", "callsign": row["callsign"],
                            "msg": f"⚠️ {row['callsign']} flying below safe altitude ({row['baro_altitude']:.0f} m)"})
        for i in range(len(df)):
            for j in range(i + 1, len(df)):
                pos1 = (df.iloc[i]["latitude"], df.iloc[i]["longitude"])
                pos2 = (df.iloc[j]["latitude"], df.iloc[j]["longitude"])
                if geodesic(pos1, pos2).km < min_distance_km:
                    alerts.append({"type": "STCA", "callsign": f"{df.iloc[i]['callsign']} & {df.iloc[j]['callsign']}",
                                "msg": f"❗Conflict: {df.iloc[i]['callsign']} and {df.iloc[j]['callsign']} too close"})
        return alerts
#-------------------------------------------------


    def show_warning_popup(message):
        st.markdown(
            f"""
            <div style="
                position: fixed;
                top: 30%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: #1f1f1f;
                color: #fff;
                border: 4px solid red;
                padding: 30px;
                border-radius: 12px;
                font-size: 18px;
                font-family: monospace;
                text-align: center;
                z-index: 9999;
                animation: fadeOut 7s forwards;
            ">
                🚨 <strong>AI WARNING</strong><br><br>
                {message}
            </div>

            <style>
            @keyframes fadeOut {{
                0% {{ opacity: 1; }}
                80% {{ opacity: 1; }}
                100% {{ opacity: 0; display: none; }}
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
        time.sleep(7)
    #------------------------------------------------------
    # === SEARCH FILTER ===
    callsign_search = st.text_input("🔍 Search by Callsign")
    if callsign_search:
        df_sa = df_sa[df_sa["callsign"].str.contains(callsign_search, case=False, na=False)]

    # === TABS FOR MAP ===
    map_tab = st.radio("🧭 Map View", ["Separation", "Load", "Weather"], horizontal=True)

    # === MAIN LAYOUT ===
    left, center, right = st.columns([2, 5, 2])

    # === LEFT: Alerts + Quick Actions ===
    with left:
        alerts = detect_conflicts_and_warnings(df_sa)
        random.shuffle(alerts)
        summary_alerts = alerts[:3] if len(alerts) >= 3 else alerts

        st.markdown('<div class="group-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚨 Alerts</div>', unsafe_allow_html=True)

        if not alerts:
            st.markdown("<p style='color:gray;'>✅ No current alerts.</p>", unsafe_allow_html=True)
        else:
            for alert in summary_alerts:
                color = "#FFD700" if alert["type"] == "MSAW" else "#FF6347"
                st.markdown(f"<p style='color:{color}; margin:2px 0;'>{alert['msg']}</p>", unsafe_allow_html=True)

            with st.expander("🔎 View All Alerts"):
                for alert in alerts:
                    color = "#FFD700" if alert["type"] == "MSAW" else "#FF6347"
                    st.markdown(f"""
                        <div style='margin: 4px 0; padding: 6px;
                            background-color:#262626; border-left: 4px solid {color};
                            border-radius: 4px;'>{alert['msg']}</div>
                    """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


        st.markdown('<div class="group-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⚙️ Quick Actions</div>', unsafe_allow_html=True)
        st.button("📅 Reschedule")
        st.button("✉️ Send Message")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="group-box">', unsafe_allow_html=True)

        st.subheader("🔊 Audio Risk Detection")

        transcript = st.text_area("Paste Transcript Text", "")

        if st.button("Analyze for Risk"):
            if transcript.strip() == "":
                st.warning("Please enter transcript text before analyzing.")
            else:
                st.info("🔍 Analyzing using AI model...")
                result = analyze_risk_with_gpt(transcript)
                
                if "WARNING" in result:
                    show_warning_popup(result)

                else:
                    st.success(result)


    
# === CENTER: Map ===
with center:
    conflict_callsigns = set()
    low_alt_callsigns = set()

    for alert in alerts:
        if alert["type"] == "STCA":
            conflict_callsigns.update(alert["callsign"].split(" & "))
        elif alert["type"] == "MSAW":
            low_alt_callsigns.add(alert["callsign"])

    def get_icon_base64(callsign):
        if callsign in conflict_callsigns:
            return red_base64
        elif callsign in low_alt_callsigns:
            return yellow_base64
        else:
            return green_base64

    df_sa["icon_data"] = df_sa.apply(lambda row: {
        "url": f"data:image/png;base64,{get_icon_base64(row['callsign'])}",
        "width": 64,
        "height": 64,
        "anchorY": 64,
        "angle": row["true_track"] if not pd.isna(row["true_track"]) else 0
    }, axis=1)

    df_sa["weather_info"] = df_sa.apply(lambda row: get_weather(row["latitude"], row["longitude"]), axis=1)

    df_sa["tooltip"] = df_sa.apply(lambda row: 
        f"✈ {row['callsign']}\n"
        f"🌍 Country: {row['origin_country']}\n"
        f"🛫 Alt: {row['baro_altitude']:.0f} m\n"
        f"🚀 Speed: {row['velocity']:.0f} m/s", axis=1)

    st.markdown('<div class="group-box">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">🗺️ Aircraft Map – View: {map_tab}</div>', unsafe_allow_html=True)

    if not df_sa.empty:
        view_state = pdk.ViewState(
            latitude=df_sa["latitude"].mean(),
            longitude=df_sa["longitude"].mean(),
            zoom=5,
            pitch=30
        )

        if map_tab == "Separation":
            layer = pdk.Layer(
                "IconLayer",
                data=df_sa,
                get_position='[longitude, latitude]',
                get_icon='icon_data',
                get_size=4,
                size_scale=15,
                pickable=True
            )
            tooltip = {
                "html": "<b>✈ {callsign}</b><br/>🌍 {origin_country}<br/>🛫 Alt: {baro_altitude} m<br/>🚀 Speed: {velocity} m/s",
                "style": {
                    "backgroundColor": "black",
                    "color": "white",
                    "fontSize": "12px"
                }
            }

            # === [❌] Frequency layer disabled ===
            # df_freq = load_frequencies_from_csv()
            # df_freq_sample = df_freq.sample(n=min(1, len(df_freq)))  # Limit to 1 for performance
            # freq_layer = pdk.Layer(
            #     "TextLayer",
            #     data=df_freq_sample,
            #     get_position='[lon, lat]',
            #     get_text='frequency',
            #     get_size=14,
            #     get_color=[0, 200, 255],
            #     get_angle=0,
            #     get_alignment_baseline='bottom'
            # )

          #  === [❌] Load GeoJSON with only 1 feature (Disabled for performance) ===
            def load_limited_geojson_layer(file_path, color=[255, 255, 255]):
                with open(file_path, "r") as f:
                    geojson_data = json.load(f)
                geojson_data["features"] = geojson_data["features"][:1]
                return pdk.Layer(
                    "GeoJsonLayer",
                    geojson_data,
                    get_fill_color=color + [30],
                    get_line_color=color + [200],
                    pickable=True,
                    stroked=True,
                    filled=True,
                    extruded=False,
                )

            apt_layer = load_limited_geojson_layer("data/sa_apt.geojson", color=[0, 255, 0])
            asp_layer = load_limited_geojson_layer("data/sa_asp.geojson", color=[255, 255, 0])
            nav_layer = load_limited_geojson_layer("data/sa_nav.geojson", color=[0, 150, 255])

            layers = [layer, apt_layer, asp_layer, nav_layer]  # Old full version
            layers = [layer, apt_layer, asp_layer, nav_layer]  # Even limited layers version
            layers = [layer]  #  Use only aircraft layer (iconLayer) for now
            

        elif map_tab == "Load":
            df_sa["congestion_score"] = [random.randint(1, 10) for _ in range(len(df_sa))]

            def get_congestion_color(score):
                if score >= 8:
                    return [255, 0, 0]  # Red
                elif score >= 5:
                    return [255, 255, 0]  # Yellow
                else:
                    return [0, 255, 0]  # Green

            df_sa["color"] = df_sa["congestion_score"].apply(get_congestion_color)
            layer = pdk.Layer(
                "HeatmapLayer",
                data=df_sa,
                get_position="[longitude, latitude]",
                get_weight="congestion_score",
                radiusPixels=60,
                colorRange=[
                    [0, 255, 0],
                    [255, 255, 0],
                    [255, 0, 0]
                ],
            )
            tooltip = None

        elif map_tab == "Weather":
            df_sa["temp"] = df_sa["weather_info"].apply(lambda x: x["temp"] if x else 0)
            layer = pdk.Layer(
                "HeatmapLayer",
                data=df_sa,
                get_position='[longitude, latitude]',
                get_weight='temp',
                radiusPixels=60
            )
            tooltip = None
        else:
            layers = []
            tooltip = None

        st.pydeck_chart(pdk.Deck(
            layers= [layer],
            initial_view_state=view_state,
            tooltip=tooltip
        ))

    else:
        st.warning("No aircraft currently over Saudi Arabia.")

    st.markdown('</div>', unsafe_allow_html=True)

    # === RIGHT: System Status + Congestion ===
    with right:
        st.markdown('<div class="group-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🛰️ System Status</div>', unsafe_allow_html=True)
        st.markdown("✅ Communication: 99%")
        st.markdown("✅ Navigation: 98%")
        st.markdown("✅ Surveillance: 97%")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="group-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📊 Congestion Level</div>', unsafe_allow_html=True)
        st.progress(0.65)
        st.markdown('</div>', unsafe_allow_html=True)
with tab2:
    st.markdown('<div class="group-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎯 Advanced Filtering Options</div>', unsafe_allow_html=True)


    with st.expander("📍 Filter by Proximity"):

        saudi_cities_coords = {
            "Riyadh": (24.7136, 46.6753),
            "Jeddah": (21.4858, 39.1925),
            "Dammam": (26.4207, 50.0888),
            "Abha": (18.2164, 42.5053),
            "Makkah": (21.3891, 39.8579),
            "Madinah": (24.5247, 39.5692),
            "Tabuk": (28.3838, 36.5550),
            "Al Baha": (20.0129, 41.4677),
            "Hail": (27.5142, 41.7208),
            "Najran": (17.4917, 44.1320)
        }

        selected_city = st.selectbox("Select a Saudi City", list(saudi_cities_coords.keys()))
        user_lat, user_lon = saudi_cities_coords[selected_city]

        radius_km = st.slider("Max Distance (km)", min_value=50, max_value=1000, value=300, step=50, key="radius")

        def is_nearby(lat, lon):
            return geodesic((user_lat, user_lon), (lat, lon)).km <= radius_km

        df_sa = df_sa[df_sa.apply(lambda row: is_nearby(row["latitude"], row["longitude"]), axis=1)]
        df_sa = df_sa.copy()


    with st.expander("🌐 Filter by Origin Country"):
        countries = sorted(df_sa["origin_country"].dropna().unique())
        selected_country = st.selectbox("Choose Country", ["All"] + countries)
        if selected_country != "All":
            df_sa = df_sa[df_sa["origin_country"] == selected_country]

    with st.expander("🛫 Filter by Altitude (m)"):
        if df_sa["baro_altitude"].dropna().empty:
            alt_min, alt_max = 0, 0  
        else:
            alt_min = int(df_sa["baro_altitude"].dropna().min())
            alt_max = int(df_sa["baro_altitude"].dropna().max())

        if alt_min == alt_max:
            st.info(f"Only one altitude value found: {alt_min} m. Skipping altitude filter.")
        else:
            altitude_range = st.slider(
                "Select Altitude Range",
                min_value=alt_min,
                max_value=alt_max,
                value=(alt_min, alt_max)
            )
            df_sa = df_sa[
                (df_sa["baro_altitude"] >= altitude_range[0]) &
                (df_sa["baro_altitude"] <= altitude_range[1])
            ]

    with st.expander("🌦️ Filter by Weather Description"):
        weather_options = sorted(set([get_weather(row["latitude"], row["longitude"])["description"]
                                    for _, row in df_sa.iterrows()
                                    if get_weather(row["latitude"], row["longitude"]) is not None]))
        selected_weather = st.selectbox("Select Weather", ["All"] + weather_options)
        if selected_weather != "All":
            def match_weather(row):
                info = get_weather(row["latitude"], row["longitude"])
                return info and info["description"] == selected_weather
            df_sa = df_sa[df_sa.apply(match_weather, axis=1)]

    st.markdown('</div>', unsafe_allow_html=True)

    # === BOTTOM: Weather Table ===
    st.markdown("---")
    st.markdown('<div class="group-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🌦️ Aircraft + Weather Overview</div>', unsafe_allow_html=True)
    if df_sa.empty:
        st.info("No aircraft data to display.")
    else:
        weather_data = []
        for _, row in df_sa.iterrows():
            weather = get_weather(row["latitude"], row["longitude"])
            weather_data.append({
                "Callsign": row["callsign"],
                "Latitude": row["latitude"],
                "Longitude": row["longitude"],
                "Altitude (m)": row["baro_altitude"],
                "Speed (m/s)": row["velocity"],
                "Weather": weather["description"] if weather else "N/A",
                "Temp (°C)": weather["temp"] if weather else "N/A",
                "Humidity (%)": weather["humidity"] if weather else "N/A",
                "Wind (m/s)": weather["wind_speed"] if weather else "N/A"
            })
        st.dataframe(pd.DataFrame(weather_data))
    st.markdown('</div>', unsafe_allow_html=True)
