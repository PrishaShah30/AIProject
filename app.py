import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
import heapq
import math
from collections import defaultdict

load_dotenv()

app = Flask(__name__)

# --- Configuration ---
MAINTENANCE_REQUEST_THRESHOLD = 10000
request_counts = {"map_loads": 0, "directions_requests": 0}
METERS_PER_MILE = 1609.34
AVG_WALKING_SPEED_METERS_PER_MINUTE = 83

# --- Core Data --- #

# Updated Buildings based on the table provided
BUILDINGS_DATA = {
    "Livingston Student Center": {"lat": 40.5235, "lon": -74.4368},
    "Tillet Hall": {"lat": 40.5230, "lon": -74.4580},
    "James Dickson Carr Library": {"lat": 40.5228, "lon": -74.4375},
    "Lynton Towers (North/South)": {"lat": 40.524597, "lon": -74.436456},
    "The Quads (1, 2, 3)": {"lat": 40.5205, "lon": -74.4385},
    "Livingston Recreation Center": {"lat": 40.5214, "lon": -74.4318},
    "Beck Hall": {"lat": 40.5240, "lon": -74.4400},
    "Lucy Stone Hall": {"lat": 40.5230, "lon": -74.4350},
    "Janice H Levin Building": {"lat": 40.5250, "lon": -74.4390},
    "Rutgers Business School": {"lat": 40.5248, "lon": -74.4358},
    "Ernest A. Lynton South Towers": {"lat": 40.5245, "lon": -74.4380},
    "U.S. Post Office": {"lat": 40.5210, "lon": -74.4395},
    "Livingston Dining Commons": {"lat": 40.5235, "lon": -74.4583},
    "Rutgers Cinema": {"lat": 40.5254, "lon": -74.4375},
    "Livingston Apartments": {"lat": 40.5259, "lon": -74.4372}
}

# Updated Bus Stops based on the table provided
BUS_STOPS_DATA = {
    "Livingston Plaza Bus Stop": {"lat": 40.5255, "lon": -74.4387},
    "Livingston Student Center Bus Stop": {"lat": 40.5235, "lon": -74.4372},
    "Quads Bus Stop": {"lat": 40.519972744342354, "lon": -74.43341298505632},
    "Busch- Livingston Health Center Bus Stop": {"lat": 40.5239, "lon": -74.4429}
}

# Direct walking distances (in MILES) from Building to Stop (from user table)
# Using underscores in keys for easier Python access if needed later
BUILDING_STOP_DISTANCES_MILES = {
    "Livingston Student Center": {
        "Livingston Plaza Bus Stop": 0.2, "Livingston Student Center Bus Stop": 0, "Quads Bus Stop": 0.3, "Busch- Livingston Health Center Bus Stop": 0.4
    },
    "Tillet Hall": {
        "Livingston Plaza Bus Stop": 0.3, "Livingston Student Center Bus Stop": 0.1, "Quads Bus Stop": 0.2, "Busch- Livingston Health Center Bus Stop": 0.5
    },
    "James Dickson Carr Library": {
        "Livingston Plaza Bus Stop": 0.3, "Livingston Student Center Bus Stop": 0.088, "Quads Bus Stop": 0.3, "Busch- Livingston Health Center Bus Stop": 0.4
    },
    "Lynton Towers (North/South)": {
        "Livingston Plaza Bus Stop": 0.3, "Livingston Student Center Bus Stop": 0.2, "Quads Bus Stop": 0.3, "Busch- Livingston Health Center Bus Stop": 0.5
    },
    "The Quads (1, 2, 3)": {
        "Livingston Plaza Bus Stop": 0.5, "Livingston Student Center Bus Stop": 0.3, "Quads Bus Stop": 0.05, "Busch- Livingston Health Center Bus Stop": 0.6
    },
    "Livingston Recreation Center": {
        "Livingston Plaza Bus Stop": 0.6, "Livingston Student Center Bus Stop": 0.4, "Quads Bus Stop": 0.2, "Busch- Livingston Health Center Bus Stop": 0.8
    },
    "Beck Hall": {
        "Livingston Plaza Bus Stop": 0.3, "Livingston Student Center Bus Stop": 0.2, "Quads Bus Stop": 0.4, "Busch- Livingston Health Center Bus Stop": 0.3
    },
    "Lucy Stone Hall": {
        "Livingston Plaza Bus Stop": 0.3, "Livingston Student Center Bus Stop": 0.2, "Quads Bus Stop": 0.3, "Busch- Livingston Health Center Bus Stop": 0.6
    },
    "Janice H Levin Building": {
        "Livingston Plaza Bus Stop": 0.1, "Livingston Student Center Bus Stop": 0.2, "Quads Bus Stop": 0.5, "Busch- Livingston Health Center Bus Stop": 0.2
    },
    "Rutgers Business School": {
        "Livingston Plaza Bus Stop": 0.2, "Livingston Student Center Bus Stop": 0.2, "Quads Bus Stop": 0.5, "Busch- Livingston Health Center Bus Stop": 0.2
    },
    "Ernest A. Lynton South Towers": {
        "Livingston Plaza Bus Stop": 0.2, "Livingston Student Center Bus Stop": 0.088, "Quads Bus Stop": 0.4, "Busch- Livingston Health Center Bus Stop": 0.5
    },
    "U.S. Post Office": {
        "Livingston Plaza Bus Stop": 0.4, "Livingston Student Center Bus Stop": 0.2, "Quads Bus Stop": 0.1, "Busch- Livingston Health Center Bus Stop": 0.6
    },
    "Livingston Dining Commons": {
        "Livingston Plaza Bus Stop": 0.2, "Livingston Student Center Bus Stop": 0.091, "Quads Bus Stop": 0.3, "Busch- Livingston Health Center Bus Stop": 0.3
    },
    "Rutgers Cinema": {
        "Livingston Plaza Bus Stop": 0.05, "Livingston Student Center Bus Stop": 0.2, "Quads Bus Stop": 0.5, "Busch- Livingston Health Center Bus Stop": 0.4
    },
    "Livingston Apartments": {
        "Livingston Plaza Bus Stop": 0.1, "Livingston Student Center Bus Stop": 0.3, "Quads Bus Stop": 0.5, "Busch- Livingston Health Center Bus Stop": 0.5
    }
}

