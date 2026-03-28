"""
SC-FTGSO Network Simulator — Animation (Enhanced UI)
Run with: streamlit run animated_simulation.py
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import plotly.graph_objects as go
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional

from ftgso_sim.model import Instance, InstanceMetrics, ResourceTier
from ftgso_sim.fitness import FitnessWeights, fitness_score
from ftgso_sim.cluster import ClusterManager, ClusterInfo
from ftgso_sim.fault import FaultDetector, FaultEvent, FaultType
from ftgso_sim.gossip import GossipProtocol
from ftgso_sim.healing import SelfHealingManager, HealingLayer
from ftgso_sim.metrics import MetricsCollector
from ftgso_sim.optimizer import select_candidate_gso

st.set_page_config(
    page_title="SC-FTGSO · Network Simulator",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Hide ALL Streamlit chrome (header bar, keyboard icon, hamburger, footer) ──
st.markdown("""
<style>
#MainMenu                              { visibility:hidden!important; display:none!important; }
header[data-testid="stHeader"]         { visibility:hidden!important; display:none!important; height:0!important; min-height:0!important; }
div[data-testid="stHeader"]            { visibility:hidden!important; display:none!important; height:0!important; min-height:0!important; }
div[data-testid="stToolbar"]           { visibility:hidden!important; display:none!important; }
div[data-testid="stDecoration"]        { visibility:hidden!important; display:none!important; }
div[data-testid="stStatusWidget"]      { display:none!important; }
.stDeployButton                        { display:none!important; }
footer                                 { visibility:hidden!important; display:none!important; }
section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] { display:none!important; }
</style>
""", unsafe_allow_html=True)

# ── Color palette — pure white everywhere ──────────────────────────────────────
NC = dict(
    healthy   = "#2563eb",
    faulty    = "#e53935",
    healing   = "#f59e0b",
    master    = "#059669",
    drained   = "#7c3aed",
    packet    = "#16a34a",
    edge_in   = "rgba(100,116,139,0.20)",
    edge_bb   = "rgba(99,102,241,0.35)",
    plot_bg   = "#ffffff",   # pure white plot area
    paper_bg  = "#ffffff",   # pure white paper
)

SPEED_OPTIONS = {
    "Slow  (200ms)": 200,
    "Normal (100ms)": 100,
    "Fast (50ms)":  50,
    "Turbo (20ms)":  20,
}

# ── Global CSS — pure white on every surface ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── Hide Streamlit top header & toolbar completely ── */
div[data-testid="stHeader"],
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
#MainMenu,
header[data-testid="stHeader"],
footer,
.stDeployButton,
div[data-testid="stStatusWidget"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
}

/* ── Remove top padding left by hidden header ── */
.main .block-container {
    padding-top: 1rem !important;
}

/* ── Root reset — white everywhere ── */
html, body,
[class*="css"],
.stApp,
.stApp > div,
.main,
.block-container,
section[data-testid="stMain"],
div[data-testid="stAppViewContainer"] {
    background-color: #ffffff !important;
    font-family: 'DM Sans', system-ui, sans-serif !important;
    color: #111110 !important;
}

/* ── Sidebar — white ── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] .block-container {
    background-color: #ffffff !important;
    border-right: 1px solid #ebebea !important;
}
section[data-testid="stSidebar"] * {
    color: #111110 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Main container ── */
.main .block-container {
    padding-top: 1.25rem !important;
    max-width: 100% !important;
    background: #ffffff !important;
}

/* ── Sidebar header ── */
.sb-title {
    font-size: 15px;
    font-weight: 600;
    color: #111110 !important;
    padding: 20px 4px 2px;
    letter-spacing: -0.02em;
}
.sb-sub {
    font-size: 12px;
    color: #9b9992 !important;
    padding: 0 4px 16px;
    border-bottom: 1px solid #ebebea;
    margin-bottom: 4px;
}

/* ── Sidebar control labels ── */
.ctrl-label {
    font-size: 11px;
    font-weight: 600;
    color: #9b9992 !important;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 18px 0 5px 0;
    display: block;
}

/* ── Streamlit slider — white bg ── */
div[data-testid="stSlider"] > div {
    background: transparent !important;
}
div[data-testid="stSlider"] * {
    background-color: transparent !important;
}

/* ── Primary button ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #2563eb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 11px 0 !important;
    width: 100% !important;
    margin-top: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    letter-spacing: -0.01em !important;
    transition: background 0.15s ease !important;
    box-shadow: 0 1px 3px rgba(37,99,235,0.25) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
    box-shadow: 0 3px 8px rgba(37,99,235,0.30) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:active {
    background: #1e40af !important;
    transform: scale(0.98) !important;
}

/* ── Metric cards ── */
div[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #ebebea !important;
    border-radius: 10px !important;
    padding: 14px 16px !important;
}
div[data-testid="stMetric"] label {
    font-size: 10.5px !important;
    font-weight: 600 !important;
    color: #9b9992 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 26px !important;
    font-weight: 600 !important;
    color: #111110 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.15 !important;
}

/* ── Info block ── */
div[data-testid="stInfo"],
div[data-testid="stAlert"] {
    background: #f4f7ff !important;
    border: 1px solid #c7d8ff !important;
    border-left: 3px solid #2563eb !important;
    border-radius: 8px !important;
    color: #111110 !important;
    font-size: 13.5px !important;
}

/* ── Spinner ── */
div[data-testid="stSpinner"] {
    background: #ffffff !important;
}

/* ── Plotly chart containers ── */
div[data-testid="stPlotlyChart"],
div[data-testid="stPlotlyChart"] > div,
div[data-testid="stPlotlyChart"] iframe {
    background: #ffffff !important;
}

/* ── Event log ── */
.ev-log {
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 11.5px;
    line-height: 1.85;
    background: #ffffff;
    border: 1px solid #ebebea;
    border-radius: 8px;
    padding: 12px 14px;
    max-height: 220px;
    overflow-y: auto;
    color: #6b6a65;
}
.ev-log::-webkit-scrollbar { width: 3px; }
.ev-log::-webkit-scrollbar-thumb { background: #d3d1c7; border-radius: 4px; }
.ev-fault  { color: #dc2626; font-weight: 500; }
.ev-heal   { color: #d97706; font-weight: 500; }
.ev-packet { color: #16a34a; }
.ev-info   { color: #b4b2a9; }

/* ── Cluster info box ── */
.cluster-box {
    background: #ffffff;
    border: 1px solid #ebebea;
    border-radius: 8px;
    padding: 12px 14px;
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 11.5px;
    line-height: 2.0;
    color: #6b6a65;
}

/* ── Legend table ── */
.leg-table { width: 100%; border-collapse: collapse; }
.leg-table td { padding: 7px 5px; vertical-align: middle; }
.leg-table tr:not(:last-child) td { border-bottom: 1px solid #f4f3f0; }
.leg-swatch { width: 11px; height: 11px; border-radius: 50%; display: inline-block; vertical-align: middle; flex-shrink: 0; }
.leg-name { font-size: 12.5px; font-weight: 500; color: #111110; }
.leg-desc { font-size: 11px; color: #9b9992; margin-top: 1px; }

/* ── Section header ── */
.sec-head {
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9b9992;
    margin: 0 0 10px 0;
    padding-bottom: 7px;
    border-bottom: 1px solid #ebebea;
}

/* ── Page header ── */
.page-header {
    padding: 18px 0 16px 0;
    border-bottom: 1px solid #ebebea;
    margin-bottom: 22px;
    background: #ffffff;
}
.page-title {
    font-size: 24px;
    font-weight: 600;
    color: #111110;
    letter-spacing: -0.03em;
    line-height: 1.2;
}
.page-sub {
    font-size: 13.5px;
    color: #6b6a65;
    margin-top: 5px;
    font-weight: 400;
}

/* ── Stage pills ── */
.stage-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
    background: #f0f4ff;
    color: #2563eb;
    border: 1px solid #c7d8ff;
    margin: 4px 2px 0;
    letter-spacing: -0.005em;
}

/* ── Divider ── */
.hdivider {
    border: none;
    border-top: 1px solid #ebebea;
    margin: 14px 0;
}

/* ── Algo box ── */
.algo-box {
    background: #ffffff;
    border: 1px solid #ebebea;
    border-radius: 8px;
    padding: 12px 14px;
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 11.5px;
    line-height: 1.9;
    color: #6b6a65;
}
</style>
""", unsafe_allow_html=True)


