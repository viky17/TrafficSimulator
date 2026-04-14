Il passaggio dall'architettura a oggetti (OOP) a quella orientata ai dati (DOD) è stato dettato da una necessità fisica riscontrata durante la fase dei test sulle performance.

## Risultati del test sull'archiettura OOP

| Agenti | Ticks | Tempo Totale (s) | Throughput (Rows/s) | Peak RAM (MB) |
|--------|-------|------------------|----------------------|----------------|
| 100    | 100   | 22.33s           | 242.0                | 292.74         |
| 1.000  | 100   | 62.78s           | 760.0                | 234.62         |
| 5.000  | 200   | 307.41s          | 732.0                | 243.93         |
| 15.000 | 200   | 904.92s          | 678.0                | 296.55         |
| 25.000 | 300   | 1512.07s         | 657.0                | 372.40         |


| Agents | Radius | Ticks | Elapsed_s | Rows_Generated | Throughput (Rows/s) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 30,000 | 1500m | 100 | 258.81s | 1,445,833 | 5,586 |
| 50,000 | 2000m | 100 | 539.71s | 2,796,979 | 5,182 |
| 75,000 | 3000m | 150 | 1317.36s | 5,663,755 | 4,299 |
| 100,000 | 5000m | 200 | **SYSTEM CRASH** | -- | -- |

Il problema principale dell'approccio OOP in Python è la frammentazione della memoria. Ogni istanza di *Agent* è un oggetto allocato in una posizione arbitraria.
Quando la CPU processa una lista di oggetti, deve continuare a recuperare puntatori a indirizzi di memoria distanti. Questo impedisce al processore di utilizzare efficacemente la cache, forzando continui accessi alla RAM. Inoltre il modello OOP richiede alla CPU di saltare da un oggetto all'altro in memoria, riducendo drasticamente il throughput (limitato ~650 righe/s).

Inoltre inizialmente il ciclo di vita era gestito da un ciclo del tipo *for agent in agents: agent.step()*. Il problema è che per ogni iterazione l'interprete deve cercare il metodo step nel dizionario dell'istanza e della classe.
Essendo Python un linguaggio dinamico, controlla costantemente se l'oggetto è ancora quello giusto e se può eseguire quel comando.

Infine un oggetto Python porta con se oltre i suoi dati anche un'enorme quantità di metadati come dizionari interni, puntatori al Garbage Collector e informazioni sui tipi. Questo già nel test con 25.000 agenti ha portato a un occupazioni di memoria pari a 372 MB. Questo porta a un inevitabile crash per *Out of memory* sui 100.000 agenti.

## Passaggio a un archiettura DOD
Il superamento dei limiti strutturali del modello OOP è stato possibile grazie alla transizione verso un paradigma **Data-Oriented**. In questo tipo di archiettura, non si considerano più delle entità "Agente" ma si utilizzando dati grezzi organizzate in struture di memoria contigue.

**Vettorializzazione**: La principale innovazione sta nell'eliminazione dei cicli for Python a favore della vettorializzazione. Sostituendo le istanze di classe con matrici NumPy, il calcolo viene delegato a funzione scritte in **C**, quindi ottimizzate per le archietture delle CPU moderne.
I dati degli agenti sono memorizzati in blocchi di memoria sequenziali, in questo modo la CPU può sfruttare appieno la **Cache L1/L2**, eliminando i tempi superflui causati dai *cache miss* del modello OOP.
Inoltre il processore può ora applicare la stessa istruzione a più dati simultaneamente sfruttando il **Single Instruction Multiple Data** calcolando decine di spostamenti in un unico ciclo di clock.