# --- Graph Creation (Simplified Direct Connections) --- #

def create_direct_connection_graph(buildings, stops, distances_miles):
    """
    Creates graph nodes for all buildings/stops and direct edges between
    every building and every stop using provided distances.
    """
    nodes = {}
    edges = defaultdict(dict)
    name_to_id = defaultdict(list) # Use list to handle potential multiple nodes per name (e.g., entrances)
    node_id_counter = 1

    # Create Building Nodes
    building_name_to_ids = defaultdict(list)
    for name, data in buildings.items():
        node_id = node_id_counter
        nodes[node_id] = {
            "name": name,
            "type": "building",
            "lat": data["lat"],
            "lon": data["lon"]
        }
        building_name_to_ids[name].append(node_id)
        name_to_id[name].append(node_id) # Keep overall mapping
        node_id_counter += 1

    # Create Bus Stop Nodes
    stop_name_to_ids = defaultdict(list)
    for name, data in stops.items():
        node_id = node_id_counter
        nodes[node_id] = {
            "name": name,
            "type": "bus_stop",
            "lat": data["lat"],
            "lon": data["lon"]
        }
        stop_name_to_ids[name].append(node_id)
        name_to_id[name].append(node_id) # Keep overall mapping
        node_id_counter += 1

    # Create Edges (Direct Building <-> Stop)
    for building_name, stop_distances in distances_miles.items():
        if building_name not in building_name_to_ids:
            print(f"Warning: Building '{building_name}' from distance table not in Buildings data. Skipping.")
            continue

        building_ids = building_name_to_ids[building_name]

        for stop_name, dist_miles in stop_distances.items():
            if stop_name not in stop_name_to_ids:
                print(f"Warning: Stop '{stop_name}' from distance table not in Bus Stops data. Skipping.")
                continue
            if dist_miles is None or dist_miles < 0: # Skip if distance is missing or invalid
                 print(f"Warning: Invalid distance ({dist_miles}) for {building_name} -> {stop_name}. Skipping edge.")
                 continue

            stop_ids = stop_name_to_ids[stop_name]
            distance_meters = dist_miles * METERS_PER_MILE

            # Add edges from all building nodes to all stop nodes for these names
            for b_id in building_ids:
                for s_id in stop_ids:
                    edges[b_id][s_id] = distance_meters
                    edges[s_id][b_id] = distance_meters # Bidirectional

    # Convert defaultdict to dict for name_to_id before returning if needed elsewhere,
    # but might be fine as defaultdict for internal use.
    return nodes, edges, dict(name_to_id)

# --- Initialize CAMPUS_DATA with the new graph structure --- #
CAMPUS_DATA = {
    "buildings": BUILDINGS_DATA,
    "bus_stops": BUS_STOPS_DATA,
    "graph": {},
    "distances_miles": BUILDING_STOP_DISTANCES_MILES # Store original distances if needed
}

