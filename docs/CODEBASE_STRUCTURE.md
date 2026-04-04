# FTGSO Project: Complete Codebase Structure & Organization

##  Directory Tree

```
CN_project/
│
├──  README.md                          # Project overview & quick start
├──  requirements.txt                   # Dependencies: numpy, matplotlib, pandas, seaborn
├──  PROJECT_ANALYSIS.md                # Detailed 7-stage implementation explanation
├──  QUICK_REFERENCE.md                 # Fast lookup: Paper → Code mapping
├──  DATA_FLOW.md                       # Complete data flow & system architecture
├──  CODEBASE_STRUCTURE.md              # This file
│
├──  ftgso_sim/                         # Main simulation package
│   │
│   ├──  __init__.py                    # Package marker
│   │
│   ├── ┌─ LAYER 1: RESOURCE MODELING ─┐
│   ├──  model.py                       # Data structures (Instance, Metrics, ResourceTier)
│   │
│   ├── ┌─ LAYER 2: CLUSTERING ─────────┐
│   ├──  cluster.py                     # Cluster formation & master node election
│   │
│   ├── ┌─ LAYER 3: FAULT DETECTION ────┐
│   ├──  fault.py                       # Fault classification (hard/soft/transient)
│   ├──  gossip.py                      # Distributed fault dissemination protocol
│   │
│   ├── ┌─ LAYER 4: OPTIMIZATION ───────┐
│   ├──  fitness.py                     # Multi-objective fitness calculation (5 objectives)
│   ├──  routing_path.py                # Enhanced GA for routing paths with backups
│   │
│   ├──  optimizer/                     # Hybrid PSO + GA optimization
│   │   ├──  __init__.py
│   │   ├──  pso.py                     # Particle Swarm Optimization (exploration)
│   │   ├──  ga.py                      # Genetic Algorithm (refinement)
│   │   └──  gso.py                     # Hybrid GSO = PSO→GA pipeline
│   │
│   ├── ┌─ LAYER 5: SELF-HEALING ───────┐
│   ├──  healing.py                     # 3-layer self-healing mechanism
│   │
│   ├── ┌─ LAYER 6: METRICS ────────────┐
│   ├──  metrics.py                     # Performance tracking (TCR, JDR, JTT, MTTH)
│   │
│   ├── ┌─ LAYER 7: BASELINES ──────────┐
│   ├──  baselines.py                   # Baseline policies & Kubernetes comparison
│   │
│   ├──  sim/                           # Simulation engines
│   │   ├──  __init__.py
│   │   ├──  step2.py                   # CORE SIMULATION LOOP (all 7 stages)
│   │   ├──  run.py                     # Entry point for default simulation
│   │   ├──  sweep.py                   # Parameter sweep runner (Stage 8)
│   │   └──  ablation.py                # Ablation study runner (Stage 8)
│   │
│   └──  prototype/                     # Local multiprocess prototype demo
│       ├──  __init__.py
│       ├──  demo.py                    # RUNNABLE DEMO (multiprocess implementation)
│       ├──  router.py                  # Worker pool manager & routing
│       ├──  worker.py                  # Simulated worker process
│       └──  healer.py                  # Self-healing interface
│
├──  outputs/                           # Main simulation results
│   └──  summary.csv                    # Results from step2.py
│
├──  sweep_outputs/                     # Parameter sweep results
│   ├──  runs.csv
│   ├──  summary_agg.csv
│   └──  summary_by_scenario.csv
│
├──  ablation_outputs/                  # Ablation study results
│   └──  ablation_summary.csv
│
└──  visual_simulation.ipynb            # JUPYTER NOTEBOOK with 25 cells of visualization

```

---

## Architecture Layers

