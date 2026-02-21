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

## 3. The Engineering Challenge: Overcoming the Parallelism Paradox

The primary challenge of this project was scaling the simulation to 10,000+ agents. In Python, moving from a single-threaded script to a high-performance engine revealed significant architectural bottlenecks that required a deep dive into system resource management.

### Identifying the Bottleneck: The "Pickling" Overhead
Initial attempts to use standard multiprocessing led to a "Parallelism Paradox": adding more CPU cores actually made the simulation slower (jumping from 4 minutes to 25 minutes for 25,000 agents). 



Through profiling, I identified that the culprit was **Serialization (Pickling)**. Python was attempting to copy the entire multi-megabyte city graph to every single process for every single agent. The system was spending 90% of its time on Inter-Process Communication (IPC) and only 10% on actual pathfinding.

### Engineering the Solution
To resolve this, I re-engineered the engine’s data flow using three core strategies:

1. **Shared Memory via Global Initializers:** I implemented a "Shared Memory" approach. Instead of passing the graph as an argument, I used a global initializer that loads the map into each CPU core's memory only once at startup. This reduced the task payload from a heavy graph object to a lightweight tuple of coordinates.
2. **Memory-Optimized Agent Architecture:** I decoupled the `Agent` objects from the `NetworkX` graph. By pre-calculating and storing only the necessary coordinate paths, I achieved a stable RAM footprint of **~370MB for 25,000 agents**, preventing memory swapping and crashes.
3. **Temporal Congestion Sampling:** I optimized the simulation loop by sampling road occupancy every 5 ticks instead of every tick. This "Temporal Sampling" provided a massive CPU relief without affecting the macroscopic accuracy of the traffic flow.
