# FTGSO Project: Proper Directory Structure

## Current vs Recommended Structure

### Current (Flat)
```
CN_project/
├── README.md
├── requirements.txt
├── PROJECT_ANALYSIS.md
├── QUICK_REFERENCE.md
├── DATA_FLOW.md
├── CODEBASE_STRUCTURE.md
├── visual_simulation.ipynb
├── ftgso_sim/
│   ├── model.py
│   ├── cluster.py
│   ├── ... (many files)
│   ├── optimizer/
│   ├── sim/
│   └── prototype/
├── outputs/
├── sweep_outputs/
├── ablation_outputs/
└── [other dirs]
```

### Recommended
```
CN_project/
│
├── ftgso_sim/                    ← Core package (rename to src/ftgso or keep as-is)
│   ├── __init__.py
│   ├── model.py
│   ├── cluster.py
│   ├── fault.py
│   ├── gossip.py
│   ├── fitness.py
│   ├── healing.py
│   ├── metrics.py
│   ├── baselines.py
│   ├── routing_path.py
│   │
│   ├── optimizer/
│   │   ├── __init__.py
│   │   ├── pso.py
│   │   ├── ga.py
│   │   └── gso.py
│   │
│   ├── sim/
│   │   ├── __init__.py
│   │   ├── step2.py
│   │   ├── run.py
│   │   ├── sweep.py
│   │   └── ablation.py
│   │
│   └── prototype/
│       ├── __init__.py
│       ├── demo.py
│       ├── router.py
│       ├── worker.py
│       └── healer.py
│
├──  docs/                         ← Documentation (REORGANIZE HERE)
│   ├── README.md                    ← Main project overview
│   ├── ARCHITECTURE.md              ← PROJECT_ANALYSIS.md (renamed)
│   ├── API_REFERENCE.md             ← QUICK_REFERENCE.md (renamed)
│   ├── DATA_FLOW.md                 ← Keep as-is
│   ├── CODEBASE_STRUCTURE.md        ← Keep as-is
│   ├── SETUP_GUIDE.md               ← New: Installation guide
│   ├── TUTORIAL.md                  ← New: Step-by-step usage
│   └── API/
│       ├── model.md
│       ├── cluster.md
│       ├── optimization.md
│       └── healing.md
│
├──  examples/                     ← Example scripts (NEW)
│   ├── README.md                    ← How to run examples
│   ├── basic_simulation.py          ← Extract from step2.py
│   ├── custom_policy.py             ← How to add custom routing
│   ├── parameter_sweep_example.py   ← Extract from sweep.py
│   └── visualize_results.py         ← Extract from notebook
│
├──  scripts/                      ← CLI utilities (NEW)
│   ├── run_simulation.py            ← Wrapper around sim/step2.py
│   ├── run_sweep.py                 ← Wrapper around sim/sweep.py
│   ├── run_ablation.py              ← Wrapper around sim/ablation.py
│   └── run_prototype.py             ← Wrapper around prototype/demo.py
│
├──  tests/                        ← Unit tests (NEW)
│   ├── __init__.py
│   ├── conftest.py                  ← Pytest fixtures
│   ├── test_model.py
│   ├── test_fitness.py
│   ├── test_cluster.py
│   ├── test_fault.py
│   ├── test_gossip.py
│   ├── test_optimizer.py
│       ├── test_pso.py
│       ├── test_ga.py
│       └── test_gso.py
│   ├── test_healing.py
│   └── test_simulation.py
│
├──  results/                      ← Organized output directory (RENAME)
│   ├── README.md                    ← Results guide
│   ├── default_run/
│   │   ├── summary.csv
│   │   └── metadata.json
│   ├── parameter_sweep/
│   │   ├── runs.csv
│   │   ├── summary_agg.csv
│   │   └── summary_by_scenario.csv
│   ├── ablation_study/
│   │   └── ablation_summary.csv
│   └── visualizations/
│       ├── metrics_comparison.png
│       └── policy_comparison.png
│
├──  notebooks/                    ← Jupyter notebooks (NEW)
│   ├── analysis.ipynb               ← Visualization notebook (from visual_simulation.ipynb)
│   ├── parameter_study.ipynb
│   └── ablation_analysis.ipynb
│
├──  config/                       ← Configuration files (NEW)
│   ├── default.yaml                 ← Default simulation config
│   ├── large_scale.yaml             ← Large-scale config
│   └── test.yaml                    ← Test config
│
├──  data/                         ← Input data (if any) (NEW)
│   ├── README.md
│   └── [input datasets if used]
│
├── .gitignore                       ← Git ignore patterns
├── setup.py                         ← Package installation
├── pyproject.toml                  ← Python 3.8+ project config
├── requirements.txt                 ← Dependencies
├── requirements-dev.txt             ← Dev dependencies (pytest, jupyter)
├── Makefile                         ← Common commands
├── README.md                        ← Project root overview
├── LICENSE                          ← License file (MIT, etc.)
└── CONTRIBUTING.md                 ← Contribution guidelines
```

