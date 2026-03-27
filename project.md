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
    note for Manager "status: contains simulation state.<br/>current_congestion: current traffic situation.<br/>raodsGeometry: list of coordinates."

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
    note for Agent "stuckTicks: counts ticks the agent remained stuck.<br/>isHeavy: if True the agent occupies more road space.<br/>currentStep: points to current position in path list."

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

### *State Diagram*

```mermaid
stateDiagram-v2
    direction TB

    [*] --> CREATED : Instance initialized
    
    state CREATED {
        direction TB
        [*] --> gDrive_None
        gDrive_None --> ApplyBarriers : buildWorld(barriers)
        ApplyBarriers --> PreProcessing : Weights & Capacity
        Note right of PreProcessing : Calculates road capacity<br/>and timeOfDay weights.
    }

    CREATED --> WORLD_READY : status = "WORLD_READY"

    state WORLD_READY {
        direction TB
        [*] --> agents_Empty
        agents_Empty --> ComputePathWorker : populationWorld(counts)
        Note left of ComputePathWorker : Parallel Dijkstra paths<br/>Increments spawn_errors
        ComputePathWorker --> agents_Created : Agent instances
    }

    WORLD_READY --> POPULATED : status = "POPULATED"

    state RUNNING {
        direction TB
        [*] --> GetEdgeOccupancy : step() every 5 ticks
        
        state ValidateMovement_Logic {
            direction TB
            [*] --> IsGreenLight
            IsGreenLight --> CapacityCheck : if Green
            CapacityCheck --> MovementResult : if space exists
        }
        
        GetEdgeOccupancy --> ValidateMovement_Logic
        MovementResult --> GetEdgeOccupancy : tick_attuale++
    }

    POPULATED --> RUNNING : status = "RUNNING"
    
    RUNNING --> FINISHED : all agents inactive
    FINISHED --> [*]
