
```mermaid
classDiagram
   

    class Manager{
        +id: String
        +status: String
        -gDrive: Graph
        -gWalk: Graph
        +agents: List
        +buildWorld(barriers)
        +populationWorld(vehicles,pedestrian,tiomOfDay)
        +step()
    }

    class Agent{
        +id: String
        +type: String
        +active: bool
        +stuckTicks: int
        +ticksAlive: int
        +isHeavy: bool
        -path: List
        -pathCoords: List
        -currentNode: Node
        -currentStep: int
        +step()
    }

    Manager "1" *-- "*" Agent
