import pandas as pd
import plotly.graph_objects as go
from math import radians, sin, cos, sqrt, atan2
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import networkx as nx

# Función para calcular la distancia haversine entre dos coordenadas geográficas
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radio de la Tierra en kilómetros

    # Convierte coordenadas de grados a radianes
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Calcula diferencias de latitud y longitud
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Calcula la distancia haversine
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Distancia en kilómetros
    distance = R * c
    return distance

# Solicitar la ruta del archivo CSV desde la terminal
csv_file_path = input("Por favor, ingresa la ruta del archivo CSV: ")

# Leer los datos del archivo CSV
df = pd.read_csv(csv_file_path)

# Crear un grafo dirigido con NetworkX
G = nx.DiGraph()

# Agregar aristas ponderadas al grafo
for index, row in df.iterrows():
    source_code = row['Source Airport Code']
    dest_code = row['Destination Airport Code']
    distance = haversine_distance(row['Source Airport Latitude'], row['Source Airport Longitude'],
                                   row['Destination Airport Latitude'], row['Destination Airport Longitude'])
    G.add_edge(source_code, dest_code, weight=distance)

# Obtener los códigos de los aeropuertos
airport_codes = df['Source Airport Code'].unique()

# Inicializar la aplicación Dash
app = dash.Dash(__name__)

# Crear listas de opciones para la lista desplegable
options = [{'label': code, 'value': code} for code in airport_codes]

# Definir el diseño de la interfaz gráfica
app.layout = html.Div([
    dcc.Graph(
        id='flight-routes-map',
        figure=go.Figure()
    ),
    dcc.Dropdown(
        id='airport-code-dropdown',
        options=options,
        value=airport_codes[0]
    ),
    html.Div([
        dcc.RadioItems(
            id='info-radio',
            options=[
                {'label': 'Aeropuertos', 'value': 'airports'},
                {'label': 'Aeropuertos con caminos mínimos', 'value': 'top_paths'},
                {'label': 'Todas las conexiones', 'value': 'all_connections'},
            ],
            value='airports',
            labelStyle={'display': 'block'}
        ),
        html.Div(id='info-output')
    ]),
    html.Div([
        html.Label('Aeropuerto de origen:'),
        dcc.Dropdown(
            id='origin-airport-dropdown',
            options=options,
            value=airport_codes[0]
        ),
        html.Label('Aeropuerto de destino:'),
        dcc.Dropdown(
            id='destination-airport-dropdown',
            options=options,
            value=airport_codes[1]
        ),
        html.Button('Buscar camino mínimo', id='submit-val', n_clicks=0),
        html.Div(id='container-button-basic')
    ])
])

# Función para obtener los 10 aeropuertos con los caminos mínimos más largos desde un vértice dado
def get_top_10_longest_paths(source_code):
    paths = nx.single_source_dijkstra_path_length(G, source=source_code)
    sorted_paths = sorted(paths.items(), key=lambda x: x[1], reverse=True)
    top_10_longest_paths = sorted_paths[:10]
    return top_10_longest_paths

