# Urban Traffic Simulator

A Python-based simulation engine developed to model large-scale urban mobility. This project focuses on the interaction between different transport modes—pedestrians, cars, and heavy vehicles—within real-world road networks.

## 1. Introduction
This project started as an investigation into how Python handles massive, concurrent data processing within a spatial context. The goal was to build a simulator that wasn't just a toy model, but a tool capable of running on real-world city maps. 

By integrating OpenStreetMap data, the engine simulates how thousands of agents navigate through complex street layouts. The project evolved from a simple routing script into a highly optimized engine, shifting the focus from "how to move an agent" to "how to manage 25,000 agents efficiently." It serves as a practical exploration of graph theory, multiprocessing, and system resource management.

## 2. Key Features
The simulator is built around several core functionalities that allow for a realistic representation of urban traffic:

* **Real-World Infrastructure:** Utilizes `OSMnx` and `NetworkX` to download and model actual street networks. It supports different network types (drive and walk) to ensure agents move on appropriate paths.
* **Multi-Agent Ecosystem:** Manages three distinct classes of agents—Pedestrians, Standard Vehicles, and Heavy Vehicles—each with specific speed variables and "road footprint" (impact on congestion).
* **Dynamic Traffic Constraints:**
    * **Traffic Lights:** Tick-based intersection logic that alternates flow based on the simulation clock.
    * **Road Capacity:** Edges have limited volume; when capacity is reached, agents experience delays or "stalling," simulating real-world traffic jams.
* **Interactive Barrier Management:** A real-time system to "block" specific nodes or edges. The engine recalculates weights, forcing agents to find alternative routes or remain stuck, simulating roadwork or accidents.
* **3D Geospatial Visualization:** Real-time rendering via `Pydeck` and `Streamlit`, allowing for a 3D view of agents moving through the city with color-coded status indicators (moving vs. congested).

## 3. The Engineering Challenge

The primary challenge of this project was scaling the simulation to 10,000+ agents. In Python, moving from a single-threaded script to a high-performance engine revealed significant architectural bottlenecks that required a deep dive into system resource management.

### Identifying the Bottleneck
Initial attempts to use standard multiprocessing led to a "Parallelism Paradox": adding more CPU cores actually made the simulation slower (jumping from 4 minutes to 25 minutes for 25,000 agents). 



Through profiling, I identified that the culprit was **Serialization (Pickling)**. Python was attempting to copy the entire multi-megabyte city graph to every single process for every single agent. The system was spending 90% of its time on Inter-Process Communication (IPC) and only 10% on actual pathfinding.

### Engineering the Solution
To resolve this, I re-engineered the engine’s data flow using three core strategies:

1. **Shared Memory via Global Initializers:** I implemented a "Shared Memory" approach. Instead of passing the graph as an argument, I used a global initializer that loads the map into each CPU core's memory only once at startup. This reduced the task payload from a heavy graph object to a lightweight tuple of coordinates.
2. **Memory-Optimized Agent Architecture:** I decoupled the `Agent` objects from the `NetworkX` graph. By pre-calculating and storing only the necessary coordinate paths, I achieved a stable RAM footprint of **~370MB for 25,000 agents**, preventing memory swapping and crashes.
3. **Temporal Congestion Sampling:** I optimized the simulation loop by sampling road occupancy every 5 ticks instead of every tick. This "Temporal Sampling" provided a massive CPU relief without affecting the macroscopic accuracy of the traffic flow.

## 4. Benchmark Analysis: Optimization Impact

To evaluate the efficiency of the engine, I conducted extensive stress tests comparing the initial sequential logic against the final optimized parallel architecture. The data shows that the final version doesn't just run faster; it scales more efficiently as the population grows.

### Sequential vs. Parallel
The most significant improvement was seen in the "Massive Population" scenario (25,000 agents). The unoptimized multiprocessing attempt suffered from heavy serialization overhead, while the final **Shared Memory** approach achieved a breakthrough in throughput.

| Scenario | Agents | Ticks | Elapsed_s | Rows_Generated | Throughput_Rows_s | RAM_Usage_MB | Peak_RAM_MB |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline** | 100 | 100 | 9.2538 | 5247 | 567.0 | 76.83 | 214.32 |
| **Standard** | 1000 | 100 | 62.7821 | 47718 | 760.0 | 20.31 | 234.62 |
| **Urban Load** | 5000 | 200 | 307.4083 | 224953 | 732.0 | 9.30 | 243.93 |
| **Heavy Stress** | 15000 | 200 | 904.9189 | 613564 | 678.0 | 52.62 | 296.55 |
| **Massive Population** | 25000 | 300 | 1512.0735 | 993201 | 657.0 | 75.85 | 372.40 |

### Scalability Performance
The final engine demonstrates a non-linear performance gain: as the agent count increases, the system becomes more efficient at utilizing CPU cycles.

| Scenario | Agents | Ticks | Elapsed_s | Rows_Generated | Throughput_Rows_s | RAM_Usage_MB | Peak_RAM_MB |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline** | 100 | 100 | 24.6426 | 5659 | 230.0 | 75.92 | 213.54 |
| **Standard** | 1000 | 100 | 30.8727 | 47051 | 1524.0 | 20.36 | 233.91 |
| **Urban Load** | 5000 | 200 | 38.6644 | 211514 | 5471.0 | 12.73 | 246.63 |
| **Heavy Stress** | 15000 | 200 | 63.2189 | 594194 | 9399.0 | 49.23 | 295.86 |
| **Massive Population** | 25000 | 300 | 79.6477 | 966183 | 12131.0 | 75.52 | 371.38 |


## 5. Installation & Setup

This project is built with Python 3.9+. To replicate the simulation or the benchmarks locally, follow these steps:

### 1. Prerequisites
Ensure you have `pip` and a virtual environment manager installed. The simulation requires several spatial and data science libraries:
* **OSMnx / NetworkX:** For street network modeling.
* **Streamlit / Pydeck:** For the interactive dashboard and 3D rendering.
* **Pandas / NumPy:** For high-speed data manipulation.

### 2. Local Installation
```bash
# Clone the repository
git clone [https://github.com/your-username/Traffic-Simulator.git](https://github.com/your-username/Traffic-Simulator.git)
cd Traffic-Simulator

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
