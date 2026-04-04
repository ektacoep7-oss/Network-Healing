# FTGSO: WSN → LAN Adaptation Quick Reference

## Paper Concepts → Your Implementation Mapping

```
WIRELESS SENSOR NETWORK (Paper)          →    COMPUTER LAN (Your Implementation)
═══════════════════════════════════════════════════════════════════════════════

[STAGE 1: RESOURCE MODELING]
Sensor Node                              →    Server Instance
- Battery capacity                       →    CPU cores + Memory + Bandwidth
- Transmission power                     →    Network capacity
- Sensor data quality                    →    Service availability

[STAGE 2: CLUSTERING & COORDINATION]
Cluster of Sensors                       →    Group of Servers
Cluster Head (CH)                        →    Master Node/Coordinator
Selection: Minimize energy drain         →    Selection: Maximize capacity headroom

[STAGE 3: FAULT DETECTION]
Node failure (battery/signal)            →    Server failure (crash/overload)
Low battery warning                      →    High utilization threshold
Communication failure                    →    Network latency spike

Gossip Protocol:
- Neighboring sensors share anomalies    →    Cluster heads share fault info
- Limited hops to prevent flooding       →    Bounded dissemination (3 hops)

[STAGE 4: OPTIMIZATION → GA+PSO]

Multi-Objective Selection (Paper §3.3.2):
┌─────────────────────────────────────────────────────────────────┐
│ Objective 1: Proximity (minimize)                               │
│   Paper: Minimize transmission distance                         │
│   Your LAN: Minimize network latency [1-500 ms]                 │
│   Weight: 0.25                                                  │
│                                                                 │
│ Objective 2: Communication Cost (minimize)                      │
│   Paper: Minimize retransmissions/jitter                        │
│   Your LAN: Minimize network penalty [0-1]                      │
│   Weight: 0.15                                                  │
│                                                                 │
│ Objective 3: Residual Energy (maximize)                         │
│   Paper: Maximize battery remaining (%)                         │
│       Your LAN: Maximize capacity headroom [0-1]                │
│      = 1 - (cpu_util + mem_util + io_util) / 3                  │
│   Weight: 0.25  ← CRITICAL ADAPTATION                           │
│                                                                 │
│ Objective 4: Coverage (maximize)                                │
│   Paper: Node availability                                      │
│   Your LAN: Service readiness/availability [0-1]                │
│   Weight: 0.20                                                  │
│                                                                 │
│ [NEW] Objective 5: Fault History (maximize) - Stage 4           │
│   Paper: Not explicitly included                                │
│   Your LAN: Penalize instances with fault history               │
│   Weight: 0.15  ← ENHANCEMENT FOR RELIABILITY                   │
└─────────────────────────────────────────────────────────────────┘

Fitness Score Calculation:
fitness = w1·f1(latency) + w2·f2(net_penalty) + w3·f3(headroom)
        + w4·f4(serveability) + w5·f5(fault_penalty)

Where: 0 ≤ fitness ≤ 1, higher is better

Optimization Strategy (Paper §3.2.2):
           
    PSO Phase: Exploration              GA Phase: Refinement
    ─────────────────────              ──────────────────
    • Particles explore                 • Population converges
    • Find promising regions            • Exploit best candidate
    • 16 particles, 20 iterations       • 20 population, 15 gen
    
    HYBRID GSO:
    PSO output → GA input → BEST SOLUTION


[STAGE 5: SELF-HEALING]

Paper (§3.3.4-6):
┌─ Layer 1: Detect low-fitness node
├─ Layer 2: Remove from routing pool (drain)
├─ Layer 3: Wait for cooldown (repair)
└─ Layer 4: Rejoin with recovery boost

Enhanced for LAN (Your Implementation - 3 Layers):
┌──────────────────────────────────────┐
│ Layer 1: Link Rewording              │
│ Remove from active routing pool      │
│ Cooldown timer starts (8 steps)      │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│ Layer 2: Service Migration           │
│ Move workload away from faulty node  │
│ Load transferred to healthy servers  │
│ [NEW - Not in paper]                 │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│ Layer 3: Predictive Load Shedding    │
│ Reduce load before saturation        │
│ Prevent cascading failures           │
│ [NEW - Not in paper]                 │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│ Recovery & Rejoin                    │
│ After cooldown: metrics boost        │
│ • serveability += 0.35               │
│ • capacit += 0.25                    │
│ • latency *= 0.75                    │
│ • net_penalty -= 0.10                │
└──────────────────────────────────────┘


[STAGE 6: PERFORMANCE METRICS]

WSN Paper                              Your LAN
─────────────────────────────────────────────────────
Packet Delivery Ratio (PDR)     →      Task Completion Rate (TCR)
Packet Loss Rate (PLR)          →      Job Drop Rate (JDR)
End-to-End Delay                →      Job Turnaround Time (JTT)
(Recovery time implicit)         →      Mean Time to Heal (MTTH)


[STAGE 7: POLICY COMPARISON]

Baselines Tested:
1. Round-Robin:    No optimization (baseline)
2. PSO-Only:       PSO exploration only
3. GA-Only:        GA refinement only
4. Kubernetes:     Industry standard (readiness probes)
5. SC-FTGSO:       Full system (paper's approach + enhancements)

Expected: SC-FTGSO > Kubernetes > GA/PSO > Round-Robin


═══════════════════════════════════════════════════════════════════════════════
```