### **Layer 1: Data Models** (`model.py`)
```python
ResourceTier (Enum)
  ├── TIER_1_NORMAL (4 cores, 8GB)
  ├── TIER_2_INTERMEDIATE (8 cores, 16GB)
  └── TIER_3_ADVANCED (16 cores, 32GB)

InstanceMetrics (Dataclass)
  ├── latency_ms: float          # Network response time (1-500ms)
  ├── net_penalty: float         # Quality penalty (0-1)
  ├── headroom: float            # Available capacity (replaces "energy %" from WSN)
  └── serveability: float        # Service functionality (0-1)

EnhancedInstanceMetrics (Dataclass)
  ├── cpu_cores, memory_gb, disk_io_mbps
  ├── network_latency_ms, bandwidth_mbps
  └── cpu_utilization, memory_utilization, io_utilization %

Instance (Dataclass)
  ├── instance_id: int
  ├── group_id: int
  ├── tier: ResourceTier
  ├── metrics: InstanceMetrics
  ├── enhanced_metrics: EnhancedInstanceMetrics
  ├── is_healthy: bool
  └── is_cluster_head: bool
```

**32 LOC • Dependencies: dataclasses, Enum • Used by: ALL layers**

---

### **Layer 2: Clustering** (`cluster.py`)
```python
ClusterInfo (Dataclass)
  ├── cluster_id: int
  ├── instance_ids: List[int]    # Members
  ├── cluster_head_id: int       # Master node
  ├── fitness_score: float       # Multi-objective score
  └── resources_profile: str     # "low"/"balanced"/"high"

ClusterManager (Class)
  ├── form_clusters(instances)
  │   └── Groups by group_id, elects head per group
  ├── _elect_cluster_head(group_instances)
  │   └── Returns max fitness instance index
  └── _classify_resources(instances)
      └── Classifies tier distribution
```

**110 LOC • Dependencies: model, fitness, numpy • Used by: step2, prototype**

---

### **Layer 3: Fault & Gossip** 
#### **fault.py:**
```python
FaultType (Enum)
  ├── HARD_FAULT       # Unreachable/crashed
  ├── SOFT_FAULT       # Overloaded CPU/Memory/IO
  ├── TRANSIENT_FAULT  # Temporary spike
  └── HEALTHY

FaultEvent (Dataclass)
  ├── instance_id: int
  ├── fault_type: FaultType
  ├── severity: float          # 0.0-1.0
  ├── timestamp: int           # Step number
  └── is_persistent: bool

FaultDetector (Class)
  └── detect_fault(instance_id, is_reachable, metrics, ts)
      → Returns FaultEvent or None
```

**120 LOC • Dependencies: dataclasses, Enum**

#### **gossip.py:**
```python
AnomalyMessage (Dataclass)
  ├── source_cluster_id: int
  ├── instance_id: int
  ├── fault_type: FaultType
  ├── severity: float
  ├── timestamp: int
  └── hop_count: int

GossipProtocol (Class)
  ├── broadcast_fault(fault_event, source_cluster_id)
  │   └── Creates & queues message
  ├── propagate_step()
  │   └── Forwards messages (3-hop limit, 70% dissemination)
  └── register_cluster(cluster_id, instance_ids)
```

**140 LOC • Dependencies: fault, numpy**

---

### **Layer 4: Fitness & Optimization**
#### **fitness.py:**
```python
FitnessWeights (Dataclass)
  ├── proximity: 0.25          # Latency weight
  ├── communication_cost: 0.15 # Penalty weight
  ├── residual_energy: 0.25    # Headroom weight
  ├── coverage: 0.20           # Serveability weight
  └── fault_history: 0.15      # Fault penalty weight

FitnessBounds (Dataclass)
  └── Min/max ranges for normalization

fitness_score(metrics, weights, fault_penalty)
  → Returns: Σ wi · normalize(fi) ∈ [0, 1]
```

**90 LOC • Dependencies: model**

#### **optimizer/pso.py: Particle Swarm Optimization**
```python
pso_optimize_1d(objective_values, n_particles=16, n_iters=20)
  │
  ├── Initialize 16 particles in index space [0, n_instances)
  ├── FOR 20 iterations:
  │   └── Update velocity: v = w*v + c1*r1*(pbest-x) + c2*r2*(gbest-x)
  │       (w=0.6, c1/c2=1.4, standard PSO equation)
  │   └── Update position: x = clip(x+v, 0, n-1)
  │   └── Track personal best & global best
  └── RETURN gbest (best position found)
```

