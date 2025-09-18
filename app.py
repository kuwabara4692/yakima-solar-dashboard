import os
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from pysolar.solar import get_altitude, get_azimuth
import pytz
import geopy
from geopy.geocoders import Nominatim

# Initialize app
app = dash.Dash(__name__)
app.title = "Solar Dashboard"

# Solar calendar events
solar_events = {
    "Spring Equinox": "2025-03-20",
    "Summer Solstice": "2025-06-20",
    "Fall Equinox": "2025-09-22",
    "Winter Solstice": "2025-12-21"
}

# Layout
app.layout = html.Div(style={"backgroundColor": "#fdf6e3", "fontFamily": "Segoe UI"}, children=[
    html.H1("🌞 Solar Dashboard", style={"textAlign": "center", "color": "#e67e22"}),

    html.Div([
        html.Label("Enter City and State:", style={"fontWeight": "bold"}),
        dcc.Input(id="location-input", type="text", placeholder="e.g. Yakima, WA", style={"width": "300px"}),
        html.Button("Submit", id="submit-location", n_clicks=0)
    ], style={"padding": "10px"}),

    html.Div(id="location-status", style={"color": "#e74c3c", "marginBottom": "10px"}),

    dcc.Tabs([
        dcc.Tab(label="Seasonal Solar Altitude", children=[dcc.Graph(id="seasonal-graph")]),
        dcc.Tab(label="Yesterday's Solar Altitude", children=[dcc.Graph(id="yesterday-graph")]),
        dcc.Tab(label="Sun Direction & Location", children=[html.Div(id="sun-info")]),
        dcc.Tab(label="Solar Calendar", children=[
            html.H3("Solstices & Equinoxes in 2025", style={"color": "#e67e22"}),
            html.Ul([
                html.Li(f"{label}: {date}", style={"marginBottom": "10px", "fontSize": "18px"})
                for label, date in solar_events.items()
            ], style={"listStyleType": "🌞", "paddingLeft": "20px"})
        ])
    ])
])

# Helper: Geocode city/state
def get_coordinates(location_text):
    geolocator = Nominatim(user_agent="solar-dashboard")
    try:
        location = geolocator.geocode(location_text)
        if location:
            return location.latitude, location.longitude
    except:
        return None
    return None

# Callback: Update all graphs and info
@app.callback(
    Output("location-status", "children"),
    Output("seasonal-graph", "figure"),
    Output("yesterday-graph", "figure"),
    Output("sun-info", "children"),
    Input("submit-location", "n_clicks"),
    State("location-input", "value")
)
def update_dashboard(n_clicks, location_text):
    if not location_text:
        return "Please enter a city and state.", go.Figure(), go.Figure(), ""

    coords = get_coordinates(location_text)
    if not coords:
        return f"Could not find location: {location_text}", go.Figure(), go.Figure(), ""

    lat, lon = coords
    tz = pytz.utc

    # Seasonal Solar Altitude
    seasons = {
        "Spring": datetime(2025, 3, 20, 12),
        "Summer": datetime(2025, 6, 20, 12),
        "Fall": datetime(2025, 9, 22, 12),
        "Winter": datetime(2025, 12, 21, 12)
    }
    seasonal_fig = go.Figure()
    for name, dt in seasons.items():
        dt_utc = tz.localize(dt)
        altitude = get_altitude(lat, lon, dt_utc)
        seasonal_fig.add_trace(go.Bar(x=[name], y=[altitude], name=name))
    seasonal_fig.update_layout(title="Solar Noon Altitude by Season", yaxis_title="Altitude (°)", template="plotly_white")

    # Yesterday's Solar Altitude
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    times = [datetime.combine(yesterday, datetime.min.time()) + timedelta(minutes=15 * i) for i in range(96)]
    altitudes = [get_altitude(lat, lon, tz.localize(t)) for t in times]
    yesterday_fig = go.Figure()
    yesterday_fig.add_trace(go.Scatter(x=times, y=altitudes, mode="lines", name="Altitude"))
    yesterday_fig.update_layout(title=f"Solar Altitude on {yesterday}", xaxis_title="Time (UTC)", yaxis_title="Altitude (°)", template="plotly_white")

    # Sun Info
    noon = tz.localize(datetime.combine(datetime.utcnow().date(), datetime.min.time()) + timedelta(hours=12))
    altitude_now = get_altitude(lat, lon, noon)
    azimuth_now = get_azimuth(lat, lon, noon)
    sun_info = html.Div([
        html.H4("Sun Direction & Location", style={"color": "#e67e22"}),
        html.P(f"Location: {location_text}"),
        html.P(f"Latitude: {lat:.4f}, Longitude: {lon:.4f}"),
        html.P(f"Solar Noon Altitude: {altitude_now:.2f}°"),
        html.P(f"Solar Noon Azimuth: {azimuth_now:.2f}°")
    ])

    return "", seasonal_fig, yesterday_fig, sun_info

# Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
