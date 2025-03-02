import logging
from flask import Flask

app = Flask(__name__)

# Set up basic logging
logging.basicConfig(level=logging.DEBUG,  # Change to INFO or ERROR as needed
                    format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/')
def home():
    app.logger.info("Home route was accessed")
    return "Hello, Azure with logging!"

@app.route('/error')
def error():
    app.logger.error("This is an intentional error for testing")
    return "Error route accessed", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