**70 LOC • Dependencies: numpy • Equation: Standard PSO**

#### **optimizer/ga.py: Genetic Algorithm**
```python
ga_refine_1d(objective_values, seed_index, pop_size=20, gen=15)
  │
  ├── Initialize population with seed (PSO result)
  ├── FOR 15 generations:
  │   ├── Evaluate fitness
  │   ├── SELECT: Tournament (top 50% as elites)
  │   ├── CROSSOVER: child = (parent1 + parent2) / 2
  │   ├── MUTATE: child += randint(-2, 3) with prob=0.2
  │   └── ELITISM: Keep best 1
  └── RETURN best(population)
```

**110 LOC • Dependencies: numpy • Operators: Tournament + Arithm.Crossover + Gaussian Mutation**

#### **optimizer/gso.py: Hybrid Pipeline**
```python
select_candidate_gso(objective_values)
  │
  ├── STEP 1: PSO Exploration
  │   ├── pso_pos = pso_optimize_1d(...)
  │   └── Explores index space quickly
  │
  ├── STEP 2: Extract Seed
  │   ├── seed_idx = round(pso_pos)
  │   └── Best candidate so far
  │
  └── STEP 3: GA Refinement
      ├── best_idx = ga_refine_1d(..., seed=seed_idx)
      └── Fine-tune around seed
      
  → RETURN best_idx (final selected instance)
```

**50 LOC • Dependencies: pso, ga • Pattern: Explore then Refine**

---

### **Layer 5: Self-Healing** (`healing.py`)
```python
HealingLayer (Enum)
  ├── LAYER_1_LINK_REWORDING       # From paper (drain)
  ├── LAYER_2_SERVICE_MIGRATION    # Enhancement (migrate)
  └── LAYER_3_PREDICTIVE_SHEDDING  # Enhancement (shed)

HealingAction (Audit Trail)
  ├── layer: HealingLayer
  ├── instance_id: int
  ├── timestamp: int
  └── effectiveness: float

SelfHealingManager (Class)
  │
  ├── initialize(n_instances)
  │   └── Allocates healing state
  │
  ├── apply_layer1_link_rewording(faulty_ids)
  │   ├── DRAIN: Mark faulty, start 8-step cooldown
  │   ├── Prevents routing to unhealthy servers
  │   └── Effectiveness: HIGH (~70%)
  │
  ├── apply_layer2_service_migration(instance_id, targets, load)
  │   ├── MIGRATE: Move workload from faulty → healthy
  │   └── Effectiveness: MEDIUM
  │
  ├── apply_layer3_predictive_shedding()
  │   ├── SHED: Reduce load if utilization > 80%
  │   └── Prevent cascading failures
  │
  ├── progress_cooldown() # Decrement timers
  │
  └── apply_recovery_boost(rejoin_mask)
      ├── Boost metrics after recovery
      ├── serveability += 0.35, latency ×0.75
      └── Re-join as healthy
```

**180 LOC • Dependencies: numpy**

---

### **Layer 6: Metrics** (`metrics.py`)
```python
PerformanceMetrics (Dataclass)
  ├── tcr: float          # Task Completion Rate = completed/submitted
  ├── jdr: float          # Job Drop Rate = dropped/submitted
  ├── jtt_ms: float       # Job Turnaround Time (mean latency)
  ├── mtth: float         # Mean Time To Heal (steps)
  ├── pdr: float          # Packet Delivery Rate (alias for TCR)
  ├── plr: float          # Packet Loss Rate (alias for JDR)
  └── e2e_latency_ms: float  # End-to-end latency (alias for JTT)

MetricsCollector (Class)
  │
  ├── record_task_submission()      # Count submitted tasks
  ├── record_task_completion(lat)   # Count + accumulate latency
  ├── record_task_drop()            # Count dropped tasks
  ├── record_fault_detected(step)   # Track fault detection time
  ├── record_fault_resolved(step)   # Track resolution time
  │
  └── Compute Methods:
      ├── compute_tcr() → completed / submitted
      ├── compute_jdr() → dropped / submitted
      ├── compute_jtt() → mean(latencies)
      └── compute_mtth() → mean(resolution_times)
```

