import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import folium
from opencage.geocoder import OpenCageGeocode
from geopy.distance import geodesic
import requests
import math
import numpy as np
from sklearn.ensemble import RandomForestRegressor

# 🌐 App config
st.set_page_config(page_title="SkySense AI", layout="centered")
st.title("🌍 SkySense AI – Fire Smoke & AQI Risk Radar")

# 📍 User input for location
place = st.text_input("Enter your city/town/village:", "Chennai")
geocoder = OpenCageGeocode(st.secrets["92ea3570441b4d16a64e2427f53fe876"])
results = geocoder.geocode(place)

if not results:
    st.error("❌ Location not found. Please try again.")
    st.stop()

location = results[0]
user_coords = (location['geometry']['lat'], location['geometry']['lng'])
st.success(f"📍 Found location: {location['formatted']}")

# 🌬️ Get wind and weather data via OpenWeatherMap
weather_api_key = "18406bb4885186a7985d590bb3109abd"  # Replace with your real key
weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={user_coords[0]}&lon={user_coords[1]}&appid={weather_api_key}&units=metric"

try:
    weather = requests.get(weather_url).json()
    wind = weather.get('wind', {})
    wind_speed = wind.get('speed', 0)
    wind_deg = wind.get('deg', 0)
    temp = weather['main']['temp']
    st.markdown(f"**🌬️ Wind:** {wind_speed} m/s @ {wind_deg}°")
    st.markdown(f"**🌡️ Temperature:** {temp:.1f} °C")
except Exception as e:
    st.error(f"Failed to get weather data: {e}")
    st.stop()

# 🏠 Get pollution data (PM2.5 + AQI)
pollution_url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={user_coords[0]}&lon={user_coords[1]}&appid={weather_api_key}"
try:
    pollution = requests.get(pollution_url).json()
    pm25 = pollution['list'][0]['components']['pm2_5']
    aqi = pollution['list'][0]['main']['aqi']

    aqi_level = {
        1: "Good ✅",
        2: "Fair 🌤️",
        3: "Moderate ⚠️",
        4: "Poor 😷",
        5: "Very Poor 🚨"
    }

    st.markdown(f"### 🏠 Local Air Quality Index: **{aqi_level[aqi]}**")
    st.markdown(f"**PM2.5 concentration:** `{pm25:.1f}` μg/m³")
except Exception as e:
    st.warning(f"Could not fetch pollution data: {e}")

# 🔥 Load FIRMS data (Global, 7d)
firms_url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_7d.csv"

try:
    fire_df = pd.read_csv(firms_url)
    fire_df.columns = fire_df.columns.str.lower()
except Exception as e:
    st.error(f"❌ Failed to load FIRMS data: {e}")
    st.stop()

# 📏 Filter fires within 100 km
fire_df['distance_km'] = fire_df.apply(
    lambda row: geodesic((row['latitude'], row['longitude']), user_coords).km,
    axis=1
)
nearby_fires = fire_df[fire_df['distance_km'] <= 100].copy()
st.markdown(f"**Nearby fires detected:** {len(nearby_fires)}")

# 🧰 Wind alignment
def calculate_bearing(p1, p2):
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def is_wind_towards(bearing, wind_deg, tolerance=45):
    diff = abs((bearing - wind_deg + 180) % 360 - 180)
    return diff <= tolerance

nearby_fires['bearing'] = nearby_fires.apply(
    lambda row: calculate_bearing((row['latitude'], row['longitude']), user_coords), axis=1
)
nearby_fires['wind_toward_user'] = nearby_fires['bearing'].apply(
    lambda b: is_wind_towards(b, wind_deg)
)

impact_fires = nearby_fires[nearby_fires['wind_toward_user']]

# 🧠 Estimate PM2.5 with ML model
if len(impact_fires) > 0:
    X = impact_fires[['frp', 'distance_km']].copy()
    X['wind_speed'] = wind_speed

    X_train = np.array([[5, 50, 3], [10, 30, 5], [20, 10, 7], [3, 90, 2], [15, 20, 4]])
    y_train = np.array([60, 100, 180, 40, 150])

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X)
    impact_fires['pm25_estimate'] = predictions

    avg_pm25 = predictions.mean()
    st.markdown(f"### 📊 Estimated Smoke PM2.5: `{avg_pm25:.1f}` μg/m³")

    if avg_pm25 < 50:
        st.success("✅ Fire smoke impact is minimal.")
    elif avg_pm25 < 100:
        st.warning("⚠️ Moderate smoke impact detected.")
    else:
        st.error("🚨 High fire smoke risk! Stay indoors.")
else:
    st.info("✅ No fire smoke reaching your location (based on wind).")

# 🌍 Fire map with legend
# ✅ Create the map before rendering it
m = folium.Map(location=user_coords, zoom_start=7)

# ✅ Optional: mark your location
folium.Marker(
    user_coords,
    tooltip="📍 You",
    icon=folium.Icon(color="blue")
).add_to(m)

# ✅ Add a simple HTML legend directly
legend_html = """
<div style='
    position: fixed;
    bottom: 40px;
    left: 40px;
    width: 180px;
    height: 90px;
    background-color: white;
    border:2px solid grey;
    z-index:9999;
    font-size:14px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
    padding: 10px;'>
<b>🔥 Legend</b><br>
<span style='color:red;'>●</span> Fire blowing toward you<br>
<span style='color:gray;'>●</span> Fire not affecting you
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# ✅ Now render the map safely
folium_map_html = m._repr_html_()
components.html(folium_map_html, height=600)

