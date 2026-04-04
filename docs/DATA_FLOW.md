# FTGSO Implementation: Complete Data Flow & System Architecture

## System Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FTGSO SERVER NETWORK SIMULATION                          │
└─────────────────────────────────────────────────────────────────────────────┘


╔═══════════════════════════════════════════════════════════════════════════════╗
║                          STAGE 1: INITIALIZATION                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    Input: Configuration
    ├─ n_instances: 20 servers
    ├─ n_clusters: 4 groups
    ├─ n_steps: 200 simulation steps
    └─ Resource distribution (Tier 1-3)
                    ↓
    Process: Create Instances
    ├─ Assign resource tier (CPU cores, RAM)
    ├─ Initialize metrics (latency, penalty, headroom, serveability)
    └─ Create group assignments
                    ↓
    Output: instances[] 
    └─ List of Instance objects with metrics


╔═══════════════════════════════════════════════════════════════════════════════╗
║                   STAGE 2: CLUSTER FORMATION                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    Input: instances[]
                    ↓
    Process: ClusterManager.form_clusters()
    ├─ Group instances by group_id
    ├─ For each group:
    │  ├─ Calculate fitness_score for each instance
    │  │  = w1·f(latency) + w2·f(penalty) + w3·f(headroom) + w4·f(serveability)
    │  ├─ Select highest fitness as cluster head
    │  └─ Create ClusterInfo
    └─ Store cluster topology
                    ↓
    Output: clusters{cluster_id → ClusterInfo}
    └─ cluster_head_id, member_ids, fitness_score, resource_profile


╔═══════════════════════════════════════════════════════════════════════════════╗
║              STAGE 3: FAULT DETECTION & GOSSIP (Per Step)                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    FOR EACH SIMULATION STEP:
    
    Input: Current metrics (latency, penalty, headroom, serveability)
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ Fault Injection (Probabilistic)                              │
    ├─────────────────────────────────────────────────────────────┤
    │ degrade_prob = 0.02  (degradation)                          │
    │  ├─ latency *= 1.3                                          │
    │  ├─ penalty += 0.1                                          │
    │  ├─ headroom -= 0.15                                        │
    │  └─ serveability -= 0.12                                    │
    │                                                              │
    │ fail_prob = 0.01  (hard failure)                            │
    │  ├─ healthy[i] = False                                      │
    │  ├─ serveability[i] = 0.0                                   │
    │  └─ headroom[i] -= 0.2                                      │
    │                                                              │
    │ passive_recovery_prob = 0.02  (environmental recovery)      │
    │  ├─ healthy[i] = True                                       │
    │  ├─ serveability[i] += 0.3                                  │
    │  ├─ headroom[i] += 0.25                                     │
    │  ├─ latency[i] *= 0.9                                       │
    │  └─ penalty[i] -= 0.05                                      │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ Fault Detection                                              │
    ├─────────────────────────────────────────────────────────────┤
    │ for each instance i:                                        │
    │   FaultDetector.detect_fault(i, is_reachable, metrics...)   │
    │                                                              │
    │   IF NOT reachable OR serveability < 0.0:                  │
    │     → FaultType.HARD_FAULT                                  │
    │                                                              │
    │   ELSE IF max(cpu_util, mem_util, io_util) > 0.5:          │
    │     → FaultType.SOFT_FAULT                                  │
    │                                                              │
    │   ELSE IF transient_spike_detected():                       │
    │     → FaultType.TRANSIENT_FAULT                             │
    │                                                              │
    │   Store in fault_history[i]                                 │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ Gossip Protocol: Disseminate Fault Info                     │
    ├─────────────────────────────────────────────────────────────┤
    │ GossipProtocol.broadcast_fault(fault_event, cluster_id)    │
    │  ├─ Create AnomalyMessage                                   │
    │  ├─ Add to message_queue                                    │
    │  └─ Mark as seen to avoid duplicates                        │
    │                                                              │
    │ GossipProtocol.propagate_step()                             │
    │  ├─ For each message in queue:                              │
    │  │  ├─ If hop_count < max_hops AND random() < diss_prob:   │
    │  │  │  └─ Forward to other clusters (hop_count++)          │
    │  │  └─ Else: discard                                        │
    │  └─ Remove old messages (> 10 steps)                        │
    └─────────────────────────────────────────────────────────────┘