@dataclass
class AnimSimConfig:
    n_instances: int = 50
    n_groups: int = 5
    seed: int = 42
    degrade_prob: float = 0.01
    fail_prob: float = 0.008
    passive_recover_prob: float = 0.01
    request_rate: float = 20.0
    low_fitness_threshold: float = 0.30
    low_fitness_window: int = 5
    heal_cooldown_steps: int = 6
    heal_recovery_boost: float = 0.45
    pso_weight_tune_interval: int = 75
    pso_weight_conservatism: float = 0.8
    positions: Optional[np.ndarray] = None


@dataclass
class FrameSnapshot:
    step: int
    healthy: np.ndarray
    serveability: np.ndarray
    headroom: np.ndarray
    latency_ms: np.ndarray
    scores: np.ndarray
    detected_faulty: np.ndarray
    drained: np.ndarray
    cluster_heads: List[int]
    packets: List[tuple]
    pdr: float
    plr: float
    e2e_ms: float
    total_delivered: int
    total_dropped: int
    event_log: List[str]
    clusters: Dict[int, "ClusterInfo"]


def _pso_tune_weights(latency, net_penalty, headroom, serveability, fault_counts, rng,
                      conservatism=0.8, base_weights=None):
    n = len(latency)
    if n == 0: return FitnessWeights()
    if base_weights is None: base_weights = FitnessWeights()
    def evaluate_weights(w):
        ws = np.clip(w, 0.05, 0.5).copy(); ws[4] = max(0.12, ws[4]); ws = ws / ws.sum()
        fw = FitnessWeights(proximity=float(ws[0]), communication_cost=float(ws[1]),
                            residual_energy=float(ws[2]), coverage=float(ws[3]), fault_history=float(ws[4]))
        total = sum(fitness_score(InstanceMetrics(latency_ms=float(latency[i]), net_penalty=float(net_penalty[i]),
                                                   headroom=float(headroom[i]), serveability=float(serveability[i])),
                                   w=fw, fault_penalty=float(min(1.0, fault_counts[i]/10.0))) for i in range(n))
        return total / n
    n_particles = 12
    pos = rng.uniform(0.1, 0.35, size=(n_particles, 5)); vel = rng.normal(0.0, 0.03, size=(n_particles, 5))
    pbest = pos.copy(); pbest_score = np.array([evaluate_weights(pos[i]) for i in range(n_particles)])
    gbest = pbest[int(np.argmax(pbest_score))].copy()
    for _ in range(15):
        r1 = rng.random((n_particles, 5)); r2 = rng.random((n_particles, 5))
        vel = 0.5*vel + 1.2*r1*(pbest-pos) + 1.2*r2*(gbest-pos); pos = np.clip(pos+vel, 0.05, 0.35)
        cur = np.array([evaluate_weights(pos[i]) for i in range(n_particles)]); improved = cur > pbest_score
        pbest_score[improved] = cur[improved]; pbest[improved] = pos[improved]
        gbest = pbest[int(np.argmax(pbest_score))].copy()
    ws = np.clip(gbest, 0.08, 0.35); ws[4] = max(0.15, ws[4]); ws = ws / ws.sum()
    tuned = FitnessWeights(proximity=float(ws[0]), communication_cost=float(ws[1]),
                           residual_energy=float(ws[2]), coverage=float(ws[3]), fault_history=float(ws[4]))
    return FitnessWeights(
        proximity=conservatism*base_weights.proximity+(1-conservatism)*tuned.proximity,
        communication_cost=conservatism*base_weights.communication_cost+(1-conservatism)*tuned.communication_cost,
        residual_energy=conservatism*base_weights.residual_energy+(1-conservatism)*tuned.residual_energy,
        coverage=conservatism*base_weights.coverage+(1-conservatism)*tuned.coverage,
        fault_history=conservatism*base_weights.fault_history+(1-conservatism)*tuned.fault_history)


