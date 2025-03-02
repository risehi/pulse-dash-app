import os
import logging
from flask import Flask, jsonify
from azure.cosmos import CosmosClient, PartitionKey

app = Flask(__name__)

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG,  # Use DEBUG level for detailed logs
                    format='%(asctime)s - %(levelname)s - %(message)s')
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

# Database and container names (replace with your actual names)
DATABASE_NAME = 'TestDatabase'
CONTAINER_NAME = 'TestContainer'

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

@app.route('/')
def home():
    try:
        # List all databases to test the connection
        databases = [db.id for db in client.list_databases()]
        app.logger.info(f"Databases retrieved: {databases}")
        return jsonify({"message": "Connected to Cosmos DB!", "databases": databases})
    except Exception as e:
        app.logger.error(f"Error fetching databases: {e}")
        return jsonify({"error": "Failed to fetch databases"}), 500

@app.route('/add-item', methods=['POST'])
def add_item():
    try:
        # Add a test item to the container
        item = {"id": "1", "partitionKey": "testPartition", "name": "Sample Item"}
        response = container.upsert_item(item)
        app.logger.info(f"Item added to Cosmos DB: {response}")
        return jsonify({"message": "Item added to Cosmos DB!", "item": item})
    except Exception as e:
        app.logger.error(f"Error adding item: {e}")
        return jsonify({"error": "Failed to add item"}), 500

@app.route('/get-items', methods=['GET'])
def get_items():
    try:
        # Retrieve items from the container
        items = list(container.read_all_items())
        app.logger.info(f"Items retrieved: {items}")
        return jsonify({"items": items})
    except Exception as e:
        app.logger.error(f"Error retrieving items: {e}")
        return jsonify({"error": "Failed to fetch items"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
