# RouteSync AI

## Overview

RouteSync AI is a web application designed to help users find the nearest bus stop to a specific building on a university campus (initially designed with Rutgers University locations in mind).

Given a target building, the application calculates and displays the estimated walking and driving time/distance to the closest bus stop.

## Features (Current & Planned)

*   **Building Selection:** Choose a campus building from a dropdown list.
*   **Nearest Stop Calculation:** Displays the name, distance, and estimated travel time (walking/driving) to the nearest bus stop (currently uses placeholder data).
*   **(Planned)** **Pathfinding:** Implement A* algorithm or similar to calculate actual shortest paths using campus map data (walkways, roads).
*   **(Planned)** **Map Integration:** Display the building, nearest stop, and the calculated route on an interactive map (e.g., Google Maps, Leaflet).
*   **(Planned)** **Real Campus Data:** Load actual building coordinates, bus stop locations, and path network data (nodes/edges with weights for distance/time).
*   **(Planned)** **User Location:** Option to use the user's current location as the starting point.

## Technology Stack

*   **Backend:** Python, Flask
*   **Frontend:** HTML, CSS, JavaScript
*   **Pathfinding (Planned):** A* algorithm
*   **Map Display (Planned):** Google Maps API / Leaflet

## Setup

1.  **Create and activate a virtual environment:**
    *(This isolates project dependencies)*
    ```bash
    # Create the virtual environment
    python3 -m venv venv

    # Activate it (macOS/Linux)
    source venv/bin/activate

    # Activate it (Windows - Git Bash/WSL)
    # source venv/Scripts/activate

    # Activate it (Windows - Command Prompt)
    # venv\Scripts\activate.bat

    # Activate it (Windows - PowerShell)
    # venv\Scripts\Activate.ps1
    ```
    You should see `(venv)` at the beginning of your terminal prompt.

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

1.  **Ensure your virtual environment is active.** (See step 2 in Setup if not).

2.  **Run the Flask development server:**
    ```bash
    python app.py
    ```

3.  **Open your web browser** and navigate to the address provided by Flask (usually `http://127.0.0.1:5000` or `http://localhost:5000`).

## Development Notes
Test
*   The core pathfinding logic needs to be implemented in `app.py` within the `find_nearest_stop` function, replacing the placeholder data.
*   Campus map data (building/stop coordinates, graph nodes/edges) needs to be created and loaded, likely from a file (e.g., JSON, CSV).
*   Frontend map integration requires adding a mapping library (like Google Maps API or Leaflet) to `templates/index.html` and calling it from the JavaScript. 
