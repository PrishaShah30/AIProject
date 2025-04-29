from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Placeholder for campus map data (nodes, edges, building locations, bus stops)
# This would likely be loaded from a file (e.g., CSV, JSON, GeoJSON)
# Focused on Livingston Campus based on provided map
CAMPUS_DATA = {
    "buildings": {
        "Livingston Student Center": {"lat": 40.5235, "lon": -74.4368},
        "Tillet Hall": {"lat": 40.5230, "lon": -74.4580}, # Note: Tillet is slightly off the main area of the provided map screenshot but often considered Livingston
        "James Dickson Carr Library": {"lat": 40.5228, "lon": -74.4375},
        "Lynton Towers (North/South)": {"lat": 40.5245, "lon": -74.4380},
        "The Quads (1, 2, 3)": {"lat": 40.5205, "lon": -74.4385},
        "Livingston Recreation Center": {"lat": 40.5190, "lon": -74.4330},
        "Beck Hall": {"lat": 40.5240, "lon": -74.4400},
        "Lucy Stone Hall": {"lat": 40.5230, "lon": -74.4350},
        "Janice H Levin Building": {"lat": 40.5250, "lon": -74.4390},
        # Add more relevant Livingston buildings if needed
    },
    "bus_stops": {
        "Livingston Plaza (Student Center)": {"lat": 40.5240, "lon": -74.4370},
        "Quads Stop": {"lat": 40.5200, "lon": -74.4380},
        "Tillet Hall Stop": {"lat": 40.5228, "lon": -74.4585},
        "Livingston Gym (Rec Center)": {"lat": 40.5195, "lon": -74.4335},
        "Lynton Towers Stop": {"lat": 40.5248, "lon": -74.4382},
        # Add more relevant Livingston stops if needed
    },
    "graph": {
        # Nodes and edges representing paths, distances, travel times would go here
        # This graph data is crucial for the A* algorithm
    }
}

@app.route('/')
def index():
    """Renders the main page with the building selection dropdown."""
    building_names = list(CAMPUS_DATA["buildings"].keys())
    return render_template('index.html', buildings=building_names)

@app.route('/find_nearest_stop', methods=['POST'])
def find_nearest_stop():
    """API endpoint to find the nearest bus stop to a selected building."""
    selected_building = request.form.get('building')
    if not selected_building or selected_building not in CAMPUS_DATA["buildings"]:
        return jsonify({"error": "Invalid building selected"}), 400

    building_location = CAMPUS_DATA["buildings"][selected_building]

    # --- A* Algorithm Placeholder ---
    # TODO: Implement A* or other pathfinding algorithm here
    # This section should:
    # 1. Get the selected building's coordinates (building_location).
    # 2. Access the campus graph data (CAMPUS_DATA['graph']).
    # 3. Find the nearest bus stop node in the graph to the building.
    # 4. Calculate walking and driving distances/times using the graph edges.

    # Dummy data for now
    nearest_stop_name = "Livingston Plaza" # Replace with actual result
    nearest_stop_location = CAMPUS_DATA["bus_stops"][nearest_stop_name]
    result = {
        "building_name": selected_building,
        "building_location": building_location,
        "nearest_stop": {
            "name": nearest_stop_name,
            "location": nearest_stop_location,
            "walking": {
                "distance_miles": 0.5,
                "time_minutes": 8
            },
            "driving": {
                 # Driving might not be applicable directly *to* the stop
                 # but could represent time to a nearby pickup point
                "distance_miles": 0.6,
                "time_minutes": 2
            }
        }
    }
    # --- End Placeholder ---

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True) 