╔═══════════════════════════════════════════════════════════════════════════════╗
║              STAGE 4: MULTI-OBJECTIVE OPTIMIZATION                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    Input: Current metrics, fault_history for all instances
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ Calculate Fitness Scores                                     │
    ├─────────────────────────────────────────────────────────────┤
    │ for each instance i:                                        │
    │                                                              │
    │   f1 = normalize_minimize(latency_ms, 1.0, 500.0)          │
    │   f2 = normalize_minimize(net_penalty, 0.0, 1.0)           │
    │   f3 = normalize_maximize(headroom, 0.0, 1.0)              │
    │   f4 = normalize_maximize(serveability, 0.0, 1.0)          │
    │   f5 = clamp(1.0 - fault_penalty)                          │
    │                                                              │
    │   fitness[i] = 0.25·f1 + 0.15·f2 + 0.25·f3 +               │
    │                0.20·f4 + 0.15·f5                            │
    │                                                              │
    │   Result: fitness[i] ∈ [0, 1] (higher is better)           │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ GSO (Genetical Swarm Optimization): Select Best Instance    │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │ STEP 1: PSO Phase (Exploration)                             │
    │ ─────────────────────────────────                           │
    │ def pso_optimize_1d(fitness_values, n_particles=16):        │
    │   for each particle p in particles:                         │
    │     p.position ∈ [0, n_instances)  # Index space            │
    │     p.velocity ∈ ℝ                                          │
    │     p.pbest = initial position                              │
    │                                                              │
    │   for iteration in range(n_iterations=20):                  │
    │     for each particle p:                                    │
    │       # Update velocity                                     │
    │       v_new = 0.6 * v_old +                                 │
    │               1.4 * rand() * (pbest - pos) +                │
    │               1.4 * rand() * (gbest - pos)                  │
    │       # Update position                                     │
    │       pos_new = clip(pos + v_new, 0, n-1)                   │
    │       # Update personal best                                │
    │       if fitness(pos_new) > fitness(pbest):                 │
    │         pbest = pos_new                                     │
    │       # Update global best                                  │
    │       gbest = max_fitness_position                          │
    │                                                              │
    │   return gbest  # Best position found                       │
    │                                                              │
    │ Output: pso_best_index (promising region)                   │
    │                                                              │
    │ STEP 2: GA Phase (Refinement)                               │
    │ ─────────────────────────────────                           │
    │ def ga_refine_1d(fitness_values, seed_index):               │
    │   population = random_indices(n_instances)                  │
    │   population[0] = seed_index  # PSO result                  │
    │                                                              │
    │   for generation in range(15):                              │
    │     # Evaluate fitness                                      │
    │     scores = [fitness[idx] for idx in population]           │
    │                                                              │
    │     # Select top 50%                                        │
    │     elites = population[top_50_by_fitness]                  │
    │                                                              │
    │     # Generate new population                               │
    │     new_pop = [elite_best]  # Elitism                       │
    │     for i in range(1, pop_size):                            │
    │       # Crossover: average parents                          │
    │       p1, p2 = random_select(elites, 2)                     │
    │       child = (p1 + p2) / 2                                 │
    │       # Mutation: small perturbation                        │
    │       if random() < 0.2:                                    │
    │         child += randint(-2, 3)                             │
    │       new_pop.append(clip(child, 0, n-1))                   │
    │     population = new_pop                                    │
    │                                                              │
    │   return best(population)  # Refined solution               │
    │                                                              │
    │ STEP 3: Hybrid GSO                                          │
    │ ──────────────────                                          │
    │ best_instance = select_candidate_gso(fitness_values)        │
    │   pso_pos = pso_optimize_1d(fitness_values)  # Explore     │
    │   seed_idx = round(pso_pos)   # Extract best               │
    │   best_idx = ga_refine_1d(fitness_values, seed_idx)  # Ref │
    │   return best_idx              # Final selection            │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    Output: selected_instance_id (best for current conditions)


