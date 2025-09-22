import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pysolar.solar import get_altitude, get_azimuth
from timezonefinder import TimezoneFinder
import pytz
from geopy.geocoders import Nominatim
import os

app = dash.Dash(__name__)
app.title = "Solar Dashboard"

solar_events = {
    "Spring Equinox": "2025-03-20",
    "Summer Solstice": "2025-06-20",
    "Fall Equinox": "2025-09-22",
    "Winter Solstice": "2025-12-21"
}

# Geolocation helpers
# TODO: Integrate autocomplete with Google Places or Mapbox
def get_coordinates(location_text):
    geolocator = Nominatim(user_agent="solar-dashboard-app")
    location_text = location_text.strip().title()

    try:
        # Try full input
        location = geolocator.geocode(location_text, exactly_one=True, timeout=10)
        if location:
            print(f"Found location: {location.address}")
            return location.latitude, location.longitude, location.address

        # Fallback: just the city name
        city_only = location_text.split(",")[0]
        location = geolocator.geocode(city_only, exactly_one=True, timeout=10)
        if location:
            print(f"Fallback location: {location.address}")
            return location.latitude, location.longitude, location.address

        # Fallback: guess country
        location = geolocator.geocode(f"{city_only}, United States", exactly_one=True, timeout=10)
        if location:
            print(f"Guessed country fallback: {location.address}")
            return location.latitude, location.longitude, location.address

    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

    return None


def get_local_timezone(lat, lon):
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    return pytz.timezone(tz_name) if tz_name else pytz.utc

def find_sunrise_sunset(lat, lon, date, tz):
    sunrise = None
    sunset = None
    for minute in range(0, 1440):
        dt_local = tz.localize(datetime.combine(date, datetime.min.time()) + timedelta(minutes=minute))
        dt_utc = dt_local.astimezone(pytz.utc)
        altitude = get_altitude(lat, lon, dt_utc)
        if altitude > 0 and sunrise is None:
            sunrise = dt_local
        if altitude < 0 and sunrise and sunset is None:
            sunset = dt_local
    return sunrise, sunset

# Layout
app.layout = html.Div(style={"backgroundColor": "#fdf6e3", "fontFamily": "Segoe UI"}, children=[
    html.Div([
        html.H1("🌞Solar Dashboard🌞", style={
            "textAlign": "center",
            "color": "#e67e22",
            "fontSize": "64px",
            "marginBottom": "0"
        })
    ]),
    html.Div([
        html.Label("Enter City and Country:", style={"fontWeight": "bold"}),
        dcc.Input(id="location-input", type="text", placeholder="e.g. Tokyo, Japan or Nairobi, Kenya", style={"width": "300px"}),
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
            html.Ul(id="calendar-list", style={"listStyleType": "🌞", "paddingLeft": "20px"})
        ]),
        dcc.Tab(label="GIFs", children=[
            html.H3("NASA Solar Observation GIFs", style={"color": "#e67e22", "marginTop": "20px"}),
            html.Div([
                html.P("SOHO C2 Coronagraph", style={"fontWeight": "bold"}),
                html.Img(src="https://soho.nascom.nasa.gov/data/LATEST/current_c2.gif", style={"width": "100%", "maxWidth": "600px"}),
                html.P("SOHO C3 Coronagraph", style={"fontWeight": "bold", "marginTop": "20px"}),
                html.Img(src="https://soho.nascom.nasa.gov/data/LATEST/current_c3.gif", style={"width": "100%", "maxWidth": "600px"}),
                html.P("SOHO EIT 284 Å", style={"fontWeight": "bold", "marginTop": "20px"}),
                html.Img(src="https://soho.nascom.nasa.gov/data/LATEST/current_eit_284small.gif", style={"width": "100%", "maxWidth": "600px"}),
                html.P([
                    html.A("NASA SOHO – Solar and Heliospheric Observatory", href="https://soho.nascom.nasa.gov/home.html", target="_blank", style={"color": "#2980b9", "fontWeight": "bold", "textDecoration": "none"})
                ], style={"marginTop": "30px", "fontSize": "16px"})
            ], style={"textAlign": "center", "padding": "20px"})
        ])
    ])
])

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
        return "Please enter a city and country.", go.Figure(), go.Figure(), go.Figure(), "", []

    coords = get_coordinates(location_text)
    if not coords:
        return f"Could not find location: {location_text}", go.Figure(), go.Figure(), go.Figure(), "", []

    lat, lon, full_address = coords
    local_tz = get_local_timezone(lat, lon)

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

        sunrise_dt, sunset_dt = find_sunrise_sunset(lat, lon, dt_local.date(), local_tz)
        sunrise_hour = sunrise_dt.strftime("%H:%M") if sunrise_dt else "N/A"
        sunset_hour = sunset_dt.strftime("%H:%M") if sunset_dt else "N/A"

        seasonal_fig.add_trace(go.Bar(
            x=[name],
            y=[altitude],
            name=name,
            marker_color=season_colors[name],
            text=f"{altitude:.2f}°",
            textposition="outside"
        ))

        sunrise_sunset_fig.add_trace(go.Bar(
            x=[name],
            y=[sunrise_dt.hour + sunrise_dt.minute / 60 if sunrise_dt else 0],
            name="Sunrise",
            marker_color="orange",
            text=sunrise_hour,
            textposition="outside"
        ))
        sunrise_sunset_fig.add_trace(go.Bar(
            x=[name],
            y=[sunset_dt.hour + sunset_dt.minute / 60 if sunset_dt else 0],
            name="Sunset",
            marker_color="blue",
            text=sunset_hour,
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
        legend=dict(itemsizing="constant", traceorder="normal")
    )

    # Yesterday's Solar Altitude
    yesterday = datetime.now(local_tz).date() - timedelta(days=1)
    times = [local_tz.localize(datetime.combine(yesterday, datetime.min.time()) + timedelta(minutes=15 * i)) for i in range(96)]
    altitudes = [get_altitude(lat, lon, t.astimezone(pytz.utc)) for t in times]
    yesterday_fig = go.Figure()
    yesterday_fig.add_trace(go.Scatter(x=times, y=altitudes, mode="lines", name="Altitude"))
    yesterday_fig.update_layout(
        title=f"Solar Altitude on {yesterday.strftime('%B %d, %Y')} ({full_address})",
        xaxis_title="Time (Local)",
        yaxis_title="Altitude (°)",
        template="plotly_white"
    )

    # Sun Info
    noon = local_tz.localize(datetime.combine(datetime.now(local_tz).date(), datetime.min.time()) + timedelta(hours=12))
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