CAMPUS_DATA['graph']['nodes'], CAMPUS_DATA['graph']['edges'], CAMPUS_DATA['graph']['name_to_id'] = create_direct_connection_graph(
    CAMPUS_DATA['buildings'],
    CAMPUS_DATA['bus_stops'],
    CAMPUS_DATA['distances_miles']
)

# --- Helper Functions (Keep existing) --- #
def meters_to_miles(meters):
    """Converts meters to miles."""
    return meters / METERS_PER_MILE if meters is not None else None

def estimate_walking_time_minutes(meters):
    """Estimates walking time in minutes based on average speed."""
    if meters is None or meters <= 0:
        return 0
    return math.ceil(meters / AVG_WALKING_SPEED_METERS_PER_MINUTE)

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the earth (in meters)."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

# --- A* Search Implementation (Keep existing - it works on the provided graph) --- #
def a_star_search(graph_nodes, graph_edges, start_node_id, goal_node_ids_set):
    # ... (A* logic remains the same)
    # ... (It will find the shortest path based on the edges provided)
    # ... (In this case, path will be [start_node_id, closest_stop_node_id])
    if start_node_id not in graph_nodes or not goal_node_ids_set:
        print(f"A* Error: Invalid start node {start_node_id} or goal set {goal_node_ids_set}.")
        return None, None, None

    valid_goal_node_ids = {gid for gid in goal_node_ids_set if gid in graph_nodes}
    if not valid_goal_node_ids:
        print(f"A* Error: No valid goal nodes found in graph for {goal_node_ids_set}.")
        return None, None, None

    # Since edges are direct building-to-stop, pathfinding is simpler
    # We can directly check edge distances for efficiency, but using A* still works

    min_dist = float('inf')
    closest_goal_id = None
    path = []

    if start_node_id not in graph_edges:
        print(f"A* Warning: Start node {start_node_id} has no outgoing edges.")
        return None, None, None

    # Find the closest directly connected goal node
    for neighbor_id, distance in graph_edges[start_node_id].items():
        if neighbor_id in valid_goal_node_ids:
            if distance < min_dist:
                min_dist = distance
                closest_goal_id = neighbor_id

    if closest_goal_id is not None:
        path = [start_node_id, closest_goal_id]
        print(f"A* (Simplified): Found direct path to {closest_goal_id} with distance {min_dist}")
        return path, min_dist, closest_goal_id
    else:
        print(f"A* Warning: No direct path found from {start_node_id} to any goal in {valid_goal_node_ids}.")
        return None, None, None

# --- Flask Routes --- #

@app.route('/')
def index():
    """Renders the main page with the building selection dropdown."""
    global request_counts
    total_requests = request_counts['map_loads'] + request_counts['directions_requests']
    maintenance_mode = total_requests >= MAINTENANCE_REQUEST_THRESHOLD

    if not maintenance_mode:
        request_counts['map_loads'] += 1
        total_requests += 1
        print(f"Request Counts: Total={total_requests}, MapLoads={request_counts['map_loads']}, Directions={request_counts['directions_requests']}")
    else:
        print(f"Maintenance Mode Active. Total Requests Reached: {total_requests}")

    # Use building names directly from our updated BUILDINGS_DATA
    building_names = sorted(list(CAMPUS_DATA["buildings"].keys()))

    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not google_maps_api_key:
        print("Warning: GOOGLE_MAPS_API_KEY not found.")

    return render_template('index.html', buildings=building_names, google_maps_api_key=google_maps_api_key, maintenance_mode=maintenance_mode)

