import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from pysolar.solar import get_altitude, get_azimuth
import pytz
import io
import base64
import os

# Supported cities with coordinates
cities = {
    "Yakima, WA": (46.6021, -120.5059),
    "New York, NY": (40.7128, -74.0060),
    "Los Angeles, CA": (34.0522, -118.2437),
    "Chicago, IL": (41.8781, -87.6298),
    "Miami, FL": (25.7617, -80.1918)
}

# Solstices and Equinoxes (2025)
solar_events = {
    "Spring Equinox": "2025-03-20",
    "Summer Solstice": "2025-06-20",
    "Fall Equinox": "2025-09-22",
    "Winter Solstice": "2025-12-21"
}

# Generate date range
dates = pd.date_range(start="2025-01-01", end="2025-12-31", freq="D")

# Dash app setup
app = dash.Dash(__name__)
app.title = "Yakima Solar Dashboard"

app.layout = html.Div(style={"backgroundColor": "#fffbe6", "fontFamily": "Arial"}, children=[
    html.H1("☀️ Solar Dashboard", style={"textAlign": "center", "color": "#e67e22"}),

    html.Div([
        html.Label("Select Location:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="location-dropdown",
            options=[{"label": city, "value": city} for city in cities],
            value="Yakima, WA",
            style={"width": "300px"}
        )
    ], style={"padding": "10px"}),

    dcc.Tabs([
        dcc.Tab(label="Solar Azimuth & Day Length", children=[
            html.H3("Solar Azimuth and Day Length", style={"color": "#e67e22"}),
            dcc.Graph(id="angles-graph"),
            html.Button("Download Solar Data", id="download-button"),
            dcc.Download(id="download-data")
        ]),
        dcc.Tab(label="Solar Altitude", children=[
            html.H3("Solar Noon Altitude Over the Year", style={"color": "#e67e22"}),
            dcc.Graph(id="altitude-graph")
        ]),
        dcc.Tab(label="Sunrise/Sunset", children=[
            html.H3("Sunrise and Sunset Times Across 2025", style={"color": "#e67e22"}),
            dcc.Graph(id="sunrise-graph")
        ]),
        dcc.Tab(label="Temperature Overlay", children=[
            html.H3("Upload Temperature Data (CSV)", style={"color": "#e67e22"}),
            dcc.Upload(
                id="upload-data",
                children=html.Div(["📁 Drag and drop or click to upload"]),
                style={
                    "width": "100%",
                    "height": "60px",
                    "lineHeight": "60px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center",
                    "margin": "10px"
                },
                multiple=False
            ),
            html.Div(id="temperature-graph")
        ])
    ])
])

def generate_solar_data(lat, lon):
    sunrise = [8 - 2 * abs((date.dayofyear - 172) / 172) for date in dates]
    sunset = [20 + 2 * abs((date.dayofyear - 172) / 172) for date in dates]
    data = []
    for i, date in enumerate(dates):
        dt = pytz.utc.localize(datetime.combine(date, datetime.min.time()) + timedelta(hours=20))
        altitude = get_altitude(lat, lon, dt)
        azimuth = get_azimuth(lat, lon, dt)
        day_length = sunset[i] - sunrise[i]
        data.append({
            "Date": date,
            "Altitude": altitude,
            "Azimuth": azimuth,
            "Day Length": day_length,
            "Sunrise": sunrise[i],
            "Sunset": sunset[i]
        })
    return pd.DataFrame(data)

def add_annotations(fig):
    for label, date_str in solar_events.items():
        fig.add_vline(
            x=pd.to_datetime(date_str),
            line=dict(color="gray", dash="dot"),
            annotation_text=label,
            annotation_position="top left"
        )
    return fig

@app.callback(
    Output("angles-graph", "figure"),
    Output("altitude-graph", "figure"),
    Output("sunrise-graph", "figure"),
    Input("location-dropdown", "value")
)
def update_graphs(location):
    lat, lon = cities[location]
    df = generate_solar_data(lat, lon)

    fig_angles = go.Figure()
    fig_angles.add_trace(go.Scatter(x=df["Date"], y=df["Azimuth"], mode="lines", name="Azimuth", line=dict(color="green")))
    fig_angles.add_trace(go.Scatter(x=df["Date"], y=df["Day Length"], mode="lines", name="Day Length", line=dict(color="purple")))
    fig_angles.update_layout(title=f"Solar Azimuth & Day Length ({location})", xaxis_title="Date", yaxis_title="Degrees / Hours", template="plotly_white")
    fig_angles = add_annotations(fig_angles)

    fig_altitude = go.Figure()
    fig_altitude.add_trace(go.Scatter(x=df["Date"], y=df["Altitude"], mode="lines", name="Solar Noon Altitude"))
    fig_altitude.update_layout(title=f"Solar Noon Altitude ({location})", xaxis_title="Date", yaxis_title="Altitude (°)", template="plotly_white")
    fig_altitude = add_annotations(fig_altitude)

    fig_sun = go.Figure()
    fig_sun.add_trace(go.Scatter(x=df["Date"], y=df["Sunrise"], mode="lines", name="Sunrise", line=dict(color="orange")))
    fig_sun.add_trace(go.Scatter(x=df["Date"], y=df["Sunset"], mode="lines", name="Sunset", line=dict(color="blue")))
    fig_sun.update_layout(title=f"Sunrise & Sunset Times ({location})", xaxis_title="Date", yaxis_title="Hour (UTC)", template="plotly_white")
    fig_sun = add_annotations(fig_sun)

    return fig_angles, fig_altitude, fig_sun

@app.callback(
    Output("download-data", "data"),
    Input("download-button", "n_clicks"),
    State("location-dropdown", "value"),
    prevent_initial_call=True
)
def download_csv(n_clicks, location):
    lat, lon = cities[location]
    df = generate_solar_data(lat, lon)
    return dcc.send_data_frame(df.to_csv, f"{location.replace(', ', '_')}_solar_data_2025.csv")

@app.callback(
    Output("temperature-graph", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename")
)
def update_temperature_graph(contents, filename):
    if contents is None:
        return html.P("Upload a CSV file with 'Date' and 'Temperature' columns.")

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df_temp = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        df_temp["Date"] = pd.to_datetime(df_temp["Date"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_temp["Date"], y=df_temp["Temperature"], mode="lines", name="Temperature", line=dict(color="red")))
        fig.update_layout(title=f"Temperature Trends from {filename}", xaxis_title="Date", yaxis_title="Temperature (°C)", template="plotly_white")
        return dcc.Graph(figure=fig)
    except Exception as e:
        return html.P(f"Error processing file: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
