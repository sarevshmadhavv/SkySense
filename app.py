import streamlit as st
import streamlit.components.v1 as components
import folium

# 🔹 User input
place = st.text_input("Enter a place (e.g., Chennai)", "Chennai")

# Hardcoded fallback if geocoder fails (for demo)
if place.lower() == "chennai":
    user_coords = (13.0827, 80.2707)
else:
    user_coords = (20.5937, 78.9629)  # India center

# 🔹 Create map
m = folium.Map(location=user_coords, zoom_start=7)
folium.Marker(user_coords, tooltip="📍 You").add_to(m)

# 🔹 Add demo fires
folium.CircleMarker([13.5, 80.3], radius=5, color="red", fill=True, popup="🔥 Toward you").add_to(m)
folium.CircleMarker([13.9, 80.7], radius=5, color="gray", fill=True, popup="🔥 Not toward").add_to(m)

# 🔹 Add working legend (no macro)
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

# 🔹 Render map
folium_map_html = m._repr_html_()
components.html(folium_map_html, height=600)