### Il collo di bottiglia dell'I/O
I test sul nuovo motore vettorializzato hanno rilevato una nuova sfida, ovvero la disparità tra la velocità di calcolo e la velocità di *serializzazione* dei dati. 
Il motore puro, lavora esclusivamente su matrici in RAM, raggiungendo picchi di **150.000** agenti al secondo. In questo caso la CPU è saturata esclusivamente da calcoli matematici SIMD. Quando però il sistema deve comunicare con l'esterno (fase di I/O) deve convertire questi tensori in formati leggibili, come ad esempio il JSON, per le API. Questa operazione riduce il throughput a circa 60.000 agenti/s. A tale scopo l'API del metodo step permette di utilizzare un attributo per specificare se è necessario oppure no ritornare i dati al termine dell'iterazione. In questo modo il client sceglie se necessita di ottenere l'evoluzione delle posizioni degli agenti ad ogni iterazione o se è sufficiente ricevere i dati solo al termine della simulazione.
Di seguito il confronto dei due test:

**Full I/O**:
| Agenti | Ticks | Tempo Totale (s) | Throughput (Rows/s) | Peak RAM (MB) |
|--------|-------|------------------|----------------------|----------------|
| 100    | 100   | 0.37s            | 26.926               | 68.96          |
| 1.000  | 100   | 1.79s            | 55.653               | 69.42          |
| 5.000  | 200   | 16.36s           | 61.121               | 72.29          |
| 15.000 | 200   | 49.23s           | 60.938               | 77.73          |
| 25.000 | 300   | 119.69s          | 62.658               | 82.75          |

**PURE ENGINE**:
| Agenti | Ticks | Tempo Totale (s) | Throughput (Rows/s) | Peak RAM (MB) |
|--------|-------|------------------|----------------------|----------------|
| 100    | 100   | 0.25s            | 38.774               | 68.96          |
| 1.000  | 100   | 0.77s            | 128.633              | 69.42          |
| 5.000  | 200   | 6.67s            | 149.925              | 72.29          |
| 15.000 | 200   | 20.27s           | 148.044              | 77.73          |
| 25.000 | 300   | 50.09s           | 149.718              | 82.75          |

### Popolazione parallella
Nonostante l'efficienza nel movimento, la fase di inizializzazione (il calcolo dei percorsi tramite l'algoritmo di Dijkstra) rimaneva l'operazione a più alto costo computazionale. In Python, il Global Interpreter Lock (GIL) impedisce ai thread di eseguire calcoli CPU-intensive in parallelo, rendendo la generazione di 100.000 percorsi un processo estremamente lento e sequenziale.

Per superare questo limite ho scelto di implementare un sistema di Popolazione Parallela basato su *Multiprocessing*. A differenza dei thread, il multiprocessing lancia processi indipendenti, ognugno con la propia istanza dell'interprete e il proprio spazio di memoria. Questo permette di sfruttare realmente tutti i core della CPU contemporaneamente.
La popolazione totale viene suddivisa in "batch" distribuiti equamente tra i core disponibili. Ogni core calcola i percorsi minimi per il suo sottoinsieme di agenti in totale autonomia.
Una volta terminati i calcoli paralleli, i risultati grezzi vengono raccolti e impacchettati direttamente nelle matrici NumPy pre-allocate. 

Grazie a questa archiettura, il throughput di popolazione rimane stabile anche al crescere del carico, mantenendo una media di **30-35 agenti/s**. Senza questo approccio, il tempo di attesa per popolare scenari metropolitani sarebbe stato proibitivo, portando spesso il sistema al crash dovuto al timeout delle API.

**Test di popolazione senza parallelizzazione**:
| Agenti  | Tempo Popolazione (s) | Throughput Simulazione (Agenti/s) | Latenza Simulazione (s) |
|---------|------------------------|------------------------------------|--------------------------|
| 50.000  | 2512.56*              | 68.196                             | 0.733s                   |
| 100.000 | 5263.15*              | 96.124                             | 1.040s                   |

