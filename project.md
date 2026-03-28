### *UML Class Diagram*

```mermaid
classDiagram
    direction TB

    class Manager{
        +id: String
        +coords: List
        +distRange: integer
        +status: String
        +agents: List
        +raodsGeometry: List
        +spawn_errors: integer
        +tick_attuale: integer
        +current_congestion: integer
        -gDrive: Graph
        -gWalk: Graph
        +buildWorld(barriers)
        +populationWorld(vehicles, pedestrian, timeOfDay)
        +step() List
    }
    class Agent{
        +id: String
        +type: String
        +active: Boolean
        +stuckTicks: integer
        +ticksAlive: integer
        +isHeavy: Boolean
        -path: List
        -pathCoords: List
        -currentNode: Node
        -currentStep: integer
        +step()
    }
    class Utils{
        <<Utility>>
        +ComputePathWorker(args: Tuple) Dictionary
        +IsGreenLight(u: integer, v: integer, tick: integer) Boolean
        +GetEdgeOccupancy(allAgents: List) Dictionary
        +ValidateMovement(agent, graph, occupancy, tick) Boolean
        +ApplyBarriers(graph, barriers: integer)
        +PreProcessing(graph, timeOfDay: String) Tuple
    }

    Manager "1" *-- "*" Agent : manages
    Manager ..> Utils : uses for calculations
    Agent ..> Utils : validated by
```
The Manager class runs the whole simulation, handling everything from building the world to keeping track of each tick. It grabs two road graphs from OSMnx (the OpenStreetMap library): gDrive for cars and gWalk for pedestrians. To keep things light for the Client, it pulls just the coordinates from these graphs—this way, the Client can render maps fast without having to load the full graph. 

Agents are the different entities managed by the Manager. Each agent follows a path found by Dijkstra’s algorithm, but they also need the actual coordinates (pathCoords) of that route to move around the world. The isHeavy attribute marks whether an agent, like a truck, puts more strain on traffic. This detail matters when you want to figure out how congested a given road is during GetEdgeOccupancy, since heavy agents add more load. The stuckTicks counter goes up whenever the Manager can’t let an agent move, tracking how long it spends blocked. 

The Utils class is packed with the math and logic the Manager needs. ComputePathWorker fetches map data and figures out the shortest routes using Dijkstra’s algorithm, and if a road is blocked, the Manager flags it. isGreenLight handles how traffic lights switch depending on the simulation tick. ValidateMovement steps in to stop an agent if its next road is packed already. GetEdgeOccupancy checks how many vehicles are on each piece of road, bumping up the count for heavy vehicles so it’s easy to spot upcoming traffic jams. ApplyBarriers takes out entire road connections, which you’d do for things like construction closures. PreProcessing nudges traffic toward busy spots in the morning and out to the edges later, using timeOfDay to set this morning/evening shift in behavior.

### *Sequence Diagram*

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Manager
    participant Utils
    participant Agent

    Note over Client, Manager: Initialization Phase
    Client->>Manager: buildWorld(barriers)
    Manager->>Utils: ApplyBarriers(graph, barriers)
    Manager->>Utils: PreProcessing(graph)
    Manager-->>Client: status = "WORLD_READY"

    Note over Client, Manager: Population Phase
    Client->>Manager: populationWorld(counts)
    Manager->>Utils: ComputePathWorker(tasks)
    Utils-->>Manager: return paths
    Manager->>Agent: Create Instances
    Manager-->>Client: status = "POPULATED"

    Note over Client, Manager: Simulation Loop
    Client->>Manager: step()
    Manager->>Utils: GetEdgeOccupancy(allAgents)
    
    loop For each active Agent
        Manager->>Utils: ValidateMovement(agent, occupancy)
        alt isValid is True
            Manager->>Agent: step()
            Agent->>Agent: update currentStep
        else Movement Blocked
            Manager->>Agent: increment stuckTicks
        end
    end
    Manager-->>Client: return data_tick
```
*Initialization Phase*: Everything starts with the buildWorld command sent by the client. The manager does not execute geographic calculations directly but delegates some responsibilities to the Utils class. Subsequently, the ApplyBarriers function is called to cut the graph connections where the user has inserted obstacles, and then the PreProcessing function is called to set the road weights based on the chosen time slot (morning/evening). Only when the graphs are ready does the Manager confirm to the Client that the engine is in the "WORLD_READY" state.

*Population Phase:* This is the most CPU-intensive phase. The Manager once again delegates this work to the Utils class, more specifically to the ComputePathWorker function. Here, Dijkstra's algorithm is exploited to calculate the shortest paths across thousands of nodes simultaneously.
Not all paths are guaranteed; if the barriers inserted by the Client have isolated an area, an agent might not be able to identify a valid path and consequently would not be created. The system detects this and increments the spawn_errors counter, avoiding a simulation crash.
Only after obtaining all valid paths does the Manager instantiate the Agent objects, assigning a path to each. When every actor is ready, the Manager updates its status to "POPULATED", signaling to the Client that the simulation is ready to be executed.

*Simulation Loop:* At the beginning of each Tick, the Manager takes a "snapshot" of the global state of the roads via GetEdgeOccupancy. This step serves to calculate how many vehicles occupy each road segment at that precise moment.
For each agent still active, the Manager queries the ValidateMovement function; here, the system verifies if the traffic light is green and if the destination road still has physical capacity to host the agent in question. If the function gives a positive result, the agent executes a step in the simulation via the step() method. If the movement is denied, the agent remains stationary, and in this case, the stuckTicks counter is incremented—a variable used for bottlenecks where agents accumulate the most delay.
Once all agents have been processed, the Manager packs the results into the data_tick, containing the updated positions and the congestion status, allowing the Client to update the graphical visualization in real time.
### *State Diagram*

```mermaid
stateDiagram-v2
    direction TB

    [*] --> CREATED : Manager() Initialization
    
    state CREATED {
        direction TB
        State_1: Waiting for buildWorld()
        State_2: Running ApplyBarriers()
        State_3: Running PreProcessing()
        
        State_1 --> State_2
        State_2 --> State_3
    }

    CREATED --> WORLD_READY : status = "WORLD_READY"
    
    state WORLD_READY {
        direction TB
        State_4: Waiting for populationWorld()
        State_5: Running ComputePathWorker()
        State_6: Initializing Agent Instances
        
        State_4 --> State_5
        State_5 --> State_6
    }

    WORLD_READY --> POPULATED : status = "POPULATED"

    state RUNNING {
        direction TB
        Step_Update: tick_attuale++
        
        Traffic_Scan: GetEdgeOccupancy(allAgents)
        
        Validation: ValidateMovement(agent, occupancy)
        
        Movement: Agent.step() OR stuckTicks++
        
        Step_Update --> Traffic_Scan
        Traffic_Scan --> Validation
        Validation --> Movement
        Movement --> Step_Update : Next Tick Loop
    }

    POPULATED --> RUNNING : status = "RUNNING" (first step call)
    
    RUNNING --> FINISHED : All Agents active = False
    FINISHED --> [*]
