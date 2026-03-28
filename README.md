<<<<<<< HEAD
# FTGSO (paper adaptation) — Simulation + Local Prototype

This project adapts ideas from **“Self-healing and optimal fault tolerant routing in wireless sensor networks using genetical swarm optimization” (Computer Networks, 2022)** to **normal computers/services**.

## Paper → this repo mapping (high level)

- **Sensor Node (SN)** → **Service instance** (a worker process)
- **Cluster / Cluster Head (CH)** → **Group / Coordinator** (logical grouping; a selected instance can act as coordinator)
- **Base Station (BS)** → **Controller** (simulation/prototype router that makes routing decisions)

### Multi-objective selection (Paper §3.3.2)
Paper objectives:
- proximity, communication cost, residual energy, coverage

In this repo we use analogs:
- **proximity** → predicted latency
- **communication cost** → network penalty (jitter/loss proxy) or cross-group penalty
- **residual energy** → capacity headroom (CPU/mem/queue)
- **coverage** → serve-ability (readiness, low error rate, available concurrency)

### GSO optimizer (Paper §3.2.2, Eq. 16–17)
- We implement PSO + GA operators to search for a routing choice/policy.

### Fault detection & self-healing (Paper §3.3.4–§3.3.6)
- Detect persistently low-fitness instances/groups.
- Self-heal by removing them from routing and “waking up” via a restart after cooldown.

## Quickstart

Create a venv and run the simulator:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m ftgso_sim.sim.run
```

Local prototype demo (single machine, multiple processes) will be added later:

```bash
python3 -m ftgso_sim.prototype.demo
```

=======
# FTGSO (paper adaptation) — Simulation + Local Prototype

This project adapts ideas from **“Self-healing and optimal fault tolerant routing in wireless sensor networks using genetical swarm optimization” (Computer Networks, 2022)** to **normal computers/services**.

## Paper → this repo mapping (high level)

- **Sensor Node (SN)** → **Service instance** (a worker process)
- **Cluster / Cluster Head (CH)** → **Group / Coordinator** (logical grouping; a selected instance can act as coordinator)
- **Base Station (BS)** → **Controller** (simulation/prototype router that makes routing decisions)

### Multi-objective selection (Paper §3.3.2)
Paper objectives:
- proximity, communication cost, residual energy, coverage

In this repo we use analogs:
- **proximity** → predicted latency
- **communication cost** → network penalty (jitter/loss proxy) or cross-group penalty
- **residual energy** → capacity headroom (CPU/mem/queue)
- **coverage** → serve-ability (readiness, low error rate, available concurrency)

### GSO optimizer (Paper §3.2.2, Eq. 16–17)
- We implement PSO + GA operators to search for a routing choice/policy.

### Fault detection & self-healing (Paper §3.3.4–§3.3.6)
- Detect persistently low-fitness instances/groups.
- Self-heal by removing them from routing and “waking up” via a restart after cooldown.

## Quickstart

Create a venv and run the simulator:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m ftgso_sim.sim.run
```

Local prototype demo (single machine, multiple processes) will be added later:

```bash
python3 -m ftgso_sim.prototype.demo
```

>>>>>>> ekta-simulation
