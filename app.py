from dash import Dash, dcc, html
import plotly.express as px
import pandas as pd

app = Dash(__name__)
data = pd.DataFrame({"Time": [1, 2, 3], "Temp": [24.0, 24.1, 24.2], "Humidity": [27.1, 27.0, 27.0]})
fig = px.line(data, x="Time", y=["Temp", "Humidity"], title="Sensor Data")

app.layout = html.Div([html.H1("Sensor Dashboard"), dcc.Graph(figure=fig)])
if __name__ == "__main__":
    app.run_server(debug=True)