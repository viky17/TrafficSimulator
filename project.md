### **UML Class Diagram**

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
    participant Client
    participant Manager
    participant Utils
    participant Agent

    Client->>Manager: step()
    Manager->>Manager: increment tick_attuale

    Manager->>Utils: GetEdgeOccupancy(allAgents)
    Utils-->>Manager: return current_congestion (Dictionary)
    end