**140 LOC • Dependencies: dataclasses, numpy**

---

### **Layer 7: Baselines** (`baselines.py`)
```python
BaselinePolicy (Enum)
  ├── ROUND_ROBIN         # Sequential cycling (baseline)
  ├── PSO_ONLY            # PSO without GA (ablation)
  ├── GA_ONLY             # GA without PSO (ablation)
  ├── KUBERNETES          # K8s-inspired (modern baseline)
  └── SC_FTGSO            # Full system (our solution)

KubernetesInspiredRouter (Class)
  ├── register_instance(instance_id, cpu_req, mem_req, limits)
  ├── liveness_probe()    # Check responsiveness
  └── select_ready_instance()  # Round-robin ready pods

SCFTGSOComparison (Class)
  └── integrate_all_components()
      └── Combines all 7 stages
```

**120 LOC • Dependencies: numpy, enum**

---

### **Simulation Engines**

#### **sim/step2.py: CORE SIMULATION LOOP**
```python
SimConfig (Dataclass)
  ├── n_instances, n_groups, n_steps
  ├── request_rate, seed
  ├── fault_thresholds & probabilities
  └── enable_healing flag

_initialize_instances() → Instance[]
  └── Stage 1: Create random instances + metrics

_simulate_one_policy(instances, policy, config) → dict
  │
  └── FOR each step in range(n_steps):
      │
      ├── [1] Fault Injection (Stage 3 setup)
      │   ├── degrade_prob = 0.02: latency ×1.3, headroom -0.15
      │   ├── fail_prob = 0.01:    healthy=False, serveability=0.0
      │   └── recovery_prob = 0.02: recovery boost
      │
      ├── [2] Cluster Formation (Stage 2)
      │   └── form_clusters(instances)
      │
      ├── [3] Fault Detection (Stage 3)
      │   ├── FaultDetector.detect_fault(each instance)
      │   └── GossipProtocol.propagate_step()
      │
      ├── [4] Calculate Fitness (Stage 4 setup)
      │   └── fitness[i] = fitness_score(metrics[i])
      │
      ├── [5] Route Request (Stage 4 main)
      │   ├── IF policy == ROUND_ROBIN: pick next
      │   ├── ELIF policy == GSO: select_candidate_gso(fitness)
      │   ├── ELIF policy == FITNESS: argmax(fitness)
      │   ├── ELIF policy == LEAST_LATENCY: argmin(latency)
      │   ├── ELIF policy == LEAST_LOADED: argmin(utilization)
      │   └── Generate request + simulate latency
      │
      ├── [6] Apply Healing (Stage 5)
      │   ├── IF enable_healing:
      │   │   ├── healing.apply_layer1_link_rewording(faulty)
      │   │   ├── healing.apply_layer2_service_migration(...)
      │   │   ├── healing.apply_layer3_predictive_shedding()
      │   │   └── healing.apply_recovery_boost(rejoin_mask)
      │
      ├── [7] Collect Metrics (Stage 6)
      │   ├── metrics.record_task_submission()
      │   ├── Simulate request completion
      │   └── metrics.record_task_completion(latency)
      │
      └── Store step metrics → time_series
      
  → RETURN {policy: tcr, jdr, jtt_ms, mtth}
```

**450+ LOC • Dependencies: ALL layers • Entry Point: Used by sweep.py, ablation.py**

#### **sim/run.py:**
```python
main()
  └── Calls _simulate_one_policy() with default params
      → Outputs to outputs/summary.csv
```

**30 LOC**

#### **sim/sweep.py: Parameter Sweep Study**
```python
main(args):
  │
  ├── FOR each n_instances in [10, 20, 30]:
  │   └── FOR each request_rate in [0.5, 1.0, 2.0]:
  │       └── FOR each policy in [ALL 5]:
  │           └── _simulate_one_policy()
  │               └── Collect results
  │
  └── Aggregate & export:
      ├── sweep_outputs/runs.csv            (all runs)
      ├── sweep_outputs/summary_agg.csv     (mean by policy)
      └── sweep_outputs/summary_by_scenario.csv (per scenario)
```

