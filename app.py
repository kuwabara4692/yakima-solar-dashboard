import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from pysolar.solar import get_altitude, get_azimuth
from timezonefinder import TimezoneFinder
import pytz
from geopy.geocoders import Nominatim
import os

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
        dcc.Tab(label="Seasonal Solar Altitude", children=[
            dcc.Graph(id="seasonal-graph"),
            dcc.Graph(id="sunrise-sunset-graph")
        ]),
        dcc.Tab(label="Yesterday's Solar Altitude", children=[dcc.Graph(id="yesterday-graph")]),
        dcc.Tab(label="Sun Direction & Location", children=[html.Div(id="sun-info")]),
        dcc.Tab(label="Solar Calendar", children=[
            html.H3("Solstices & Equinoxes in 2025", style={"color": "#e67e22"}),
            html.Ul([
                html.Li(f"{label}: {date} 12:00 PM local time", style={"marginBottom": "10px", "fontSize": "18px"})
                for label, date in solar_events.items()
            ], style={"listStyleType": "🌞", "paddingLeft": "20px"})
        ])
    ])
])

# Geolocation helpers
def get_coordinates(location_text):
    geolocator = Nominatim(user_agent="solar-dashboard")
    try:
        location = geolocator.geocode(location_text)
        if location:
            return location.latitude, location.longitude, location.address
        # Fallback: try just the city name
        city_only = location_text.split(",")[0]
        location = geolocator.geocode(city_only)
        if location:
            return location.latitude, location.longitude, location.address
    except:
        return None
    return None

def get_local_timezone(lat, lon):
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    return pytz.timezone(tz_name) if tz_name else pytz.utc

# Callback
@app.callback(
    Output("location-status", "children"),
    Output("seasonal-graph", "figure"),
    Output("sunrise-sunset-graph", "figure"),
    Output("yesterday-graph", "figure"),
    Output("sun-info", "children"),
    Output("calendar-list", "children"),
    Input("submit-location", "n_clicks"),
    State("location-input", "value")
)
def update_dashboard(n_clicks, location_text):
    if not location_text:
        return "Please enter a city and state.", go.Figure(), go.Figure(), go.Figure(), ""

    coords = get_coordinates(location_text)
    if not coords:
        return f"Could not find location: {location_text}", go.Figure(), go.Figure(), go.Figure(), ""

    lat, lon, full_address = coords
    local_tz = get_local_timezone(lat, lon)

    # Seasonal Solar Altitude
    seasons = {
        "Spring": datetime(2025, 3, 20, 12),
        "Summer": datetime(2025, 6, 20, 12),
        "Fall": datetime(2025, 9, 22, 12),
        "Winter": datetime(2025, 12, 21, 12)
    }

    seasonal_fig = go.Figure()
    sunrise_sunset_fig = go.Figure()
    season_colors = {
        "Spring": "#2ecc71",
        "Summer": "#f1c40f",
        "Fall": "#e67e22",
        "Winter": "#3498db"
    }

    for name, dt_local in seasons.items():
        dt_localized = local_tz.localize(dt_local)
        dt_utc = dt_localized.astimezone(pytz.utc)
        altitude = get_altitude(lat, lon, dt_utc)

        # Simulated sunrise/sunset hours
        day_of_year = dt_local.timetuple().tm_yday
        sunrise = 8 - 2 * abs((day_of_year - 172) / 172)
        sunset = 20 + 2 * abs((day_of_year - 172) / 172)

        seasonal_fig.add_trace(go.Bar(
            x=[name],
            y=[altitude],
            name=name,
            marker_color=season_colors[name],
            text=f"{altitude:.2f}°",
            textposition="outside",
            hovertext=f"{name} Solar Noon<br>{dt_localized.strftime('%Y-%m-%d %I:%M %p %Z')}<br>Altitude: {altitude:.2f}°"
        ))

        sunrise_sunset_fig.add_trace(go.Bar(
            x=[name],
            y=[sunrise],
            name=f"{name} Sunrise",
            marker_color="orange",
            text=f"{sunrise:.2f}h",
            textposition="outside"
        ))
        sunrise_sunset_fig.add_trace(go.Bar(
            x=[name],
            y=[sunset],
            name=f"{name} Sunset",
            marker_color="blue",
            text=f"{sunset:.2f}h",
            textposition="outside"
        ))

    seasonal_fig.add_shape(
        type="line",
        x0=-0.5, x1=3.5,
        y0=45, y1=45,
        line=dict(color="gray", dash="dash")
    )
    seasonal_fig.update_layout(
        title=f"Solar Noon Altitude by Season ({full_address})",
        yaxis_title="Altitude (°)",
        template="plotly_white",
        showlegend=False,
        height=600,
        annotations=[
            dict(
                x=1.5,
                y=45,
                xref="x",
                yref="y",
                text="45° Reference Altitude",
                showarrow=False,
                font=dict(color="gray", size=12)
            )
        ]
    )
    sunrise_sunset_fig.update_layout(
        title="Sunrise and Sunset Times by Season",
        yaxis_title="Hour (Local Time)",
        template="plotly_white",
        legend=dict(
            itemsizing="constant",
            traceorder="normal"
        )
    )


    # Yesterday's Solar Altitude
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    times = [local_tz.localize(datetime.combine(yesterday, datetime.min.time()) + timedelta(minutes=15 * i)) for i in range(96)]
    altitudes = [get_altitude(lat, lon, t.astimezone(pytz.utc)) for t in times]
    yesterday_fig = go.Figure()
    yesterday_fig.add_trace(go.Scatter(x=times, y=altitudes, mode="lines", name="Altitude"))
    yesterday_fig.update_layout(title=f"Solar Altitude on {yesterday} ({full_address})", xaxis_title="Time (UTC)", yaxis_title="Altitude (°)", template="plotly_white")

    # Sun Info
    noon = local_tz.localize(datetime.combine(datetime.utcnow().date(), datetime.min.time()) + timedelta(hours=12))
    noon_utc = noon.astimezone(pytz.utc)
    altitude_now = get_altitude(lat, lon, noon_utc)
    azimuth_now = get_azimuth(lat, lon, noon_utc)
    sun_info = html.Div([
        html.H4("Sun Direction & Location", style={"color": "#e67e22"}),
        html.P(f"Location: {full_address}"),
        html.P(f"Latitude: {lat:.4f}, Longitude: {lon:.4f}"),
        html.P(f"Solar Noon Altitude: {altitude_now:.2f}°"),
        html.P(f"Solar Noon Azimuth: {azimuth_now:.2f}°")
    ])
    
    # Solar Calendar with time of day
    calendar_items = []
    for label, date_str in solar_events.items():
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dt_local = local_tz.localize(datetime.combine(dt.date(), datetime.min.time()) + timedelta(hours=12))
        formatted = dt_local.strftime("%B %d, %Y at %I:%M %p %Z")
        calendar_items.append(html.Li(f"{label}: {formatted}", style={"marginBottom": "10px", "fontSize": "18px"}))

    return "", seasonal_fig, sunrise_sunset_fig, yesterday_fig, sun_info, calendar_items

# Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