@app.route('/find_nearest_stop', methods=['POST'])
def find_nearest_stop():
    """Finds the nearest bus stop(s) based on direct pre-calculated distances."""
    global request_counts

    try:
        # --- Maintenance Check ---
        total_requests = request_counts['map_loads'] + request_counts['directions_requests']
        if total_requests >= MAINTENANCE_REQUEST_THRESHOLD:
            return jsonify({"error": "Service undergoing maintenance.", "details": "Request threshold reached.", "type": "MAINTENANCE"}), 503
        # --- End Maintenance Check ---

        selected_building_name = request.form.get('building')
        if not selected_building_name:
            return jsonify({"error": "No building selected", "details": "Please select a building from the dropdown.", "type": "USER_INPUT_ERROR"}), 400

        # Get graph data
        graph_nodes = CAMPUS_DATA['graph']['nodes']
        graph_edges = CAMPUS_DATA['graph']['edges']
        name_to_id = CAMPUS_DATA['graph']['name_to_id']

        # Find the starting node ID for the selected building
        if selected_building_name not in name_to_id or not name_to_id[selected_building_name]:
             return jsonify({"error": f"Building data not found for: {selected_building_name}", "details": "Selected building is not in the graph data.", "type": "DATA_ERROR"}), 404
        # Use the first ID if multiple exist (e.g., multiple entrances mapped to one name)
        start_node_id = name_to_id[selected_building_name][0]

        # Get all node IDs that are bus stops
        goal_node_ids_set = {
            node_id for node_id, node_data in graph_nodes.items()
            if node_data['type'] == 'bus_stop'
        }
        if not goal_node_ids_set:
             return jsonify({"error": "No bus stop data available.", "details": "No nodes marked as 'bus_stop' in the graph data.", "type": "DATA_ERROR"}), 500

        # --- Find Minimum Distance and Nearest Stops --- #
        min_distance_meters = float('inf')
        nearest_stop_node_ids = []

        if start_node_id not in graph_edges:
            return jsonify({"error": f"No path data available from {selected_building_name}", "details": "The selected building node has no connections in the graph.", "type": "DATA_ERROR"}), 404

        # Iterate through direct connections from the building node
        for neighbor_id, distance in graph_edges[start_node_id].items():
            if neighbor_id in goal_node_ids_set: # Check if the neighbor is a bus stop
                if distance < min_distance_meters:
                    min_distance_meters = distance
                    nearest_stop_node_ids = [neighbor_id] # New minimum found, reset list
                elif distance == min_distance_meters:
                    nearest_stop_node_ids.append(neighbor_id) # Add to list of ties

        if not nearest_stop_node_ids:
            return jsonify({"error": f"Could not find a route from {selected_building_name} to any bus stop.", "details": "No connected bus stops found for the selected building.", "type": "NO_ROUTE"}), 404
        # --- End Finding --- #

        # Prepare list of nearest stop details
        nearest_stops_details = []
        for stop_id in nearest_stop_node_ids:
            stop_node_data = graph_nodes.get(stop_id)
            if stop_node_data:
                nearest_stops_details.append({
                    "name": stop_node_data['name'],
                    "location": {"lat": stop_node_data['lat'], "lon": stop_node_data['lon']}
                })

        # Calculate distance/time based on the minimum found
        distance_miles = meters_to_miles(min_distance_meters)
        time_minutes = estimate_walking_time_minutes(min_distance_meters)

        building_node_data = graph_nodes[start_node_id]
        building_location = {"lat": building_node_data['lat'], "lon": building_node_data['lon']}

        # Path coordinates are just building -> first nearest stop (for simple visualization)
        first_stop_location = nearest_stops_details[0]["location"] if nearest_stops_details else None
        path_coordinates = []
        if first_stop_location:
            path_coordinates = [
                {"lat": building_location['lat'], "lng": building_location['lon']},
                {"lat": first_stop_location['lat'], "lng": first_stop_location['lon']}
            ]

        # Count request
        request_counts['directions_requests'] += 1
        current_total_requests = request_counts['map_loads'] + request_counts['directions_requests']
        print(f"Request Counts: Total={current_total_requests}, MapLoads={request_counts['map_loads']}, Directions={request_counts['directions_requests']}")

        # Structure the result
        result = {
            "building_name": selected_building_name,
            "building_location": building_location,
            "nearest_stops": nearest_stops_details, # List of stops sharing min distance
            "walking": {
                "distance_meters": round(min_distance_meters, 2) if min_distance_meters != float('inf') else None,
                "distance_miles": round(distance_miles, 2) if distance_miles is not None else None,
                "time_minutes": time_minutes
            },
            "path_coordinates": path_coordinates # Simple path for visualization
        }

        return jsonify(result)

    except Exception as e:
        import traceback
        print("--- UNHANDLED EXCEPTION IN /find_nearest_stop ---")
        traceback.print_exc()
        print("--------------------------------------------------")
        # Provide a more informative generic error
        return jsonify({"error": "An internal server error occurred processing your request.", "details": str(e), "type": "SERVER_ERROR"}), 500

if __name__ == '__main__':
    # Consider environment variables for host/port/debug
    app_host = os.getenv("APP_HOST", "127.0.0.1")
    app_port = int(os.getenv("APP_PORT", "5000"))
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ["true", "1", "yes"]
    print(f"Starting Flask app on {app_host}:{app_port} with debug={debug_mode}")
    app.run(host=app_host, port=app_port, debug=debug_mode)