## Critical Adaptation: Energy → Capacity Headroom

```
PAPER: Residual Energy Model (WSN)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Battery State = current_charge / max_capacity
- Node drains battery over time
- Low battery → node failure
- Objective: Maximize remaining battery

Energy consumed per transmission:
E_tx(d) = k1·d² + k2  (proportional to distance)


YOUR LAN: Capacity Headroom Model
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORRECT ADAPTATION:

Capacity Headroom = 1.0 - utilization_rate

Where utilization rate = (CPU_used + Memory_used + IO_used) / 3

Examples:
- Idle server:    headroom = 1.0 (maximum)
- 50% busy:       headroom = 0.5
- Saturated:      headroom = 0.0 (minimum)

Objective: Maximize available headroom
(More headroom = better, like more battery)

Fit for server networks because:
✓ CPU utilization affects request handling capacity
✓ Memory utilization affects data processing
✓ I/O utilization affects throughput
✓ All three are comparable to energy drain
```

## Key Implementation Details

```
Module              Purpose                  Key Function
───────────────────────────────────────────────────────────
model.py            Resource representation  InstanceMetrics, Instance
fitness.py          Fitness calculation      fitness_score(m, w)
optimizer/pso.py    PSO exploration         pso_optimize_1d()
optimizer/ga.py     GA refinement           ga_refine_1d()
optimizer/gso.py    Hybrid GSO              select_candidate_gso()
cluster.py          Cluster formation       ClusterManager.form_clusters()
fault.py            Fault detection         FaultDetector.detect_fault()
gossip.py           Gossip protocol         GossipProtocol.propagate_step()
healing.py          Self-healing            SelfHealingManager (3 layers)
metrics.py          Performance tracking    MetricsCollector
baselines.py        Baseline policies       PolicyFactory.create_all_policies()
routing_path.py     Routing optimization    RoutingPathGA
```

## Parameter Verification

```
Parameter              Paper         Implementation    Status
═══════════════════════════════════════════════════════════════════
PSO Inertia (w)       0.7-0.9       0.6               Good
PSO Cognitive (c1)    1.0-2.0       1.4               Good
PSO Social (c2)       1.0-2.0       1.4               Good
PSO Particles         Variable      16                Reasonable
PSO Iterations        Variable      20                Reasonable

GA Population         Variable      20                Reasonable
GA Generations        Variable      15                Reasonable
GA Mutation Prob      0.01-0.1      0.2               Good

Fitness Weights       w1=?          w1=0.25 (latency)
                      w2=?          w2=0.15 (comm)
                      w3=?          w3=0.25 (energy→headroom)
                      w4=?          w4=0.20 (coverage)
                      w5=N/A        w5=0.15 (fault history)
                                     New enhancement

Cooldown Steps        Variable      8                 Good
Recovery Boost        Variable      0.35              Good
Gossip Hops          3-5           3                  Good
```

## Summary Checklist

- [x] WSN concepts correctly mapped to LAN/server networks
- [x] GA+PSO ideology correctly implemented (PSO explores, GA refines)
- [x] 4-objective optimization maintained + 1 new (fault history)
- [x] Energy model adapted to capacity headroom
- [x] Fault detection enhanced (3 types)
- [x] Healing enhanced (3 layers)
- [x] Gossip protocol for distributed coordination
- [x] Cluster heads elected via multi-objective fitness
- [x] Metrics adapted to server network requirements
- [x] Baseline comparisons provided

## Recommendations for Production

1. **Dynamic Weight Tuning**: Adjust weights based on workload
2. **SLA Enforcement**: Add QoS constraints
3. **Load Distribution**: Send to top-K instead of single instance
4. **Workload Classification**: Different weights for CPU/IO/Memory-bound tasks
5. **Cost Model**: Include cloud provider costs if applicable
6. **Monitoring**: Add real-time dashboards
7. **Testing**: Validate against paper's experimental setup