class SCFTGSOAnimSimulator:
    def __init__(self, cfg: AnimSimConfig):
        self.cfg = cfg; self.rng = np.random.default_rng(cfg.seed)
        self.pso_rng = np.random.default_rng(cfg.seed+777_777); self.n = cfg.n_instances
        self.instances = self._initialize_instances()
        self.positions = cfg.positions if cfg.positions is not None else self._compute_positions()
        self.latency      = np.array([x.metrics.latency_ms  for x in self.instances], dtype=float)
        self.net_penalty  = np.array([x.metrics.net_penalty  for x in self.instances], dtype=float)
        self.headroom     = np.array([x.metrics.headroom     for x in self.instances], dtype=float)
        self.serveability = np.array([x.metrics.serveability for x in self.instances], dtype=float)
        self.healthy      = np.ones(self.n, dtype=bool)
        self.fault_counts = np.zeros(self.n, dtype=int)
        self.low_streak   = np.zeros(self.n, dtype=int)
        self.detected_faulty = np.zeros(self.n, dtype=bool)
        self.scores       = np.zeros(self.n, dtype=float)
        self.weights = FitnessWeights(); self.current_weights = FitnessWeights()
        self.cluster_mgr = ClusterManager(n_clusters=cfg.n_groups, weights=self.weights)
        self.cluster_mgr.form_clusters(self.instances, self.rng)
        self.fault_detector = FaultDetector(hard_fault_threshold=0.0, soft_fault_threshold=0.5, transient_window=3)
        self.gossip = GossipProtocol(max_hops=2, dissemination_prob=0.85)
        for cid, info in self.cluster_mgr.clusters.items(): self.gossip.register_cluster(cid, info.instance_ids)
        self.healer = SelfHealingManager(cooldown_steps=cfg.heal_cooldown_steps, recovery_boost=cfg.heal_recovery_boost,
                                         migration_threshold=0.35, shed_threshold=0.15)
        self.healer.initialize(self.n)
        self.collector = MetricsCollector()
        self._active_packets: List[dict] = []; self._next_pid = 0; self.rr_idx = 0
        self.event_log: List[str] = []; self.step = 0
        self._pdr_history: List[float] = []; self._fault_history: List[int] = []; self._healing_history: List[int] = []

    def _initialize_instances(self):
        tiers = [ResourceTier.TIER_1_NORMAL, ResourceTier.TIER_2_INTERMEDIATE, ResourceTier.TIER_3_ADVANCED]
        instances = []
        for i in range(self.n):
            group_id = int(i % self.cfg.n_groups); tier = tiers[self.rng.integers(0, len(tiers))]
            m = InstanceMetrics(latency_ms=float(self.rng.uniform(5.0,200.0)), net_penalty=float(self.rng.uniform(0.0,0.3)),
                                headroom=float(self.rng.uniform(0.2,1.0)), serveability=float(self.rng.uniform(0.5,1.0)))
            instances.append(Instance(instance_id=i, group_id=group_id, tier=tier, metrics=m))
        return instances

    def _compute_positions(self):
        pos = np.zeros((self.n, 2))
        for i in range(self.n):
            g = i % self.cfg.n_groups; ca = 2*np.pi*g/self.cfg.n_groups
            gx, gy = np.cos(ca)*3.2, np.sin(ca)*3.2
            ni = i // self.cfg.n_groups; na = 2*np.pi*ni/max(1, self.n//self.cfg.n_groups)
            pos[i,0] = gx + np.cos(na)*0.8; pos[i,1] = gy + np.sin(na)*0.8
        return pos

    def _log(self, tag, msg):
        prefix = {"fault":"[FAULT]","heal":"[HEAL] ","pkt":"[PKT]  "}.get(tag,"[INFO] ")
        self.event_log.append(f"{self.step:04d}  {prefix}  {msg}")
        if len(self.event_log) > 120: self.event_log.pop(0)

    def _get_cluster_heads(self): return [info.cluster_head_id for info in self.cluster_mgr.clusters.values()]

    def tick(self) -> FrameSnapshot:
        self.step += 1; cfg = self.cfg; n = self.n
        degrade_mask = self.healthy & (self.rng.random(n) < cfg.degrade_prob)
        fail_mask    = self.healthy & (self.rng.random(n) < cfg.fail_prob)
        self.latency[degrade_mask]      = np.clip(self.latency[degrade_mask]*1.35, 5.0, 500.0)
        self.net_penalty[degrade_mask]  = np.clip(self.net_penalty[degrade_mask]+0.08, 0.0, 1.0)
        self.headroom[degrade_mask]     = np.clip(self.headroom[degrade_mask]-0.12, 0.0, 1.0)
        self.serveability[degrade_mask] = np.clip(self.serveability[degrade_mask]-0.10, 0.0, 1.0)
        self.healthy[fail_mask] = False; self.serveability[fail_mask] = 0.0
        self.headroom[fail_mask] = np.clip(self.headroom[fail_mask]-0.2, 0.0, 1.0)
        self.fault_counts[fail_mask] += 1
        for i in np.where(fail_mask)[0]: self._log("fault", f"Node {i} (cluster {self.instances[i].group_id}) failed")
        recover_mask = (~self.healthy) & (self.rng.random(n) < cfg.passive_recover_prob)
        self.healthy[recover_mask] = True
        self.serveability[recover_mask] = np.clip(self.serveability[recover_mask]+0.25, 0.0, 1.0)
        self.headroom[recover_mask]     = np.clip(self.headroom[recover_mask]+0.20, 0.0, 1.0)
        self.latency[recover_mask]      = np.clip(self.latency[recover_mask]*0.9, 5.0, 500.0)
        self.net_penalty[recover_mask]  = np.clip(self.net_penalty[recover_mask]-0.05, 0.0, 1.0)
        if self.step > 0 and self.step % cfg.pso_weight_tune_interval == 0:
            self.current_weights = _pso_tune_weights(self.latency, self.net_penalty, self.headroom,
                self.serveability, self.fault_counts, self.pso_rng,
                conservatism=cfg.pso_weight_conservatism, base_weights=self.weights)
            self._log("info", f"Step {self.step}: PSO re-tuned weights (Stage 4)")
        for i in range(n):
            if self.healthy[i]:
                fp = float(min(1.0, self.fault_counts[i]/10.0))
                self.scores[i] = fitness_score(
                    InstanceMetrics(latency_ms=float(self.latency[i]), net_penalty=float(self.net_penalty[i]),
                                    headroom=float(self.headroom[i]), serveability=float(self.serveability[i])),
                    w=self.current_weights, fault_penalty=fp)
            else: self.scores[i] = 0.0
        for i in range(n):
            self.fault_detector.detect_fault(instance_id=i, is_reachable=bool(self.healthy[i]),
                serveability=float(self.serveability[i]), cpu_util=float(1.0-self.headroom[i]),
                mem_util=float(self.net_penalty[i]), io_util=0.0, timestamp=self.step)
            if (not self.healthy[i]) or (self.scores[i] < cfg.low_fitness_threshold):
                self.low_streak[i] += 1
                if self.low_streak[i] >= cfg.low_fitness_window and not self.detected_faulty[i]:
                    self.detected_faulty[i] = True; self.collector.record_fault_detected(self.step)
                    self.fault_counts[i] += 1; self._log("fault", f"Node {i} confirmed faulty (streak={self.low_streak[i]})")
            else:
                if self.detected_faulty[i]: self.detected_faulty[i] = False; self.collector.record_fault_resolved(self.step); self._log("heal", f"Node {i} cleared from fault detection")
                self.low_streak[i] = 0
        for i in np.where(self.detected_faulty)[0]:
            cid = self.cluster_mgr.get_instance_cluster(int(i))
            if cid is not None:
                ev = FaultEvent(instance_id=int(i), fault_type=FaultType.SOFT_FAULT, severity=float(1.0-self.scores[i]), timestamp=self.step)
                self.gossip.broadcast_fault(ev, cid, self.rng)
        self.gossip.propagate_step(self.rng); self.gossip.clear_old_messages(self.step)
        self.healer.apply_layer1_link_rewording(self.detected_faulty, self.step)
        for i in np.where(self.detected_faulty & self.healer.drained)[0]: self._log("heal", f"Node {i} drained from routing (Layer 1)")
        migration_candidates = np.where(self.healthy & (~self.healer.drained) & ((self.scores < cfg.low_fitness_threshold*1.5) | ((1.0-self.headroom) > 0.7) & (self.serveability < 0.6)))[0]
        healthy_targets = np.where(self.healthy & (~self.healer.drained) & (self.scores > cfg.low_fitness_threshold*1.2) & (self.headroom > 0.3) & (self.serveability > 0.7))[0]
        loaded_this_step: set = set()
        for src in migration_candidates[:max(1, len(migration_candidates)//2)]:
            if healthy_targets.size > 0:
                self.healer.apply_layer2_service_migration(int(src), healthy_targets, float(np.clip(1.0-self.headroom[src], 0.1, 0.8)), self.step)
                self.headroom[src] = np.clip(self.headroom[src]+0.20, 0.0, 1.0)
                self.net_penalty[src] = np.clip(self.net_penalty[src]-0.08, 0.0, 1.0)
                self.serveability[src] = np.clip(self.serveability[src]+0.10, 0.0, 1.0)
                unloaded = [tid for tid in healthy_targets if int(tid) not in loaded_this_step]
                if unloaded:
                    t = int(self.rng.choice(unloaded)); loaded_this_step.add(t)
                    self.headroom[t] = np.clip(self.headroom[t]-0.08, 0.0, 1.0)
                    self.net_penalty[t] = np.clip(self.net_penalty[t]+0.03, 0.0, 1.0)
        should_shed = ((1.0-self.headroom) > 0.85) & (self.serveability < 0.5) & (~self.healer.drained)
        self.healer.apply_layer3_predictive_shedding(1.0-self.headroom, self.serveability, self.step)
        self.serveability[should_shed] = np.clip(self.serveability[should_shed]+0.08, 0.0, 1.0)
        rejoin_mask = self.healer.progress_cooldown()
        if np.any(rejoin_mask):
            self.healthy[rejoin_mask] = True; self.detected_faulty[rejoin_mask] = False; self.low_streak[rejoin_mask] = 0
            (self.serveability, self.headroom, self.latency, self.net_penalty) = self.healer.apply_recovery_boost(
                rejoin_mask, self.serveability, self.headroom, self.latency, self.net_penalty)
            for i in np.where(rejoin_mask)[0]: self.collector.record_fault_resolved(self.step); self._log("heal", f"Node {i} rejoined routing after cooldown (Layer 1 release)")
        for cid in range(self.cfg.n_groups):
            current_head = self.cluster_mgr.get_cluster_head_id(cid)
            if current_head is not None and not self.healthy[current_head]:
                changed = self.cluster_mgr.reelect_cluster_head(cid, self.instances)
                if changed: self._log("info", f"Cluster {cid}: master re-elected → node {self.cluster_mgr.get_cluster_head_id(cid)}")
        avail = np.flatnonzero(self.healthy & (~self.healer.drained))
        requests = int(self.rng.poisson(cfg.request_rate)); self.collector.total_tasks_submitted += requests
        if avail.size == 0: self.collector.total_tasks_dropped += requests
        else:
            li = select_candidate_gso(self.scores[avail], self.rng)
            chosen = int(avail[int(np.clip(li, 0, avail.size-1))])
            for _ in range(requests):
                p_ok = float(np.clip(0.15+0.7*self.serveability[chosen]+0.2*self.headroom[chosen]-0.3*self.net_penalty[chosen], 0.0, 0.995))
                lat = abs(float(self.latency[chosen]+self.rng.normal(0.0, 5.0)))
                if self.rng.random() < p_ok: self.collector.record_task_completion(lat)
                else: self.collector.record_task_drop()
        if avail.size >= 2:
            for _ in range(min(int(self.rng.poisson(3)), 60-len(self._active_packets))):
                si, di = int(self.rng.integers(0, avail.size)), int(self.rng.integers(0, avail.size))
                if si != di:
                    src, dst = int(avail[si]), int(avail[di])
                    sg, dg = self.instances[src].group_id, self.instances[dst].group_id
                    sh, dh = self.cluster_mgr.get_cluster_head_id(sg), self.cluster_mgr.get_cluster_head_id(dg)
                    path = [src, dst] if (sg == dg or sh is None or dh is None) else [src, sh, dh, dst]
                    self._active_packets.append({"id": self._next_pid, "src": src, "dst": dst, "path": path, "progress": 0.0})
                    self._next_pid += 1
        survivors = []
        for pkt in self._active_packets:
            pkt["progress"] = min(1.0, pkt["progress"]+0.12)
            idx = min(int(pkt["progress"]*(len(pkt["path"])-1)), len(pkt["path"])-2)
            cur = pkt["path"][idx]
            if not self.healthy[cur] or self.detected_faulty[cur]: self._log("pkt", f"Packet {pkt['id']} dropped at node {cur}"); continue
            if pkt["progress"] >= 1.0: continue
            survivors.append(pkt)
        self._active_packets = survivors
        m = self.collector.get_metrics()
        self._pdr_history.append(m.pdr); self._fault_history.append(int(np.sum(self.detected_faulty))); self._healing_history.append(int(np.sum(self.healer.drained)))
        pkt_vis = []
        for pkt in self._active_packets:
            path = pkt["path"]; t = pkt["progress"]*(len(path)-1); idx = min(int(t), len(path)-2); frac = t-idx
            n0, n1 = path[idx], path[idx+1]
            pkt_vis.append((self.positions[n0,0]+(self.positions[n1,0]-self.positions[n0,0])*frac,
                            self.positions[n0,1]+(self.positions[n1,1]-self.positions[n0,1])*frac,
                            pkt["src"], pkt["dst"], pkt["id"]))
        return FrameSnapshot(step=self.step, healthy=self.healthy.copy(), serveability=self.serveability.copy(),
            headroom=self.headroom.copy(), latency_ms=self.latency.copy(), scores=self.scores.copy(),
            detected_faulty=self.detected_faulty.copy(), drained=self.healer.drained.copy(),
            cluster_heads=self._get_cluster_heads(), packets=pkt_vis,
            pdr=m.pdr, plr=m.plr, e2e_ms=m.e2e_latency_ms if m.e2e_latency_ms > 0 else 0.0,
            total_delivered=self.collector.total_tasks_completed, total_dropped=self.collector.total_tasks_dropped,
            event_log=self.event_log[-60:], clusters=dict(self.cluster_mgr.clusters))


def build_static_traces(sim):
    pos = sim.positions; traces = []
    for cid, info in sim.cluster_mgr.clusters.items():
        head = info.cluster_head_id; xs, ys = [], []
        for nid in info.instance_ids:
            if nid == head: continue
            xs += [pos[head,0], pos[nid,0], None]; ys += [pos[head,1], pos[nid,1], None]
        traces.append(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=NC["edge_in"], width=1.0), hoverinfo="none", showlegend=False))
    heads = [info.cluster_head_id for info in sim.cluster_mgr.clusters.values()]; xs, ys = [], []
    for i in range(len(heads)):
        for j in range(i+1, len(heads)):
            a, b = heads[i], heads[j]; xs += [pos[a,0], pos[b,0], None]; ys += [pos[a,1], pos[b,1], None]
    traces.append(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=NC["edge_bb"], width=1.5, dash="dot"), hoverinfo="none", showlegend=False))
    for name, color, symbol, sz in [
        ("Healthy", NC["healthy"], "circle", 10), ("Master Head", NC["master"], "star", 13),
        ("Faulty", NC["faulty"], "circle", 10), ("Drained (L1)", NC["drained"], "diamond", 10),
        ("Packet", NC["packet"], "circle", 8)]:
        traces.append(go.Scatter(x=[99], y=[99], mode="markers",
            marker=dict(size=sz, color=color, symbol=symbol, line=dict(color="#111110", width=1.5)),
            name=name, showlegend=True, hoverinfo="none"))
    traces.append(go.Scatter(x=[99,99], y=[99,99], mode="lines", line=dict(color=NC["edge_in"], width=2), name="Intra-cluster", showlegend=True, hoverinfo="none"))
    traces.append(go.Scatter(x=[99,99], y=[99,99], mode="lines", line=dict(color=NC["edge_bb"], width=2, dash="dot"), name="Inter-cluster", showlegend=True, hoverinfo="none"))
    return traces