---

## Step-by-Step Refactoring Guide

### **Step 1: Create New Directories**
```bash
mkdir -p docs examples scripts tests results/default_run results/parameter_sweep results/ablation_study results/visualizations notebooks config data
```

### **Step 2: Move Documentation**
```bash
# Move documentation files to docs/
mv PROJECT_ANALYSIS.md docs/ARCHITECTURE.md
mv QUICK_REFERENCE.md docs/API_REFERENCE.md
mv DATA_FLOW.md docs/
mv CODEBASE_STRUCTURE.md docs/

# Create new docs
touch docs/SETUP_GUIDE.md
touch docs/TUTORIAL.md
touch docs/API/model.md
touch docs/API/cluster.md
touch docs/API/optimization.md
touch docs/API/healing.md
```

### **Step 3: Move Output Directories**
```bash
# Organize results
mv outputs/summary.csv results/default_run/
mv sweep_outputs/* results/parameter_sweep/
mv ablation_outputs/* results/ablation_study/
rm -rf outputs sweep_outputs ablation_outputs sweep_outputs_quick
```

### **Step 4: Create Example Scripts**
```bash
# Extract examples from main code
touch examples/basic_simulation.py
touch examples/custom_policy.py
touch examples/parameter_sweep_example.py
touch examples/visualize_results.py
touch examples/README.md
```

### **Step 5: Move Notebooks**
```bash
mkdir -p notebooks
mv visual_simulation.ipynb notebooks/analysis.ipynb
touch notebooks/parameter_study.ipynb
touch notebooks/ablation_analysis.ipynb
```

### **Step 6: Create CLI Scripts**
```bash
touch scripts/run_simulation.py
touch scripts/run_sweep.py
touch scripts/run_ablation.py
touch scripts/run_prototype.py
```

### **Step 7: Create Test Structure**
```bash
# Create test files (initially empty, to be filled)
touch tests/__init__.py
touch tests/conftest.py
touch tests/test_model.py
touch tests/test_fitness.py
touch tests/test_cluster.py
touch tests/test_fault.py
touch tests/test_gossip.py
touch tests/test_optimizer.py
touch tests/test_healing.py
touch tests/test_simulation.py
```

### **Step 8: Create Configuration Files**
```bash
touch config/default.yaml
touch config/large_scale.yaml
touch config/test.yaml
```

### **Step 9: Create Project Files**
```bash
touch setup.py
touch pyproject.toml
touch requirements-dev.txt
touch Makefile
touch LICENSE
touch CONTRIBUTING.md
```

---

## File Contents to Create

### **setup.py**
```python
from setuptools import setup, find_packages

setup(
    name="ftgso-sim",
    version="1.0.0",
    description="Fault-Tolerant Genetical Swarm Optimization for LANs",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/ftgso-sim",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.19.0",
        "matplotlib>=3.3.0",
        "pandas>=1.1.0",
        "seaborn>=0.11.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.10.0",
            "jupyter>=1.0.0",
            "ipython>=7.0.0",
        ],
        "docs": [
            "sphinx>=3.0",
            "sphinx-rtd-theme>=0.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ftgso-simulate=scripts.run_simulation:main",
            "ftgso-sweep=scripts.run_sweep:main",
            "ftgso-ablation=scripts.run_ablation:main",
            "ftgso-prototype=scripts.run_prototype:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
```

### **pyproject.toml**
```toml
[build-system]
requires = ["setuptools>=40.8.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ftgso-sim"
version = "1.0.0"
description = "Fault-Tolerant Genetical Swarm Optimization for LANs"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.8"
authors = [{name = "Your Name", email = "your.email@example.com"}]
keywords = ["optimization", "swarm", "genetic-algorithm", "routing", "fault-tolerance"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=ftgso_sim"

[tool.black]
line-length = 100

[tool.isort]
profile = "black"
line_length = 100
```

### **requirements-dev.txt**
```
-r requirements.txt
pytest>=6.0
pytest-cov>=2.10.0
black>=21.0
isort>=5.0
flake8>=3.9.0
jupyter>=1.0.0
ipython>=7.0.0
sphinx>=3.0
```

