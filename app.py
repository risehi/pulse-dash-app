import os
import logging
from flask import Flask, jsonify, request
from azure.cosmos import CosmosClient, PartitionKey
from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd
from dash.dependencies import Input, Output

app = Flask(__name__)
dash_app = Dash(__name__, server=app, url_base_pathname='/dash/')

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
app.logger.setLevel(logging.DEBUG)

# Access environment variables
cosmos_url = os.getenv('COSMOS_URL')
cosmos_key = os.getenv('COSMOS_KEY')

if not cosmos_url or not cosmos_key:
    app.logger.error("COSMOS_URL or COSMOS_KEY environment variables are missing!")
else:
    app.logger.info("Environment variables for Cosmos DB loaded successfully.")

# Initialize Cosmos DB client
try:
    client = CosmosClient(cosmos_url, cosmos_key)
    app.logger.info("Cosmos DB client initialized.")
except Exception as e:
    app.logger.error(f"Error initializing Cosmos DB client: {e}")

# Database and container names
DATABASE_NAME = 'GrowData'
CONTAINER_NAME = 'Readings'

# Ensure the database and container exist
try:
    database = client.create_database_if_not_exists(id=DATABASE_NAME)
    app.logger.info(f"Database '{DATABASE_NAME}' checked/created.")
    container = database.create_container_if_not_exists(
        id=CONTAINER_NAME,
        partition_key=PartitionKey(path="/partitionKey"),
        offer_throughput=400
    )
    app.logger.info(f"Container '{CONTAINER_NAME}' checked/created.")
except Exception as e:
    app.logger.error(f"Error setting up database and container: {e}")

# Flask Routes
@app.route('/')
def home():
    try:
        databases = [db['id'] for db in client.list_databases()]
        app.logger.info(f"Databases retrieved: {databases}")
        return jsonify({"message": "Connected to Cosmos DB!", "databases": databases})
    except Exception as e:
        app.logger.error(f"Error fetching databases: {e}")
        return jsonify({"error": "Failed to fetch databases"}), 500

@app.route('/add-item', methods=['POST'])
def add_item_batch():
    try:
        app.logger.debug(f"Raw request data: {request.data.decode('utf-8')}")
        app.logger.debug(f"Request headers: {request.headers}")
        batch = request.get_json()
        app.logger.debug(f"Parsed batch: {batch}")
        if not isinstance(batch, list):
            app.logger.error("Invalid input data: Expected a list of items.")
            return jsonify({"error": "Input must be a list of items."}), 400
        for item in batch:
            if not all(key in item for key in ["id", "partitionKey", "name"]):
                app.logger.error("Invalid item format. 'id', 'partitionKey', and 'name' are required.")
                return jsonify({"error": "Each item must have 'id', 'partitionKey', and 'name'"}), 400
            container.upsert_item(item)
            app.logger.info(f"Item added: {item}")
        return jsonify({"message": f"Batch of {len(batch)} items added to Cosmos DB!"}), 200
    except Exception as e:
        app.logger.error(f"Error adding batch: {e}")
        return jsonify({"error": "Failed to add batch"}), 500

@app.route('/get-items', methods=['GET'])
def get_items():
    try:
        items = list(container.read_all_items())
        app.logger.info(f"Items retrieved: {items}")
        return jsonify({"items": items})
    except Exception as e:
        app.logger.error(f"Error retrieving items: {e}")
        return jsonify({"error": "Failed to fetch items"}), 500

# Dash Data Preparation
def get_time_series_data():
    try:
        # Fetch items from Cosmos DB
        items = list(container.read_all_items())
        app.logger.info(f"Fetched {len(items)} items from Cosmos DB")

        # Convert to DataFrame
        df = pd.DataFrame(items)

        # Validate raw data integrity
        if df.empty:
            app.logger.warning("Fetched data is empty!")
            return pd.DataFrame()

        app.logger.debug(f"Raw DataFrame structure: {df.columns.tolist()}")

        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        app.logger.debug("Converted 'timestamp' to datetime.")

        # Flatten nested 'sensorGroups'
        sensors_df = pd.json_normalize(df['sensorGroups'])
        df = pd.concat([df.drop(['sensorGroups'], axis=1), sensors_df], axis=1)
        app.logger.debug(f"Flattened 'sensorGroups' into columns: {sensors_df.columns.tolist()}")

        # Drop unnecessary metadata columns
        df = df.drop(columns=['_rid', '_self', '_etag', '_attachments', '_ts'], errors='ignore')
        app.logger.debug("Dropped unnecessary metadata columns.")

        return df
    except Exception as e:
        app.logger.error(f"Error preparing time series data: {e}")
        return pd.DataFrame()


# Dash Layout
dash_app.layout = html.Div([
    html.H1("Sensor Time Series Dashboard"),
    dcc.Graph(id='temperature-graph'),
    dcc.Graph(id='humidity-graph'),
    dcc.Graph(id='lux-graph'),
    dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0)  # Update every 60s
])

@dash_app.callback(
    [Output('temperature-graph', 'figure'),
     Output('humidity-graph', 'figure'),
     Output('lux-graph', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_graphs(n_intervals):
    app.logger.info(f"Interval triggered (count: {n_intervals})")
    
    # Fetch data
    df = get_time_series_data()
    if df.empty:
        app.logger.warning("DataFrame is empty, no data to graph.")
        return {}, {}, {}

    # Convert columns to lists
    timestamps = df['timestamp'].tolist()  # Convert timestamp to list
    temp_data_test_unit = df['test_unit.temperature'].tolist()  # Convert temperature column for test_unit
    temp_data_space_nursery = df['space_nursery.temperature'].tolist()  # Convert temperature column for space_nursery
    humid_data_test_unit = df['test_unit.humidity'].tolist()  # Convert humidity column for test_unit
    humid_data_space_nursery = df['space_nursery.humidity'].tolist()  # Convert humidity column for space_nursery
    lux_data = df['space_nursery.lux'].tolist()  # Convert lux column

    # Create figures using the explicitly converted lists
    temp_fig = px.line(
        x=timestamps,
        y=[temp_data_test_unit, temp_data_space_nursery],  # List of temperature data
        title='Temperature Over Time',
        labels={'value': 'Temperature (°C)'}
    )
    humid_fig = px.line(
        x=timestamps,
        y=[humid_data_test_unit, humid_data_space_nursery],  # List of humidity data
        title='Humidity Over Time',
        labels={'value': 'Humidity (%)'}
    )
    lux_fig = px.line(
        x=timestamps,
        y=lux_data,  # Lux data as list
        title='Lux Over Time',
        labels={'value': 'Lux'}
    )

    return temp_fig, humid_fig, lux_fig


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)