╔═══════════════════════════════════════════════════════════════════════════════╗
║                    STAGE 5: THREE-LAYER SELF-HEALING                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    Input: fitness_scores[] for all instances
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ Identify Faulty Instances                                    │
    ├─────────────────────────────────────────────────────────────┤
    │ detected_faulty[i] = True  if:                               │
    │   ├─ fitness[i] < 0.3 (low fitness threshold)               │
    │   └─ Sustained for >= 5 consecutive steps                   │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ LAYER 1: Link Rewording (Drain from routing)                │
    ├─────────────────────────────────────────────────────────────┤
    │ newly_drained = detected_faulty & ~already_drained          │
    │ for i in newly_drained:                                     │
    │   drained[i] = True                                         │
    │   cooldown[i] = 8 steps  # Start timer                      │
    │   record_healing_action(LAYER_1, i)                         │
    │                                                              │
    │ Effect: Remove instance from request routing                │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ LAYER 2: Service Migration (Move workload)                  │
    ├─────────────────────────────────────────────────────────────┤
    │ for i in newly_drained:                                     │
    │   healthy_targets = get_healthy_instances()                 │
    │   load_to_migrate = get_current_load(i)                     │
    │   migrated = migrate_load(i, healthy_targets, load)         │
    │   record_healing_action(LAYER_2, i, effectiveness=migrated) │
    │                                                              │
    │ Effect: Distribute load to healthy servers                  │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ LAYER 3: Predictive Load Shedding                            │
    ├─────────────────────────────────────────────────────────────┤
    │ should_shed[i] = (utilization[i] > 0.8) &                  │
    │                  (serveability[i] < 0.4)                    │
    │ for i in should_shed:                                       │
    │   reduce_incoming_load(i, by=50%)                           │
    │   record_healing_action(LAYER_3, i)                         │
    │                                                              │
    │ Effect: Prevent overload and cascading failures             │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ Cooldown Management                                          │
    ├─────────────────────────────────────────────────────────────┤
    │ for i in drained:                                           │
    │   cooldown[i] -= 1                                          │
    │   if cooldown[i] == 0:                                      │
    │     rejoin_mask[i] = True  # Ready to rejoin               │
    └─────────────────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ Recovery & Rejoin (After Cooldown)                          │
    ├─────────────────────────────────────────────────────────────┤
    │ for i in rejoin_mask:                                       │
    │   # Apply recovery boost                                    │
    │   serveability[i] += 0.35                                   │
    │   headroom[i] += 0.25                                       │
    │   latency[i] *= 0.75  # 25% improvement                     │
    │   penalty[i] -= 0.10                                        │
    │   drained[i] = False                                        │
    │   healthy[i] = True                                         │
    │                                                              │
    │ Effect: Instance back in service with improved state        │
    └─────────────────────────────────────────────────────────────┘


╔═══════════════════════════════════════════════════════════════════════════════╗
║                   STAGE 6: PERFORMANCE MONITORING                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    Track for Each Request/Step:
    ├─ Task submitted
    │   ├─ request_id, timestamp, source
    │   └─ requested_resources
    │
    ├─ Task routed
    │   ├─ selected_instance (from GSO)
    │   ├─ routing_path (primary + backups)
    │   └─ routing_timestamp
    │
    └─ Task completed or failed
        ├─ completion_timestamp
        ├─ actual_latency_ms
        ├─ success/failure
        └─ failure_reason

    Aggregate Metrics (Each Step & Final):
    ├─ TCR = completed_tasks / submitted_tasks
    ├─ JDR = dropped_tasks / submitted_tasks
    ├─ JTT = mean(latencies_of_completed_tasks)
    ├─ MTTH = mean(recovery_times)
    ├─ PDR = TCR (packet delivery rate)
    ├─ PLR = JDR (packet loss rate)
    └─ E2E = JTT (end-to-end latency)


╔═══════════════════════════════════════════════════════════════════════════════╗
║                   STAGE 7: POLICY COMPARISON                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    Run Simulation With Different Policies:
    ├─ Round-Robin:    Random instance selection
    ├─ PSO-Only:       GSO without GA refinement
    ├─ GA-Only:        GSO without PSO exploration
    ├─ Kubernetes:     Readiness probes + resource requests
    └─ SC-FTGSO:       Full system (baseline for comparison)

    Compare Results:
    ├─ TCR (%):       Task completion rate
    ├─ JDR (%):       Job drop rate
    ├─ JTT (ms):      Job turnaround time
    ├─ MTTH (steps):  Mean time to heal
    └─ Winner:        SC-FTGSO expected to outperform all