# Callback para actualizar el mapa y mostrar la información correspondiente
@app.callback(
    [Output('flight-routes-map', 'figure'),
     Output('info-output', 'children')],
    [Input('info-radio', 'value'),
     Input('airport-code-dropdown', 'value'),
     Input('submit-val', 'n_clicks')],
    [dash.dependencies.State('origin-airport-dropdown', 'value'),
     dash.dependencies.State('destination-airport-dropdown', 'value')]
)
def update_info(info_type, selected_airport_code, n_clicks, origin_airport, destination_airport):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'submit-val' in changed_id:
        shortest_path = nx.shortest_path(G, source=origin_airport, target=destination_airport)
        info_output = html.Div([
            html.H3(f'Camino mínimo entre {origin_airport} y {destination_airport}:'),
            html.P(f'Recorrido: {" -> ".join(shortest_path)}')
        ])

        # Crear la figura de Plotly con Mapbox para el camino mínimo desde el aeropuerto de origen al de destino
        lats = []
        lons = []
        for i in range(len(shortest_path) - 1):
            source_airport = df[df['Source Airport Code'] == shortest_path[i]].iloc[0]
            dest_airport = df[df['Source Airport Code'] == shortest_path[i + 1]].iloc[0]

            lats += [source_airport['Source Airport Latitude'], dest_airport['Source Airport Latitude'], None]
            lons += [source_airport['Source Airport Longitude'], dest_airport['Source Airport Longitude'], None]

        flight_routes_map = go.Figure(go.Scattermapbox(
            mode='lines',
            lat=lats,
            lon=lons,
            marker={'size': 10},
            line=dict(width=1, color='purple'),
        ))

        flight_routes_map.update_layout(
            mapbox={
                'accesstoken': 'pk.eyJ1IjoidG9ycmVuZWdyYWFtIiwiYSI6ImNsdmZ5ejEzcjBxNjIybG1ncXBpbTNqdTkifQ.HXP50_TGgZJOxUBmiUNvEg',
                'style': "outdoors",
                'center': {'lon': 0, 'lat': 0},
                'zoom': 2
            },
            margin={'l': 0, 't': 0, 'r': 0, 'b': 0},
            autosize=True
        )

    else:
        info_output = html.Div()

        if info_type == 'airports':
            # Obtener información de los aeropuertos
            airport_info = df[df['Source Airport Code'] == selected_airport_code]
            info_output = html.Table([
                html.Tr([html.Th('Aeropuerto'), html.Td(selected_airport_code)]),
                html.Tr([html.Th('Ciudad'), html.Td(airport_info['Source Airport City'].iloc[0])]),
                html.Tr([html.Th('País'), html.Td(airport_info['Source Airport Country'].iloc[0])]),
                html.Tr([html.Th('Latitud'), html.Td(airport_info['Source Airport Latitude'].iloc[0])]),
                html.Tr([html.Th('Longitud'), html.Td(airport_info['Source Airport Longitude'].iloc[0])])
            ])

            # Crear la figura de Plotly con Mapbox para las conexiones de los aeropuertos
            selected_airport_connections = df[df['Source Airport Code'] == selected_airport_code]
            lats = []
            lons = []
            for index, row in selected_airport_connections.iterrows():
                source_lat = row['Source Airport Latitude']
                source_lon = row['Source Airport Longitude']
                dest_lat = row['Destination Airport Latitude']
                dest_lon = row['Destination Airport Longitude']

                lats += [source_lat, dest_lat, None]
                lons += [source_lon, dest_lon, None]

            flight_routes_map = go.Figure(go.Scattermapbox(
                mode='lines',
                lat=lats,
                lon=lons,
                marker={'size': 10},
                line=dict(width=1, color='blue'),
            ))

            flight_routes_map.update_layout(
                mapbox={
                    'accesstoken': 'pk.eyJ1IjoidG9ycmVuZWdyYWFtIiwiYSI6ImNsdmZ5ejEzcjBxNjIybG1ncXBpbTNqdTkifQ.HXP50_TGgZJOxUBmiUNvEg',
                    'style': "outdoors",
                    'center': {'lon': 0, 'lat': 0},
                    'zoom': 2
                },
                margin={'l': 0, 't': 0, 'r': 0, 'b': 0},
                autosize=True
            )

        elif info_type == 'top_paths':
            # Obtener los 10 aeropuertos con los caminos mínimos más largos
            top_10_longest_paths = get_top_10_longest_paths(selected_airport_code)
            info_output = html.Div([
                html.H3('10 aeropuertos con caminos mínimos más largos desde {}'.format(selected_airport_code)),
                html.Table([
                    html.Tr([html.Th('Aeropuerto'), html.Th('Distancia (km)')]),
                    *[html.Tr([html.Td(code), html.Td('{:.2f}'.format(distance))]) for code, distance in top_10_longest_paths]
                ])
            ])

            # Obtener los recorridos detallados de los caminos mínimos
            detailed_paths = []
            for code, _ in top_10_longest_paths:
                detailed_path = nx.shortest_path(G, source=selected_airport_code, target=code, weight='weight')
                detailed_paths.append((code, detailed_path))

            # Crear el texto para mostrar los recorridos detallados
            detailed_path_text = html.Div([
                html.H3('Recorridos detallados desde {}'.format(selected_airport_code)),
                *[html.P(f'Aeropuerto {code}: {" -> ".join(path)}') for code, path in detailed_paths]
            ])
            info_output.children.append(detailed_path_text)

            # Crear la figura de Plotly con Mapbox para las conexiones de los aeropuertos con caminos mínimos
            lats = []
            lons = []
            for code, _ in top_10_longest_paths:
                # Obtener el camino mínimo desde el aeropuerto seleccionado hasta este aeropuerto
                shortest_path = nx.shortest_path(G, source=selected_airport_code, target=code, weight='weight')

                # Agregar las coordenadas de los aeropuertos al recorrido
                for i in range(len(shortest_path) - 1):
                    source_airport = df[df['Source Airport Code'] == shortest_path[i]].iloc[0]
                    dest_airport = df[df['Source Airport Code'] == shortest_path[i + 1]].iloc[0]

                    lats += [source_airport['Source Airport Latitude'], dest_airport['Source Airport Latitude'], None]
                    lons += [source_airport['Source Airport Longitude'], dest_airport['Source Airport Longitude'], None]

            flight_routes_map = go.Figure(go.Scattermapbox(
                mode='lines',
                lat=lats,
                lon=lons,
                marker={'size': 10},
                line=dict(width=1, color='red'),
            ))

            flight_routes_map.update_layout(
                mapbox={
                    'accesstoken': 'pk.eyJ1IjoidG9ycmVuZWdyYWFtIiwiYSI6ImNsdmZ5ejEzcjBxNjIybG1ncXBpbTNqdTkifQ.HXP50_TGgZJOxUBmiUNvEg',
                    'style': "outdoors",
                    'center': {'lon': 0, 'lat': 0},
                    'zoom': 2
                },
                margin={'l': 0, 't': 0, 'r': 0, 'b': 0},
                autosize=True
            )

        elif info_type == 'all_connections':
            # Crear la figura de Plotly con Mapbox para todas las conexiones del archivo CSV
            lats = []
            lons = []
            for index, row in df.iterrows():
                source_lat = row['Source Airport Latitude']
                source_lon = row['Source Airport Longitude']
                dest_lat = row['Destination Airport Latitude']
                dest_lon = row['Destination Airport Longitude']

                lats += [source_lat, dest_lat, None]
                lons += [source_lon, dest_lon, None]

            flight_routes_map = go.Figure(go.Scattermapbox(
                mode='lines',
                lat=lats,
                lon=lons,
                marker={'size': 10},
                line=dict(width=1, color='green'),
            ))

            flight_routes_map.update_layout(
                mapbox={
                    'accesstoken': 'pk.eyJ1IjoidG9ycmVuZWdyYWFtIiwiYSI6ImNsdmZ5ejEzcjBxNjIybG1ncXBpbTNqdTkifQ.HXP50_TGgZJOxUBmiUNvEg',
                    'style': "outdoors",
                    'center': {'lon': 0, 'lat': 0},
                    'zoom': 2
                },
                margin={'l': 0, 't': 0, 'r': 0, 'b': 0},
                autosize=True
            )
        else:
            info_output = html.Div()
            flight_routes_map = go.Figure()

    return flight_routes_map, info_output

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True)