**200 LOC • CLI: --n-instances, --n-groups, --n-steps, --request-rate, --seed, --output-dir**

#### **sim/ablation.py: Ablation Study**
```python
main():
  │
  └── Test 4 system variants:
      ├── score_only:        Fitness-based, no healing
      ├── gso_only:          GSO-based, no healing
      ├── healing_only:      Round-robin + healing
      └── full_ftgso_healing: GSO + healing
      
  → Outputs: ablation_outputs/ablation_summary.csv
           + individual metric plots
```

**250 LOC • Used by: researchers for ablation analysis**

---

### **Local Prototype** (Multiprocess Implementation)

#### **prototype/demo.py: RUNNABLE DEMO**
```python
main(args):
  │
  ├── LocalRouter.start()
  │   └── Spawns n_worker processes
  │
  ├── FOR each request:
  │   ├── router.pick_worker(policy)  # GSO or fitness
  │   └── router.route(job)           # Send to worker
  │
  ├── Periodically:
  │   ├── drain_results()             # Check completions
  │   └── heal_once()                 # Restart dead workers
  │
  └── Report metrics (PDR, PLR, E2E)
```

**120 LOC • CLI: --workers, --requests, --mode (fitness|gso), --crash-prob**
**Run:** `python3 -m ftgso_sim.prototype.demo`

#### **prototype/router.py:**
```python
WorkerHandle (Class)
  ├── worker_id, in_queue, process object
  └── metrics tracking

LocalRouter (Class)
  ├── start(n_workers)              # Spawn processes
  ├── pick_worker(policy, scores)  # Select using fitness/GSO
  ├── route(job_id, input_data)    # Send to worker
  ├── drain_results()              # Get completions
  ├── restart_dead()               # Restart crashed
  └── shutdown()                   # Clean up
```

**200 LOC • Dependencies: fitness, model, optimizer/gso, multiprocessing**

#### **prototype/worker.py:**
```python
worker_main(worker_id, in_queue, out_queue):
  │
  └── LOOP:
      ├── Receive job_id, submit_timestamp
      ├── Simulate work: sleep(latency * jitter)
      ├── Random crash: if random() < crash_prob
      └── Send back: (job_id, worker_id, latency, success)
```

**80 LOC • Pure multiprocessing worker**

#### **prototype/healer.py:**
```python
heal_once(router):
  └── Wrapper: router.restart_dead()
```

**15 LOC • Interface layer**

---

### **Visualization**

#### **visual_simulation.ipynb: Jupyter Notebook**
```
25 cells organized as:

[1]  Markdown:  Title
[2]  Code:      Import modules
[3]  Code:      Load outputs/summary.csv
[4]  Markdown:  Stage 1-2 visualization
[5]  Code:      Plot tier distribution + cluster topology
[6]  Code:      Plot cluster head fitness
[7]  Markdown:  Stage 3-5 analysis
[8]  Code:      Plot fault detection + healing
[9]  Code:      Calculate metrics
[10] Markdown:  Stage 6 metrics
[11] Code:      Plot TCR, JDR, JTT by policy
[12] Code:      Plot ablation study results
[13] Markdown:  Stage 7 comparison
[14] Code:      Policy comparison bar charts
[15] Code:      Scenario analysis
[16] Markdown:  Summary
[17] Code:      Generate summary table
[18] Code:      Export visual_simulation_summary.csv
[19] Markdown:  Conclusions
[20] Code:      Final validation checks

Generates: 10+ plots covering all 7 stages
Exports:   visual_simulation_summary.csv
```

**600+ LOC • Dependencies: pandas, matplotlib, numpy, csv**

---

## Code Statistics

