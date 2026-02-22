# Urban Traffic Simulator

A high-performance Python simulation engine designed to model and analyze large-scale urban mobility. This project transforms raw geospatial data into a living, interactive metropolis, allowing users to explore the complex dynamics of city traffic in real-time.
## Video Demo
https://github.com/viky17/TrafficSimulator/Assets/demo.mp4

## 1. Introduction:
This project is more than just a routing script; it is a **geospatial experiment** designed to handle massive concurrent data processing. The core philosophy was to move beyond "toy models" and build a tool capable of simulating real-world city districts with extreme fidelity.

By integrating OpenStreetMap data, the simulator allows you to:
* **Simulate Any Location:** Download and populate any street network worldwide, from a small neighborhood to a sprawling metropolis.
* **Be the Urban Planner:** Interactively block roads or create bottlenecks to observe how traffic flow redistributes across the city graph.
* **Analyze Multi-Modal Stress:** Observe how different entities—from pedestrians to heavy trucks—compete for road capacity and impact urban congestion.

What started as an investigation into Python's performance evolved into a highly optimized engine, shifting the focus from simple agent movement to the efficient management of **75,000+ agents** in a 3D environment.

## 2. Key Features
The simulator provides a robust set of tools for both interactive exploration and technical analysis:

* **Infinite World Maps:** Direct integration with `OSMnx` and `NetworkX` to model actual street layouts, supporting distinct pathfinding for driving and walking networks.
* **Interactive Environment Management:** * **Live Road Blocks:** Real-time system to "block" nodes or edges. The engine immediately forces agents to find alternative routes, simulating accidents or roadwork.
    * **Adaptive Traffic Lights:** Tick-based logic that alternates flow at intersections based on the global simulation clock.
* **Massive Multi-Agent Ecosystem:** Manages three distinct classes (Pedestrians, Cars, Heavy Vehicles) with individual speeds and "road footprints" that dynamically influence congestion.
* **Resource-Aware Congestion:** Edges have limited volume; when capacity is reached, agents experience realistic delays or "stalling."
* **GPU-Accelerated 3D Visualization:** Real-time rendering via `Pydeck` and `Streamlit`, providing a bird's-eye 3D view with color-coded status indicators for movement and gridlock.

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

## 5 Extreme Scale Testing & System Limits

Finding the operational limits of the engine is crucial for understanding its reliability in production-grade scenarios. I pushed the simulator beyond standard urban loads to identify the "breaking point" of the current architecture on consumer-grade hardware.

### Results: From Metropolis to the Breaking Point
As the agent count and search radius increased, the engine continued to process millions of data points until reaching the physical limits of the system.

| Scenario | Agents | Radius | Ticks | Elapsed_s | Rows_Generated | Throughput (Rows/s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **District Scale** | 30,000 | 1500m | 100 | 258.81s | 1,445,833 | 5,586 |
| **City Scale** | 50,000 | 2000m | 100 | 539.71s | 2,796,979 | 5,182 |
| **Metropolis Scale** | 75,000 | 3000m | 150 | 1317.36s | 5,663,755 | 4,299 |
| **Maximum Stress** | 100,000 | 5000m | 200 | **SYSTEM CRASH** | -- | -- |

### Failure Analysis: The 100k Threshold
At the **100,000 agents** threshold with a 5km search radius, the simulation encountered a system failure.

**Technical Diagnosis:**
* **Memory Saturation:** The combination of a massive spatial graph (5km radius) and the pre-calculation of paths for 100,000 agents exceeded the available physical RAM. 
* **OOM (Out Of Memory) Event:** The silence from the terminal and subsequent crash indicate an OS-level intervention (OOM Killer) during the "Pathfinding Initialization" phase.
* **Geospatial Complexity:** Doubling the radius from 2.5km to 5km quadruples the search area ($A = \pi r^2$), leading to an exponential increase in graph nodes and memory overhead.

**Conclusion:** The current architecture is optimized for high-performance stability up to **~75,000 concurrent agents**. To scale beyond this limit, the next engineering step would involve implementing **Dynamic Path Loading** or **Spatial Chunking** to reduce the initial memory footprint.

## 6. Installation & Setup

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