def build_dynamic_traces(snap, pos):
    master_set = set(snap.cluster_heads)
    px, py, pt = [], [], []
    for x, y, src, dst, pid in snap.packets:
        px.append(x); py.append(y); pt.append(f"pkt#{pid}  {src}→{dst}")
    pkt_trace = go.Scatter(x=px, y=py, mode="markers",
        marker=dict(size=7, color=NC["packet"], symbol="circle", line=dict(color="#ffffff", width=1), opacity=0.9),
        text=pt, hoverinfo="text", name="Packets", showlegend=False)
    ids = [i for i in range(len(snap.healthy)) if i not in master_set]
    colors = [NC["faulty"] if snap.detected_faulty[i] or not snap.healthy[i] else NC["drained"] if snap.drained[i] else NC["healthy"] for i in ids]
    node_trace = go.Scatter(x=[pos[i,0] for i in ids], y=[pos[i,1] for i in ids], mode="markers",
        marker=dict(size=12, color=colors, symbol="circle", line=dict(color="#ffffff", width=1.5), opacity=0.92),
        text=[f"Node {i}  ·  score {snap.scores[i]:.3f}<br>serve {snap.serveability[i]:.2f}  head {snap.headroom[i]:.2f}  lat {snap.latency_ms[i]:.0f}ms<br>{'FAULTY' if snap.detected_faulty[i] or not snap.healthy[i] else 'DRAINED' if snap.drained[i] else 'OK'}" for i in ids],
        hoverinfo="text", name="Nodes", showlegend=False)
    m_ids = list(master_set)
    m_colors = [NC["faulty"] if snap.detected_faulty[i] or not snap.healthy[i] else NC["drained"] if snap.drained[i] else NC["master"] for i in m_ids]
    cid_map = {info.cluster_head_id: cid for cid, info in snap.clusters.items()}
    master_trace = go.Scatter(x=[pos[i,0] for i in m_ids], y=[pos[i,1] for i in m_ids],
        mode="markers+text",
        marker=dict(size=18, color=m_colors, symbol="star", line=dict(color="#ffffff", width=1.5)),
        text=[f"M{cid_map.get(i,'?')}" for i in m_ids], textposition="middle center",
        textfont=dict(size=7, color="#111110", family="DM Sans"),
        hovertext=[f"Master {i}  ·  Cluster {cid_map.get(i,'?')}<br>score {snap.scores[i]:.3f}  serve {snap.serveability[i]:.2f}<br>{'FAULTY' if snap.detected_faulty[i] or not snap.healthy[i] else 'OK'}" for i in m_ids],
        hoverinfo="text", name="Masters", showlegend=False)
    return [pkt_trace, node_trace, master_trace]