| Component | LOC | Purpose |
|-----------|-----|---------|
| **model.py** | 32 | Data structures |
| **cluster.py** | 110 | Stage 2 clustering |
| **fault.py** | 120 | Stage 3 fault detection |
| **gossip.py** | 140 | Stage 3 fault sharing |
| **fitness.py** | 90 | Stage 4 fitness |
| **optimizer/pso.py** | 70 | Stage 4 PSO |
| **optimizer/ga.py** | 110 | Stage 4 GA |
| **optimizer/gso.py** | 50 | Stage 4 GSO |
| **healing.py** | 180 | Stage 5 healing |
| **metrics.py** | 140 | Stage 6 metrics |
| **baselines.py** | 120 | Stage 7 baselines |
| **sim/step2.py** | 450+ | Core loop |
| **sim/sweep.py** | 200 | Parameter sweep |
| **sim/ablation.py** | 250 | Ablation study |
| **prototype/** | 415 | Local demo |
| **visual_simulation.ipynb** | 600+ | Visualization |
| **TOTAL** | **~3300** | Complete system |

---

## Dependency Graph

```
                         (No dependencies)
                                |
                            model.py
                               /|\
                              / | \
                             /  |  \
                   fitness.py   |   fault.py
                        /\      |      \
                       /  \     |       \
                      /    ga.py|    gossip.py
                     /          |
                   gso.py    cluster.py
                  /   \           \
                 /     \           \
            step2.py  routing_path.py
            /    \         
        sweep.py  \
                   \
              healing.py (independent)
              
              metrics.py (independent)
              
              baselines.py (independent)
              
          ↓
          
    visual_simulation.ipynb
    (reads CSV outputs)
```

**Key Insight:** Layered architecture with clear separation of concerns!
- **Layer 0:** model.py (foundation)
- **Layer 1:** fitness.py + fault.py + metrics.py (parallel)
- **Layer 2:** pso.py + ga.py + gso.py + gossip.py + healpy.py (specialized)
- **Layer 3:** step2.py + baselines.py + cluster.py (integration)
- **Layer 4:** sweep.py + ablation.py + prototype/ (workflows)
- **Layer 5:** visual_simulation.ipynb (visualization)

---

## How to Run Each Component

### **1. Core Simulation (default config)**
```bash
python3 -m ftgso_sim.sim.run
→ Outputs: outputs/summary.csv
```

### **2. Parameter Sweep (8 different configs)**
```bash
python3 -m ftgso_sim.sim.sweep \
  --n-instances 20 \
  --n-steps 200 \
  --request-rate 1.0 \
  --seed 42 \
  --output-dir sweep_outputs
→ Outputs: sweep_outputs/{runs,summary_agg,summary_by_scenario}.csv
```

### **3. Ablation Study (4 system variants)**
```bash
python3 -m ftgso_sim.sim.ablation
→ Outputs: ablation_outputs/ablation_summary.csv + plots
```

### **4. Local Prototype (multiprocess demo)**
```bash
python3 -m ftgso_sim.prototype.demo \
  --workers 8 \
  --requests 100 \
  --mode gso \
  --crash-prob 0.02
→ Live output: Request routing, crash/recovery, final metrics
```

### **5. Visualization (Jupyter)**
```bash
jupyter notebook visual_simulation.ipynb
→ Loads CSV files and generates 10+ plots
→ Exports: visual_simulation_summary.csv
```

---

## Summary

**What:** Complete FTGSO simulation framework with:
-  7 operational stages (resource modeling → baselines)
-  Hybrid PSO+GA optimization
-  Multi-layer self-healing
-  Comprehensive metrics & comparison

**How Organized:**
- **ftgso_sim/model.py** → Data layer
- **ftgso_sim/{cluster,fault,gossip,healing,metrics,baselines}.py** → Feature layers
- **ftgso_sim/optimizer/{pso,ga,gso}.py** → Optimization subsystem
- **ftgso_sim/sim/{step2,sweep,ablation}.py** → Simulation engines
- **ftgso_sim/prototype/{demo,router,worker,healer}.py** → Local implementation
- **visual_simulation.ipynb** → Visualization & analysis
- **Documentation** → PROJECT_ANALYSIS.md, QUICK_REFERENCE.md, DATA_FLOW.md

**Statistics:**
- ~3300 lines of Python code
- 16 Python modules + 1 Jupyter notebook
- Layered dependency graph (no cycles)
- Multiple execution modes (simulation, prototype, sweep, ablation, visualization)