### **Makefile**
```makefile
.PHONY: help install install-dev test coverage lint format clean docs

help:
	@echo "FTGSO Project - Available Commands"
	@echo "==================================="
	@echo "make install       - Install package in production mode"
	@echo "make install-dev   - Install package with development tools"
	@echo "make test          - Run pytest tests"
	@echo "make coverage      - Run tests with coverage report"
	@echo "make lint          - Check code style (flake8)"
	@echo "make format        - Auto-format code (black, isort)"
	@echo "make clean         - Remove build artifacts and cache"
	@echo "make docs          - Generate Sphinx documentation"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,docs]"

test:
	pytest

coverage:
	pytest --cov=ftgso_sim --cov-report=html --cov-report=term

lint:
	flake8 ftgso_sim tests

format:
	black ftgso_sim tests examples
	isort ftgso_sim tests examples

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info .coverage htmlcov .pytest_cache

docs:
	cd docs && sphinx-build -b html . _build
```

### **.gitignore**
```
# Byte-compiled / optimized
__pycache__/
*.py[cod]
*$py.class
*.so

# Distribution
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Jupyter
.ipynb_checkpoints/
*.ipynb_checkpoints

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
results/*/
*.csv.bak
.cache/
*.log

# Virtual environments
venv/
env/
ENV/
```

### **examples/README.md**
```markdown
# FTGSO Examples

This directory contains standalone examples demonstrating how to use the FTGSO library.

## Basic Simulation
```bash
python examples/basic_simulation.py
```

## Parameter Sweep
```bash
python examples/parameter_sweep_example.py --n-instances 20 --request-rate 1.0
```

## Custom Policy
```bash
python examples/custom_policy.py
```

## Visualization
```bash
python examples/visualize_results.py results/default_run/summary.csv
```
```

### **docs/SETUP_GUIDE.md**
```markdown
# FTGSO Setup Guide

## Installation

### From Source
```bash
git clone https://github.com/yourusername/ftgso-sim.git
cd ftgso-sim
pip install -e .
```

### Development Setup
```bash
pip install -e ".[dev,docs]"
```

## Verification
```bash
pytest
python -m ftgso_sim.sim.run
```
```

---

## Benefits of This Structure

| Aspect | Benefit |
|--------|---------|
| **Scalability** | Easy to add new modules without cluttering root |
| **Maintainability** | Clear separation of concerns (code, tests, docs, examples) |
| **Distribution** | Can be packaged and distributed via pip |
| **Testing** | Organized test structure with fixtures |
| **Documentation** | Dedicated docs directory with API references |
| **Examples** | New users learn quickly from working code |
| **CI/CD** | Easier to integrate with GitHub Actions, Jenkins |
| **Collaboration** | Clear guidelines for contributors via CONTRIBUTING.md |

---

## Quick Reorganization Script

If you want to automate most of this:

```bash
#!/bin/bash

# Create directories
mkdir -p docs examples scripts tests results/{default_run,parameter_sweep,ablation_study,visualizations} notebooks config data

# Move files
mv PROJECT_ANALYSIS.md docs/ARCHITECTURE.md 2>/dev/null || true
mv QUICK_REFERENCE.md docs/API_REFERENCE.md 2>/dev/null || true
mv DATA_FLOW.md docs/ 2>/dev/null || true
mv CODEBASE_STRUCTURE.md docs/ 2>/dev/null || true
mv visual_simulation.ipynb notebooks/analysis.ipynb 2>/dev/null || true

# Move results
mv outputs/* results/default_run/ 2>/dev/null || true
mv sweep_outputs/* results/parameter_sweep/ 2>/dev/null || true
mv ablation_outputs/* results/ablation_study/ 2>/dev/null || true
rm -rf outputs sweep_outputs ablation_outputs sweep_outputs_quick 2>/dev/null || true

# Create test files
touch tests/__init__.py tests/conftest.py tests/test_*.py

# Create config files
touch config/default.yaml config/large_scale.yaml config/test.yaml

# Create root files
touch setup.py pyproject.toml requirements-dev.txt Makefile LICENSE CONTRIBUTING.md

echo " Directory structure reorganized successfully!"
```

---

## Alternative: Src Layout (More Professional)

If you prefer the modern "src" layout:

```
CN_project/
├── src/
│   └── ftgso_sim/          # Rename ftgso_sim → src/ftgso_sim
│       ├── model.py
│       ├── optimizer/
│       ├── sim/
│       └── prototype/
├── tests/
├── docs/
├── examples/
└── setup.py                # Points to src/ftgso_sim
```

**Advantages:**
-  Avoids accidental imports from wrong location
-  Clearer separation of source code
-  Standard for pip distributions
-  Better for CI/CD

**setup.py with src layout:**
```python
from setuptools import setup, find_packages

setup(
    name="ftgso-sim",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    # ...
)
```

---