def build_animated_figure(cfg, n_steps, frame_ms):
    sim = SCFTGSOAnimSimulator(cfg)
    stage12_info = {"clusters": dict(sim.cluster_mgr.clusters),
        "top5": sorted([(fitness_score(x.metrics, w=sim.weights), x) for x in sim.instances], key=lambda t: t[0], reverse=True)[:5]}
    static_traces = build_static_traces(sim); n_static = len(static_traces)
    snap0 = FrameSnapshot(step=0, healthy=sim.healthy.copy(), serveability=sim.serveability.copy(),
        headroom=sim.headroom.copy(), latency_ms=sim.latency.copy(), scores=sim.scores.copy(),
        detected_faulty=sim.detected_faulty.copy(), drained=sim.healer.drained.copy(),
        cluster_heads=sim._get_cluster_heads(), packets=[], pdr=1.0, plr=0.0, e2e_ms=0.0,
        total_delivered=0, total_dropped=0, event_log=[], clusters=dict(sim.cluster_mgr.clusters))
    dyn0 = build_dynamic_traces(snap0, sim.positions)
    dyn_indices = list(range(n_static, n_static+len(dyn0)))
    all_traces = static_traces + dyn0
    frames, slider_steps, snapshots = [], [], [snap0]
    for step in range(n_steps):
        snap = sim.tick(); snapshots.append(snap); dyn = build_dynamic_traces(snap, sim.positions)
        pdr_color = "#16a34a" if snap.pdr > 0.7 else "#d97706" if snap.pdr > 0.5 else "#e53935"
        n_faulty = int(np.sum(snap.detected_faulty | ~snap.healthy)); n_drain = int(np.sum(snap.drained))
        frames.append(go.Frame(data=dyn, traces=dyn_indices, name=str(step),
            layout=go.Layout(title_text=(
                f"step {snap.step}  ·  "
                f"<span style='color:{pdr_color}'>PDR {snap.pdr:.1%}</span>  ·  "
                f"<span style='color:{NC['faulty']}'>faulty {n_faulty}</span>  ·  "
                f"<span style='color:{NC['drained']}'>drained {n_drain}</span>  ·  "
                f"<span style='color:{NC['packet']}'>pkts {len(snap.packets)}</span>"))))
        slider_steps.append(dict(method="animate",
            args=[[str(step)], dict(mode="immediate", frame=dict(duration=0, redraw=False), transition=dict(duration=0))],
            label=str(step+1)))
    fig = go.Figure(data=all_traces, frames=frames)
    fig.update_layout(
        uirevision="sc-ftgso-white",
        paper_bgcolor="#ffffff",   # pure white
        plot_bgcolor="#ffffff",    # pure white — no grey tint on canvas
        font=dict(family="DM Sans, system-ui, sans-serif", color="#6b6a65", size=12),
        title=dict(
            text="Press ▶ Play to start",
            font=dict(size=12, color="#9b9992", family="DM Sans"),
            x=0.0
        ),
        showlegend=True,
        legend=dict(
            bgcolor="#ffffff",
            bordercolor="#ebebea",
            borderwidth=1,
            font=dict(size=11, color="#6b6a65", family="DM Sans"),
            x=1.01, y=0.98
        ),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#ebebea",
            font=dict(family="DM Sans", size=12, color="#111110")
        ),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-5, 5],
            showline=False
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-5, 5],
            showline=False
        ),
        height=555,
        margin=dict(l=10, r=175, t=40, b=70),
        updatemenus=[dict(
            type="buttons", showactive=False,
            y=0, x=0.17, xanchor="right", yanchor="top",
            bgcolor="#ffffff",
            bordercolor="#ebebea",
            borderwidth=1,
            font=dict(family="DM Sans", size=12, color="#111110"),
            buttons=[
                dict(
                    label="▶  Play", method="animate",
                    args=[None, dict(frame=dict(duration=frame_ms, redraw=False),
                                     fromcurrent=True, transition=dict(duration=0), mode="immediate")]
                ),
                dict(
                    label="⏸  Pause", method="animate",
                    args=[[None], dict(frame=dict(duration=0, redraw=False),
                                       mode="immediate", transition=dict(duration=0))]
                )
            ]
        )],
        sliders=[dict(
            active=0,
            currentvalue=dict(prefix="Step ", font=dict(color="#6b6a65", size=12, family="DM Sans")),
            pad=dict(t=48, b=8, l=130),
            steps=slider_steps,
            bgcolor="#ffffff",
            bordercolor="#ebebea",
            borderwidth=1,
            tickcolor="#ebebea",
            font=dict(color="#9b9992", size=10, family="DM Sans")
        )]
    )
    return fig, sim, stage12_info, snapshots


