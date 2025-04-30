import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
import heapq  # Required for  A* implementation
import math   # Required for distance calculations
from collections import defaultdict # Helpful for building edges

load_dotenv() # Load variables from .env file

app = Flask(__name__)

# --- Request Counters & Maintenance Threshold (In-Memory) ---
# Counts reset on server restart.
MAINTENANCE_REQUEST_THRESHOLD = 10000 # Trigger maintenance after this many total requests since last restart
request_counts = {
    "map_loads": 0,
    "directions_requests": 0
}

# campus map data (nodes, edges, building locations, bus stops)
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
        "Rutgers Business School": {"lat": 40.5248, "lon": -74.4358}, # Added RBS
        "Ernest A. Lynton South Towers": {"lat": 40.5245, "lon": -74.4380}, # Added based on distance data
        "U.S. Post Office": {"lat": 40.5210, "lon": -74.4395}, # Estimated location near Quads
        "Livingston Dining Commons": {"lat": 40.5208, "lon": -74.4390}, # Estimated location near Quads
        "Quad Three Residence Hall": {"lat": 40.5205, "lon": -74.4385}, # Same as general Quads for now
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

# --- Provided Walking Distances (Building to Stop) ---
# Source: User input
# Units: Meters
# NOTE: Keys updated to match CAMPUS_DATA['bus_stops'] names
WALKING_DISTANCES_METERS = {
    "Livingston Plaza (Student Center)": { # Updated distances based on user input (converted from miles)
        "Rutgers Business School": 322,  # 0.2 miles
        "Janice H Levin Building": 322,  # 0.2 miles (Using name from old data)
        "Livingston Student Center": 0,    # 0 miles
        "Beck Hall": 322,  # 0.2 miles
        "James Dickson Carr Library": 145,  # 0.09 miles
        "Ernest A. Lynton South Towers": 113,  # 0.07 miles
        "Tillet Hall": 483,  # 0.3 miles (Using name from old data)
        "U.S. Post Office": 322,  # 0.2 miles
        "Lucy Stone Hall": 322,  # 0.2 miles
        "Livingston Dining Commons": 145,  # 0.09 miles
        "Quad Three Residence Hall": 483   # 0.3 miles
    },
    "Quads Stop": { # Renamed from "Livingston Quads Bus Stop" - Keeping old values
        "Rutgers Business School": 800,
        "Janice H Levin Building": 750,
        "Livingston Student Center": 700,
        "Beck Hall": 850,
        "James Dickson Carr Library": 650,
        "Ernest A. Lynton South Towers": 200,
        "Tillet Hall": 250,
        "U.S. Post Office": 150,
        "Lucy Stone Hall": 300,
        "Livingston Dining Commons": 100,
        "Quad Three Residence Hall": 120
    },
}

# --- Helper Functions ---

METERS_PER_MILE = 1609.34
AVG_WALKING_SPEED_METERS_PER_MINUTE = 83 # Approx 3.1 mph

def meters_to_miles(meters):
    """Converts meters to miles."""
    return meters / METERS_PER_MILE

