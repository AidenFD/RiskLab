"""Small immutable domain records for validated boundary snapshots."""
from dataclasses import dataclass
from enum import Enum

class RunState(str, Enum):
    EMPTY='EMPTY'
    INVALID='INVALID'
    READY='READY'
    RUNNING='RUNNING'
    CANCELLING='CANCELLING'
    COMPLETED='COMPLETED'
    CANCELLED='CANCELLED'
    FAILED='FAILED'

@dataclass(frozen=True)
class PortfolioSnapshot:
    as_of_session: str
    currency: str
    cash: float
    symbols: tuple[str, ...]
    quantities: tuple[float, ...]
    initial_prices: tuple[float, ...]

@dataclass(frozen=True)
class ProgressSnapshot:
    phase: str
    completed: int
    total: int

@dataclass(frozen=True)
class SimulationConfig:
    n_paths: int = 10000
    n_steps: int = 252
    seed: int = 42
    batch_size: int = 512
    preview_count: int = 20
    confidences: tuple[str, ...] = ('0.95','0.99')
    drift_mode: str = 'ZERO_LOG_MEAN'