def build_pdr_chart(sim):
    steps = list(range(len(sim._pdr_history)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=steps, y=sim._pdr_history, name="PDR", mode="lines",
        line=dict(color=NC["packet"], width=2.0),
        fill="tozeroy", fillcolor="rgba(22,163,74,0.06)"
    ))
    fig.add_trace(go.Scatter(
        x=steps, y=[f/max(1, sim.n) for f in sim._fault_history], name="Fault ratio",
        mode="lines", line=dict(color=NC["faulty"], width=1.5),
        fill="tozeroy", fillcolor="rgba(229,57,53,0.05)"
    ))
    fig.add_trace(go.Scatter(
        x=steps, y=[d/max(1, sim.n) for d in sim._healing_history], name="Drained",
        mode="lines", line=dict(color=NC["drained"], width=1.2, dash="dot")
    ))
    fig.add_hline(
        y=0.72, line=dict(color="rgba(22,163,74,0.30)", dash="dash"),
        annotation_text="~72% baseline",
        annotation_font=dict(color="#16a34a", size=10, family="DM Sans")
    )
    fig.update_layout(
        paper_bgcolor="#ffffff",   # pure white
        plot_bgcolor="#ffffff",    # pure white
        font=dict(family="DM Sans", color="#6b6a65", size=11),
        title=dict(
            text="Performance over Simulation",
            font=dict(size=12, color="#9b9992", family="DM Sans")
        ),
        legend=dict(
            bgcolor="#ffffff", bordercolor="#ebebea", borderwidth=1,
            font=dict(size=10, color="#6b6a65"),
            orientation="h", y=-0.25
        ),
        xaxis=dict(
            title="Step",
            gridcolor="#f4f3f0",
            linecolor="#ebebea",
            color="#9b9992",
            tickfont=dict(size=11, family="DM Sans"),
            title_font=dict(size=11),
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title="Ratio",
            gridcolor="#f4f3f0",
            linecolor="#ebebea",
            color="#9b9992",
            tickfont=dict(size=11, family="DM Sans"),
            title_font=dict(size=11),
            range=[0, 1.05],
            zeroline=False
        ),
        height=215,
        margin=dict(l=46, r=14, t=36, b=54)
    )
    return fig


