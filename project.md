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
stateDiagram-
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
