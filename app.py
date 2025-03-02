from dash import Dash, dcc, html
import plotly.express as px
import pandas as pd
from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, PartitionKey, exceptions
import os

# Flask app for Azure App Service
server = Flask(__name__)
app = Dash(__name__, server=server)

# Cosmos DB configuration from environment variables
COSMOS_URL = os.getenv("COSMOS_URL", "https://localhost:8081")  # Fallback for local testing
COSMOS_KEY = os.getenv("COSMOS_KEY", "your-local-test-key")    # Replace with a test key if needed
DATABASE_NAME = "sensor_db"
CONTAINER_NAME = "readings"

# Initialize Cosmos DB client
client = CosmosClient(COSMOS_URL, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Initialize container
def init_container():
    try:
        client.create_database_if_not_exists(id=DATABASE_NAME)
        database.create_container_if_not_exists(
            id=CONTAINER_NAME,
            partition_key=PartitionKey(path="/timestamp"),
            offer_throughput=1000
        )
    except exceptions.CosmosHttpResponseError as e:
        print(f"Container init failed: {e}")

# POST endpoint for MicroPython batches
@server.route("/data", methods=["POST"])
def receive_data():
    try:
        batch = request.get_json()
        for reading in batch:
            reading["id"] = str(reading["timestamp"]) if "id" not in reading else reading["id"]
            container.upsert_item(reading)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error saving data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# Fetch data from Cosmos DB
def get_sensor_data():
    try:
        query = "SELECT c.timestamp, c.temperature, c.humidity FROM c ORDER BY c.timestamp"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        df = pd.DataFrame(items)
        if df.empty:
            return pd.DataFrame({"timestamp": [], "temperature": [], "humidity": []})
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        return df
    except exceptions.CosmosHttpResponseError as e:
        print(f"Query failed: {e}")
        return pd.DataFrame({"timestamp": [], "temperature": [], "humidity": []})

# Dashboard layout
app.layout = html.Div([
    html.H1("AM2302 Sensor Dashboard"),
    dcc.Graph(id="sensor-graph"),
    dcc.Interval(id="interval-component", interval=60*1000, n_intervals=0)
])

# Dynamic chart
@app.callback(
    dash.dependencies.Output("sensor-graph", "figure"),
    [dash.dependencies.Input("interval-component", "n_intervals")]
)
def update_graph(n):
    df = get_sensor_data()
    if df.empty:
        return px.line(title="No Data Available")
    fig = px.line(
        df,
        x="timestamp",
        y=["temperature", "humidity"],
        title="Sensor Readings Over Time",
        labels={"timestamp": "Time", "value": "Measurement", "variable": "Metric"}
    )
    return fig

# Initialize on startup
init_container()