# ── Page header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class='page-header'>
  <div class='page-title'>SC-FTGSO Network Simulator</div>
  <div class='page-sub'>Self-healing fault-tolerant routing &nbsp;·&nbsp; MO-GSO + PSO + GA + Gossip + 3-layer Healing</div>
  <div style='margin-top:10px;'>
    <span class='stage-pill'>S1 Tier</span>
    <span class='stage-pill'>S2 Cluster</span>
    <span class='stage-pill'>S3 Fault+Gossip</span>
    <span class='stage-pill'>S4 PSO+GA Route</span>
    <span class='stage-pill'>S5 Self-Healing</span>
    <span class='stage-pill'>S6 Metrics</span>
    <span class='stage-pill'>S7 Visualize</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class='sb-title'>SC-FTGSO</div>
<div class='sb-sub'>Simulation Settings</div>
""", unsafe_allow_html=True)

    st.markdown("<span class='ctrl-label'>Number of Nodes</span>", unsafe_allow_html=True)
    n_nodes = st.slider("Number of nodes", 20, 80, 50, step=5, label_visibility="collapsed")

    st.markdown("<span class='ctrl-label'>Simulation Steps</span>", unsafe_allow_html=True)
    n_steps = st.slider("Simulation steps", 20, 300, 100, label_visibility="collapsed")

    st.markdown("<span class='ctrl-label'>Animation Speed</span>", unsafe_allow_html=True)
    speed_label = st.select_slider("Speed", options=list(SPEED_OPTIONS.keys()), value="Normal (100ms)", label_visibility="collapsed")
    frame_ms = SPEED_OPTIONS[speed_label]

    st.markdown("<span class='ctrl-label'>Random Seed</span>", unsafe_allow_html=True)
    seed = st.slider("Random seed", 1, 100, 42, label_visibility="collapsed")

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
    run_btn = st.button("▶  Build & Animate", type="primary", use_container_width=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
    st.markdown("<div class='sec-head'>Legend</div>", unsafe_allow_html=True)
    st.markdown(f"""
