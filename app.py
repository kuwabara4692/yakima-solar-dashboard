import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from pysolar.solar import get_altitude
import pytz
import base64
import io
import os

# Coordinates for Yakima
latitude = 46.6021
longitude = -120.5059

# Generate solar noon altitudes across the year
dates = pd.date_range(start="2025-01-01", end="2025-12-31", freq="D")
altitudes = [
    get_altitude(latitude, longitude, pytz.utc.localize(datetime.combine(date, datetime.min.time()) + timedelta(hours=20)))
    for date in dates
]
df_altitude = pd.DataFrame({"Date": dates, "Solar Noon Altitude": altitudes})

# Simulate sunrise/sunset times (simplified)
sunrise = [8 - 2 * abs((date.dayofyear - 172) / 172) for date in dates]
sunset = [20 + 2 * abs((date.dayofyear - 172) / 172) for date in dates]
df_sun = pd.DataFrame({"Date": dates, "Sunrise": sunrise, "Sunset": sunset})

# Path to your GIF
gif_path = r"C:\Users\cmkoh\yakima_sunpath.gif"
gif_encoded = ""
if os.path.exists(gif_path):
    with open(gif_path, "rb") as f:
        gif_encoded = base64.b64encode(f.read()).decode()

# Dash app setup
app = dash.Dash(__name__)
app.title = "Yakima Solar Dashboard"

app.layout = html.Div(style={"backgroundColor": "#fffbe6", "fontFamily": "Arial"}, children=[
    html.H1("☀️ Yakima Solar Dashboard", style={"textAlign": "center", "color": "#e67e22"}),

    dcc.Tabs([
        dcc.Tab(label="Sun Path Animation", children=[
            html.H3("Animated Sun Path Over Yakima", style={"color": "#e67e22"}),
            html.Img(src=f"data:image/gif;base64,{gif_encoded}", style={"width": "80%", "margin": "auto"}) if gif_encoded else html.P("GIF not found.")
        ]),
        dcc.Tab(label="Solar Altitude", children=[
            html.H3("Solar Noon Altitude Over the Year", style={"color": "#e67e22"}),
            dcc.Graph(
                figure=go.Figure().add_trace(
                    go.Scatter(x=df_altitude["Date"], y=df_altitude["Solar Noon Altitude"], mode="lines", name="Solar Noon")
                ).update_layout(
                    title="Solar Noon Altitude (2025)",
                    xaxis_title="Date",
                    yaxis_title="Altitude (°)",
                    template="plotly_white"
                )
            )
        ]),
        dcc.Tab(label="Sunrise/Sunset", children=[
            html.H3("Sunrise and Sunset Times Across 2025", style={"color": "#e67e22"}),
            dcc.Graph(
                figure=go.Figure([
                    go.Scatter(x=df_sun["Date"], y=df_sun["Sunrise"], mode="lines", name="Sunrise", line=dict(color="orange")),
                    go.Scatter(x=df_sun["Date"], y=df_sun["Sunset"], mode="lines", name="Sunset", line=dict(color="blue"))
                ]).update_layout(
                    title="Sunrise & Sunset Times",
                    xaxis_title="Date",
                    yaxis_title="Hour (UTC)",
                    template="plotly_white"
                )
            )
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
    app.run(debug=True)