═══════════════════════════════════════════════════════════════════════════════════════════════════
```

## Key Data Structures

```python
# Core domain model
Instance(
    instance_id: int,
    group_id: int,
    tier: ResourceTier,           # T1, T2, or T3
    metrics: InstanceMetrics(
        latency_ms: float,        # Network latency
        net_penalty: float,       # Quality penalty
        headroom: float,          # Available capacity
        serveability: float,      # Service availability
    ),
    enhanced_metrics: EnhancedInstanceMetrics(
        cpu_cores: int,
        memory_gb: float,
        disk_io_mbps: float,
        network_latency_ms: float,
        bandwidth_mbps: float,
        cpu_utilization: float,
        memory_utilization: float,
        io_utilization: float,
    ),
    is_healthy: bool,
    is_cluster_head: bool,
)

# Cluster topology
ClusterInfo(
    cluster_id: int,
    instance_ids: list,          # Members
    cluster_head_id: int,        # Master node
    fitness_score: float,        # Multi-objective
    resources_profile: str,      # "low"/"balanced"/"high"
)

# Fault information
FaultEvent(
    instance_id: int,
    fault_type: FaultType,       # HARD/SOFT/TRANSIENT
    severity: float,             # 0.0 to 1.0
    timestamp: int,              # Step number
    is_persistent: bool,
)

# Healing action
HealingAction(
    layer: HealingLayer,         # 1/2/3
    instance_id: int,
    timestamp: int,
    effectiveness: float,        # How much it helped
)

# Performance metrics
PerformanceMetrics(
    tcr: float,                  # Task completion rate
    jdr: float,                  # Job drop rate
    jtt_ms: float,               # Job turnaround time
    mtth: float,                 # Mean time to heal
    pdr: float,                  # For compatibility
    plr: float,                  # For compatibility
    e2e_latency_ms: float,       # For compatibility
)
```

## Time Complexity Analysis

```
Per Simulation Step:

Stage 3 (Fault Detection):     O(n_instances)
Stage 3 (Gossip):              O(n_clusters × max_hops)
Stage 4 (Fitness):             O(n_instances)
Stage 4 (PSO):                 O(n_particles × n_iterations × n_instances)
                               = O(16 × 20 × n) = O(320 × n)
Stage 4 (GA):                  O(n_pop × n_generations × n_instances)
                               = O(20 × 15 × n) = O(300 × n)
Stage 5 (Healing):             O(n_instances)
Stage 6 (Metrics):             O(requests)

Total per step: O(n_instances × (620 + 300 + 300))
             = O(n_instances) linear complexity 

For n=20, steps=200:
Total operations: ~200 × 20 × 600 = 2.4M Tractable
```

## Memory Usage

```
Instance storage:     20 instances × 500 bytes = ~10 KB
Cluster storage:      4 clusters × 100 bytes = ~0.4 KB
Fault history:        20 × 10 faults × 200 bytes = ~40 KB
Healing actions:      100 actions × 100 bytes = ~10 KB
Metrics history:      200 steps × 50 bytes = ~10 KB

Total: ~70 KB (negligible)
```

## Execution Flow (Per Step Loop)

```python
for step in range(n_steps):  # 0 to 199
    
    # [1] Fault injection
    degradation_event()
    failure_event()
    recovery_event()
    
    # [2] Fault detection  
    for i in instances:
        detect_fault(i)
        if fault_detected:
            gossip_broadcast(fault)
    
    # [3] Gossip propagation
    gossip_propagate_step()
    
    # [4] Fitness calculation
    for i in instances:
        fitness[i] = calculate_fitness(i)
    
    # [5] GSO selection
    if healthy_instances > 0:
        best_instance = select_candidate_gso(fitness)
    
    # [6] Healing
    faulty = identify_faulty(fitness)
    apply_layer1_link_rewording(faulty)
    apply_layer2_service_migration(faulty)
    apply_layer3_predictive_shedding()
    progress_cooldown_timers()
    rejoin = apply_recovery_boost()
    
    # [7] Load generation & routing
    requests = poisson(request_rate)
    for _ in range(requests):
        route_request_to(best_instance)  # or fallback if unavailable
        record_metric(latency, success)
    
    # [8] Record step metrics
    metrics.update(tcr, jdr, jtt, mtth)

# [9] Final analysis
compute_baseline_comparisons()
generate_visualizations()
```