<table class='leg-table'>
  <tr><td><span class='leg-swatch' style='background:{NC["healthy"]};'></span></td>
      <td><span class='leg-name'>Healthy</span><br><span class='leg-desc'>Routing via GSO</span></td></tr>
  <tr><td><span class='leg-swatch' style='background:{NC["master"]}; border-radius:2px;'></span></td>
      <td><span class='leg-name'>Master (Head)</span><br><span class='leg-desc'>MO-GSO elected cluster head</span></td></tr>
  <tr><td><span class='leg-swatch' style='background:{NC["faulty"]};'></span></td>
      <td><span class='leg-name'>Faulty</span><br><span class='leg-desc'>Hard / Soft / Transient fault</span></td></tr>
  <tr><td><span class='leg-swatch' style='background:{NC["drained"]}; border-radius:2px;'></span></td>
      <td><span class='leg-name'>Drained (L1)</span><br><span class='leg-desc'>Link-rewording cooldown</span></td></tr>
  <tr><td><span class='leg-swatch' style='background:{NC["packet"]};'></span></td>
      <td><span class='leg-name'>Packet</span><br><span class='leg-desc'>src → M_src → M_dst → dst</span></td></tr>
</table>
""", unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
    st.markdown("<div class='sec-head'>Algorithm</div>", unsafe_allow_html=True)
    st.markdown("""
<div class='algo-box'>
fitness = w₁(1−CPU) + w₂(1−Net)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ w₃(headroom) + w₄(serve)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ w₅(fault history)<br><br>
PSO retunes w₁–w₅ every 75 steps<br>
Routing: PSO + GA hybrid (GSO)<br>
Gossip: hops = 2, p = 0.85<br>
Heal: cooldown = 6, boost = 0.45<br>
Expected PDR ≈ 72 – 80%
</div>
""", unsafe_allow_html=True)


# ── Main layout ────────────────────────────────────────────────────────────────
col_net, col_stats = st.columns([3, 1])

with col_stats:
    st.markdown("<div class='sec-head' style='margin-top:2px;'>Results</div>", unsafe_allow_html=True)
    stat_pdr     = st.empty()
    stat_deliv   = st.empty()
    stat_dropped = st.empty()
    stat_steps   = st.empty()
    st.markdown("<div class='sec-head' style='margin-top:16px;'>Cluster Formation</div>", unsafe_allow_html=True)
    cluster_box = st.empty()
    st.markdown("<div class='sec-head' style='margin-top:16px;'>Event Log</div>", unsafe_allow_html=True)
    log_box = st.empty()

with col_net:
    net_box     = st.empty()
    metrics_box = st.empty()


# ── Render ─────────────────────────────────────────────────────────────────────
if "fig" not in st.session_state:
    with net_box:
        st.info("Configure the simulation in the sidebar, then click **▶ Build & Animate**.\n\nRuns the real SC-FTGSO engine — same algorithm yielding ~72–79% PDR.")

if run_btn:
    cfg = AnimSimConfig(n_instances=n_nodes, n_groups=5, seed=seed)
    with st.spinner("Running SC-FTGSO (all 7 stages)…"):
        fig, final_sim, stage12_info, snapshots = build_animated_figure(cfg, n_steps, frame_ms)
    st.session_state.update({"fig": fig, "sim": final_sim, "stage12": stage12_info, "snapshots": snapshots})

if "fig" in st.session_state:
    fig, sim_done, stage12 = st.session_state["fig"], st.session_state["sim"], st.session_state["stage12"]

    with col_net:
        net_box.plotly_chart(fig, use_container_width=True)
        metrics_box.plotly_chart(build_pdr_chart(sim_done), use_container_width=True)

    with col_stats:
        m = sim_done.collector.get_metrics()
        stat_pdr.metric("Final PDR",   f"{m.pdr:.1%}")
        stat_deliv.metric("Delivered", sim_done.collector.total_tasks_completed)
        stat_dropped.metric("Dropped", sim_done.collector.total_tasks_dropped)
        stat_steps.metric("Steps run", sim_done.step)

        ch_html = "<div class='cluster-box'>"
        for cid, info in sorted(stage12["clusters"].items()):
            ch_html += (
                f"<span style='color:#9b9992'>C{cid}</span> "
                f"<span style='color:#111110;font-weight:600'>{len(info.instance_ids)} nodes</span>"
                f"  head=<span style='color:#2563eb'>#{info.cluster_head_id}</span>"
                f"  fit=<span style='color:#16a34a'>{info.fitness_score:.3f}</span><br>"
            )
        ch_html += "</div>"
        cluster_box.markdown(ch_html, unsafe_allow_html=True)

        log_html = "<div class='ev-log'>"
        for entry in reversed(sim_done.event_log[-40:]):
            css = "ev-fault" if "[FAULT]" in entry else "ev-heal" if "[HEAL]" in entry else "ev-packet" if "[PKT]" in entry else "ev-info"
            log_html += f"<div class='{css}'>{entry}</div>"
        log_html += "</div>"
        log_box.markdown(log_html, unsafe_allow_html=True)