**Test di popolazione con parallelizzazione**:
| Agenti  | Tempo Popolazione (s) | Throughput Simulazione (Agenti/s) | Latenza Simulazione (s) |
|---------|------------------------|------------------------------------|--------------------------|
| 50.000  | 1504.39               | 149.925                            | 0.333s                   |
| 100.000 | 3255.46               | 150.000                            | 0.666s                   |

### Breaking Point
Per confermare la scalabilità dell'architettura DOD, ho condotto uno stress test finalizzato a individuare il *Breaking Point* fisico del sistema su una workstation dotata di **32 GB di RAM**.
Al fine di isolare le performance del motore di calcolo dai tempi di I/O dovuti al pre-processing tramite l'algoritmo di Dijkstra, ho implementato una tecnica alternativa di popolazione istantanea, in cui vengono allocate istantaneamente le strutture dati vettorializzate in memoria, permettendo di testare il comportamento del sistema con un numero molto grande di entità attive.

**Risultati del test**:
| Agenti Totali | Latenza per Tick | Throughput (Rows/s) | Occupazione RAM | Esito           |
|----------------|------------------|----------------------|------------------|--------------|
| 100.000        | 0.38s            | 263.157              | 34.4%            | PASSED       |
| 500.000        | 1.81s            | 276.243              | 44.2%            | PASSED       |
| 1.000.000      | 3.62s            | 276.243              | 55.8%            | PASSED       |
| 1.500.000      | 5.61s            | 267.379              | 67.4%            | PASSED       |
| 2.000.000      | 7.51s            | 266.311              | 77.6%            | PASSED       |
| 2.500.000      | --               | --                   | --               | MEMORY ERROR |

L'analisi dei risultati mostra che nel nuovo motore di simulazione il limite non è più dato dalla velocità di esecuzione, come avveniva nel modello OOP, ma è dato esclusivamente dalla capacità fisica della memoria.
Fino alla soglia dei **2.000.000 agenti**, il sistema mostra una scalabilità quasi lineare, mantenendo un throughput costante sopra le 260.000 righe processate al secondo. Questo indica che l'architettura è estremamente efficiente nel gestire le risorse e il tempo di calcolo cresce in modo prevedibile rispetto all'aumentare dei dati.

Il fallimento riscontrato a 2.500.000 agenti è dovuto a un limite fisico di indirizzamento della RAM. In un'architettura DOD basata su NumPy, i dati devono essere memorizzati in blocchi di memoria contigui per permettere alla CPU di eseguire istruzioni SIMD.
Per gestire 2.500.000 agenti, il sistema ha tentato di allocare simultaneamente:

  - *node_path_matrix* (int64): ~9.31 GiB
  - *path_matrix* (float32): ~9.31 GiB
  - Strutture di stato e overhead: ~2.5 GiB
    
Sebbene la workstation sia dotata di 32 GB, il sistema operativo non è stato in grado di trovare un blocco di indirizzi unico e contiguo abbastanza grande da ospitare queste matrici, a causa della naturale frammentazione della RAM occupata dai processi in background. Il *Memory Error* è quindi l'intervento di sicurezza del sistema per prevenire un blocco totale dell'hardware (kernel panic).

Il fatto che la latenza per tick rimanga costante (proporzionalmente) fino al limite della RAM suggerisce che l'architettura sta sfruttando la gerarchia della memoria. Organizzando i dati in modo sequenziale, abbiamo minimizzato i cache miss, infatti la CPU trova quasi sempre i dati di cui ha bisogno nei registri veloci (L1/L2), senza dover attendere i tempi di risposta, molto più lenti, della RAM principale.

## Conclusioni
Il passaggio alla nuova architettura Data-Oriented ha permesso di:

  - Aumentare il limite di simulazione (da 75.000 a 2.000.000), su una workstation da 32GB di RAM
  - Garantire un'esecuzione deterministica, infatti il tempo richiesto per un tick è lineare rispetto alla mole di dati
  - Sfruttare le istruzioni Single Instruction Multiple Data del processore, calcolando molte posizioni in un singolo ciclo di clock.
