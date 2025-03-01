from dash import Dash, dcc, html
import plotly.express as px
import pandas as pd

# Create Flask app explicitly and pass it to Dash
from flask import Flask
server = Flask(__name__)  # This is what Gunicorn will use
app = Dash(__name__, server=server)

# Your static data (replace with dynamic data later if needed)
data = pd.DataFrame({"Time": [1, 2, 3], "Temp": [24.0, 24.1, 24.2], "Humidity": [27.1, 27.0, 27.0]})
fig = px.line(data, x="Time", y=["Temp", "Humidity"], title="Sensor Data")

# Dashboard layout
app.layout = html.Div([html.H1("Sensor Dashboard"), dcc.Graph(figure=fig)])

# No need for this in production; Gunicorn runs the app
# if __name__ == "__main__":
#     app.run_server(debug=True)