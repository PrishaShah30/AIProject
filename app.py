import heapq

# --- Graph Definition (distances in meters) ---
graph = {
    "Livingston Student Center Bus Stop": {
        "Rutgers Business School": 240,
        "Janice H. Levin Building": 320,
        "Livingston Student Center": 0,
        "Beck Hall": 400,
        "James Dickson Carr Library": 160,
        "Ernest A. Lynton South Towers": 480,
        "Tillett Hall": 560,
        "U.S. Post Office": 300,
        "Lucy Stone Hall": 600,
        "Livingston Dining Commons": 450,
        "Quad Three Residence Hall": 500
    },
    "Livingston Quads Bus Stop": {
        "Rutgers Business School": 800,
        "Janice H. Levin Building": 750,
        "Livingston Student Center": 700,
        "Beck Hall": 850,
        "James Dickson Carr Library": 650,
        "Ernest A. Lynton South Towers": 200,
        "Tillett Hall": 250,
        "U.S. Post Office": 150,
        "Lucy Stone Hall": 300,
        "Livingston Dining Commons": 100,
        "Quad Three Residence Hall": 120
    },
    "Livingston Plaza Bus Stop": {
        "Rutgers Business School": 400,
        "Janice H. Levin Building": 100,
        "Livingston Student Center": 300,
        "Beck Hall": 300,
        "James Dickson Carr Library": 450,
        "Ernest A. Lynton South Towers": 700,
        "Tillett Hall": 750,
        "U.S. Post Office": 600,
        "Lucy Stone Hall": 700,
        "Livingston Dining Commons": 650,
        "Quad Three Residence Hall": 680
    }
}

# --- Make edges bidirectional ---
for src in list(graph):
    for dest, dist in graph[src].items():
        if dest not in graph:
            graph[dest] = {}
        graph[dest][src] = dist

# --- Heuristic Table (estimated distance to closest bus stop) ---
heuristic_estimates = {
    "Rutgers Business School": 240,
    "Janice H. Levin Building": 100,
    "Livingston Student Center": 0,
    "Beck Hall": 300,
    "James Dickson Carr Library": 160,
    "Ernest A. Lynton South Towers": 200,
    "Tillett Hall": 250,
    "U.S. Post Office": 150,
    "Lucy Stone Hall": 300,
    "Livingston Dining Commons": 100,
    "Quad Three Residence Hall": 120,
    "Livingston Student Center Bus Stop": 0,
    "Livingston Quads Bus Stop": 0,
    "Livingston Plaza Bus Stop": 0
}

def heuristic(node, goal_nodes):
    # In this simple case, we precomputed a heuristic estimate per node
    return heuristic_estimates.get(node, float('inf'))

# --- A* Algorithm ---
def a_star(start, goal_nodes):
    visited = set()
    pq = [(heuristic(start, goal_nodes), 0, start, [start])]  # (f = g + h, g, node, path)

    while pq:
        f, cost, current, path = heapq.heappop(pq)
        if current in goal_nodes:
            return path, cost

        if current in visited:
            continue
        visited.add(current)

        for neighbor, weight in graph[current].items():
            if neighbor not in visited:
                g = cost + weight
                h = heuristic(neighbor, goal_nodes)
                heapq.heappush(pq, (g + h, g, neighbor, path + [neighbor]))

    return None, float('inf')

# --- Example Usage ---
if __name__ == "__main__":
    start_building = "Janice H. Levin Building"
    bus_stops = {
        "Livingston Student Center Bus Stop",
        "Livingston Quads Bus Stop",
        "Livingston Plaza Bus Stop"
    }

    path, total_cost = a_star(start_building, bus_stops)
    if path:
        print(f"Shortest path from {start_building} to closest bus stop:")
        print(" → ".join(path))
        print(f"Total walking distance: {total_cost} meters")
    else:
        print("No path found.")
