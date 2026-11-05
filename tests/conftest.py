import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from pathlib import Path
import pytest
from risklab.core.inputs import read_json
from risklab.services.experiments import default_config

@pytest.fixture
def scenario():
    return read_json(Path(__file__).resolve().parents[1]/'risklab/resources/examples/correlated_history.json')

@pytest.fixture
def config():
    d=default_config();d.update(n_paths=2000,n_steps=8,confidences=['0.95']);return d