def estimate_walking_time_minutes(meters):
    """Estimates walking time in minutes based on average speed."""
    if meters == 0:
        return 0
    # Using math.ceil to round up to the nearest whole minute
    return math.ceil(meters / AVG_WALKING_SPEED_METERS_PER_MINUTE) if meters > 0 else 0

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the earth (in meters)."""
    R = 6371000 # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

# --- Graph Creation ---

def create_simplified_graph(buildings_data, bus_stops_data, walking_distances):
    """
    Creates a simplified graph with nodes for known buildings/stops
    and edges based *only* on the provided direct walking_distances.
    """
    nodes = {}
    edges = defaultdict(dict)
    node_id_counter = 1
    name_to_id = {}

    # Create nodes for buildings referenced in distances
    building_names_in_distances = set()
    for stop_data in walking_distances.values():
        building_names_in_distances.update(stop_data.keys())

    for name, data in buildings_data.items():
        if name in building_names_in_distances: # Only add buildings we have distances for
            nodes[node_id_counter] = {
                "name": name,
                "type": "building",
                "lat": data["lat"],
                "lon": data["lon"]
            }
            name_to_id[name] = node_id_counter
            node_id_counter += 1

    # Create nodes for bus stops referenced as keys in distances
    for name, data in bus_stops_data.items():
         if name in walking_distances: # Only add stops we have distances *from*
            nodes[node_id_counter] = {
                "name": name,
                "type": "bus_stop",
                "lat": data["lat"],
                "lon": data["lon"]
            }
            name_to_id[name] = node_id_counter
            node_id_counter += 1

    # Create edges based on walking_distances
    for stop_name, building_distances in walking_distances.items():
        if stop_name not in name_to_id: continue # Skip if stop node wasn't created

        stop_node_id = name_to_id[stop_name]

        for building_name, distance in building_distances.items():
            if building_name not in name_to_id: continue # Skip if building node wasn't created

            building_node_id = name_to_id[building_name]
            # Add bi-directional edge with the given distance as cost
            if distance >= 0: # Ensure valid distance
                edges[stop_node_id][building_node_id] = distance
                edges[building_node_id][stop_node_id] = distance

    return nodes, edges, name_to_id

# Populate the graph using existing data
CAMPUS_DATA['graph'] = {} # Initialize graph dict
CAMPUS_DATA['graph']['nodes'], CAMPUS_DATA['graph']['edges'], CAMPUS_DATA['graph']['name_to_id'] = create_simplified_graph(
    CAMPUS_DATA['buildings'],
    CAMPUS_DATA['bus_stops'],
    WALKING_DISTANCES_METERS
)

# --- A* Search Implementation ---

def a_star_search(graph_nodes, graph_edges, start_node_id, goal_node_ids_set):
    """
    Performs A* search on the campus graph. Finds path to the nearest goal node.
    Args:
        graph_nodes: Dictionary of nodes {node_id: {'lat': lat, 'lon': lon, ...}}
        graph_edges: Adjacency list {node_id: {neighbor_id: distance, ...}}
        start_node_id: The ID of the starting node.
        goal_node_ids_set: A set of target node IDs (bus stops).

    Returns:
        A tuple: (path_list, total_distance, goal_node_id) if a path is found,
                 otherwise (None, None, None).
                 path_list is a list of node IDs from start to goal.
    """
    if start_node_id not in graph_nodes or not goal_node_ids_set:
        print("A* Error: Invalid start or goal node IDs.")
        return None, None, None

    # Filter goal nodes that actually exist in the graph
    valid_goal_node_ids = {gid for gid in goal_node_ids_set if gid in graph_nodes}
    if not valid_goal_node_ids:
        print("A* Error: No valid goal node IDs found in the graph.")
        return None, None, None

    # Find the geographically closest goal node for heuristic calculation.
    start_lat, start_lon = graph_nodes[start_node_id]['lat'], graph_nodes[start_node_id]['lon']
    closest_goal_node_id_for_h = -1
    min_h_dist = float('inf')

    for goal_id in valid_goal_node_ids:
        goal_data = graph_nodes[goal_id]
        dist = haversine(start_lat, start_lon, goal_data['lat'], goal_data['lon'])
        if dist < min_h_dist:
            min_h_dist = dist
            closest_goal_node_id_for_h = goal_id

    # Handle case where no goal node could be evaluated (shouldn't happen if valid_goal_node_ids is populated)
    if closest_goal_node_id_for_h == -1:
         print("A* Error: Could not determine closest goal node for heuristic.")
         return None, None, None

    closest_goal_lat = graph_nodes[closest_goal_node_id_for_h]['lat']
    closest_goal_lon = graph_nodes[closest_goal_node_id_for_h]['lon']

    # A* Data Structures
    open_set = []  # Priority queue (min-heap) stores (f_score, node_id)
    heapq.heappush(open_set, (haversine(start_lat, start_lon, closest_goal_lat, closest_goal_lon), start_node_id))

    came_from = {}  # Stores {node_id: previous_node_id} for path reconstruction
    g_score = defaultdict(lambda: float('inf')) # Cost from start to node
    g_score[start_node_id] = 0
    f_score = defaultdict(lambda: float('inf')) # Estimated total cost (g + h)
    f_score[start_node_id] = g_score[start_node_id] + haversine(start_lat, start_lon, closest_goal_lat, closest_goal_lon)

    open_set_hash = {start_node_id} # Track nodes currently in the priority queue

    while open_set:
        current_f_score, current_node_id = heapq.heappop(open_set)
        open_set_hash.remove(current_node_id)

        # --- Goal Check ---
        if current_node_id in valid_goal_node_ids:
            # Path found! Reconstruct path.
            path = []
            temp_id = current_node_id
            while temp_id in came_from:
                path.append(temp_id)
                temp_id = came_from[temp_id]
            path.append(start_node_id)
            path.reverse()
            # Return the path, the actual cost (g_score), and the specific goal node ID reached
            return path, g_score[current_node_id], current_node_id

        # --- Explore Neighbors ---
        # Check if current_node_id exists in graph_edges and has neighbors
        if current_node_id in graph_edges:
            for neighbor_id, distance in graph_edges[current_node_id].items():
                if neighbor_id not in graph_nodes: continue # Skip invalid neighbors

                tentative_g_score = g_score[current_node_id] + distance

                if tentative_g_score < g_score[neighbor_id]:
                    # This path to neighbor is better than any previous one. Record it.
                    came_from[neighbor_id] = current_node_id
                    g_score[neighbor_id] = tentative_g_score

                    neighbor_lat = graph_nodes[neighbor_id]['lat']
                    neighbor_lon = graph_nodes[neighbor_id]['lon']
                    h_val = haversine(neighbor_lat, neighbor_lon, closest_goal_lat, closest_goal_lon)
                    f_score[neighbor_id] = tentative_g_score + h_val

                    if neighbor_id not in open_set_hash:
                        heapq.heappush(open_set, (f_score[neighbor_id], neighbor_id))
                        open_set_hash.add(neighbor_id)

    print(f"A* Warning: Path not found from node {start_node_id} to goals {valid_goal_node_ids}.")
    return None, None, None # Path not found

# --- End A* Search ---

@app.route('/')
def index():
    """Renders the main page with the building selection dropdown."""
    global request_counts # Use global in-memory counter

    # --- Check Maintenance Mode --- #
    total_requests = request_counts['map_loads'] + request_counts['directions_requests']
    maintenance_mode = total_requests >= MAINTENANCE_REQUEST_THRESHOLD

    if not maintenance_mode:
        # Count map load only if not in maintenance mode
        request_counts['map_loads'] += 1
        total_requests += 1 # Update total for logging
        print(f"Total Requests (since restart): {total_requests}, Map loads: {request_counts['map_loads']}, Directions: {request_counts['directions_requests']}") # Log counts
    else:
         print(f"Maintenance Mode Active. Total Requests (since restart): {total_requests}")
    # --- End Check Maintenance Mode --- #

    # Use building names present in the distance data for selection
    available_buildings = set()
    for stop_data in WALKING_DISTANCES_METERS.values():
        available_buildings.update(stop_data.keys())

    # Ensure these buildings also have coordinates defined
    building_names = sorted([b for b in available_buildings if b in CAMPUS_DATA["buildings"]])

    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not google_maps_api_key:
        print("Warning: GOOGLE_MAPS_API_KEY not found in environment variables.")
        google_maps_api_key = None

    return render_template('index.html', buildings=building_names, google_maps_api_key=google_maps_api_key, maintenance_mode=maintenance_mode)

@app.route('/find_nearest_stop', methods=['POST'])
def find_nearest_stop():
    # print("--- find_nearest_stop: Entered function ---") # DEBUG REMOVED
    global request_counts

    try:
        # print("--- find_nearest_stop: Inside try block ---") # DEBUG REMOVED
        # --- Maintenance Check ---
        total_requests = request_counts['map_loads'] + request_counts['directions_requests']
        # print(f"--- find_nearest_stop: Checking maintenance (Total: {total_requests}) ---") # DEBUG REMOVED
        if total_requests >= MAINTENANCE_REQUEST_THRESHOLD:
            # print("--- find_nearest_stop: Maintenance Mode Active --- ") # DEBUG REMOVED
            return jsonify({"error": "currently on maintenance, big upgrade coming"}), 503
        # --- End Maintenance Check ---

        selected_building_name = request.form.get('building')
        # print(f"--- find_nearest_stop: Building selected: {selected_building_name} ---") # DEBUG REMOVED
        if not selected_building_name:
            # print("--- find_nearest_stop: No building selected --- ") # DEBUG REMOVED
            return jsonify({"error": "No building selected"}), 400

        # --- A* Pathfinding ---
        # print("--- find_nearest_stop: Accessing graph data ---") # DEBUG REMOVED
        graph_nodes = CAMPUS_DATA['graph']['nodes']
        graph_edges = CAMPUS_DATA['graph']['edges']
        name_to_id = CAMPUS_DATA['graph']['name_to_id']

        # print("--- find_nearest_stop: Finding start node ID ---") # DEBUG REMOVED
        start_node_id = None
        for node_id, node_data in graph_nodes.items():
            if node_data['type'] == 'building' and node_data['name'] == selected_building_name:
                start_node_id = node_id
                break
        # print(f"--- find_nearest_stop: Start node ID found: {start_node_id} ---") # DEBUG REMOVED

        if start_node_id is None:
            # print(f"--- find_nearest_stop: Start node ID is None for '{selected_building_name}' ---") # DEBUG REMOVED
            return jsonify({"error": f"No pathfinding data available for building: {selected_building_name}"}), 404

        # print("--- find_nearest_stop: Finding goal node IDs ---") # DEBUG REMOVED
        goal_node_ids_set = {
            node_id for node_id, node_data in graph_nodes.items()
            if node_data['type'] == 'bus_stop'
        }
        # print(f"--- find_nearest_stop: Goal node IDs: {goal_node_ids_set} ---") # DEBUG REMOVED

        if not goal_node_ids_set:
             # print("--- find_nearest_stop: No goal nodes found --- ") # DEBUG REMOVED
             # This case should hopefully not happen now after the data fix
             return jsonify({"error": "No bus stop nodes found in the graph (data inconsistency?)."}), 500

        # Run A*
        # print(f"--- find_nearest_stop: Calling a_star_search from {start_node_id} to {goal_node_ids_set} ---") # DEBUG REMOVED
        path_ids, total_distance_meters, goal_node_id = a_star_search(
            graph_nodes,
            graph_edges,
            start_node_id,
            goal_node_ids_set
        )
        # print(f"--- find_nearest_stop: a_star_search returned: path={path_ids is not None}, distance={total_distance_meters}, goal={goal_node_id} ---") # DEBUG REMOVED

        if path_ids is None:
            # print(f"--- find_nearest_stop: A* failed (path_ids is None) for {selected_building_name} ---") # DEBUG REMOVED
            return jsonify({"error": f"Could not find a direct path from {selected_building_name} to a bus stop based on available data."}), 404

        # --- Process A* Results ---
        # print("--- find_nearest_stop: Processing A* results --- ") # DEBUG REMOVED
        nearest_stop_node_data = graph_nodes[goal_node_id]
        nearest_stop_name = nearest_stop_node_data['name']
        nearest_stop_location = {"lat": nearest_stop_node_data['lat'], "lon": nearest_stop_node_data['lon']}

        building_node_data = graph_nodes[start_node_id]
        building_location = {"lat": building_node_data['lat'], "lon": building_node_data['lon']}

        distance_miles = meters_to_miles(total_distance_meters)
        time_minutes = estimate_walking_time_minutes(total_distance_meters)

        # print("--- find_nearest_stop: Calculating path coordinates --- ") # DEBUG REMOVED
        path_coordinates = []
        if path_ids:
             path_coordinates = [{"lat": graph_nodes[nid]['lat'], "lng": graph_nodes[nid]['lon']} for nid in path_ids if nid in graph_nodes]
        # print(f"--- find_nearest_stop: Path coordinates length: {len(path_coordinates)} ---") # DEBUG REMOVED

        # --- Count Directions Request ---
        # print("--- find_nearest_stop: Counting request --- ") # DEBUG REMOVED
        request_counts['directions_requests'] += 1
        current_total_requests = request_counts['map_loads'] + request_counts['directions_requests']
        # Keep this print for monitoring usage
        print(f"Total Requests (since restart): {current_total_requests}, Map loads: {request_counts['map_loads']}, Directions: {request_counts['directions_requests']}")

        # print("--- find_nearest_stop: Building result dictionary --- ") # DEBUG REMOVED
        result = {
            "building_name": selected_building_name,
            "building_location": building_location,
            "nearest_stop": {
                "name": nearest_stop_name,
                "location": nearest_stop_location,
                "walking": {
                    "distance_meters": round(total_distance_meters, 2),
                    "distance_miles": round(distance_miles, 2),
                    "time_minutes": time_minutes
                }
            },
            "path_coordinates": path_coordinates
        }

        # print("--- find_nearest_stop: Preparing to return jsonify(result) --- ") # DEBUG REMOVED
        return jsonify(result)

    except Exception as e:
        import traceback
        print("--- UNHANDLED EXCEPTION IN /find_nearest_stop --- ") # Keep this
        traceback.print_exc()
        print("--------------------------------------------------")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    app.run(debug=True) 