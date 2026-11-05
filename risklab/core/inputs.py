"""Strict input boundaries shared by CLI, desktop, and saved-run verification."""
from __future__ import annotations
import json
import math
from datetime import date
from pathlib import Path
import numpy as np


class ValidationError(ValueError):
    """A user-correctable input error."""


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValidationError(f'Duplicate JSON key: {key}')
        obj[key] = value
    return obj


def parse_json(text):
    try:
        return json.loads(text, object_pairs_hook=_pairs,
                          parse_constant=lambda s: (_ for _ in ()).throw(ValidationError(f'Invalid number {s}')))
    except (ValueError, TypeError) as exc:
        raise ValidationError(f'Invalid JSON: {exc}') from exc


def read_json(path):
    try:
        if Path(path).stat().st_size>16000000:
            raise ValidationError('JSON input exceeds the 16 MB v1 limit')
        return parse_json(Path(path).read_text(encoding='utf-8-sig'))
    except OSError as exc:
        raise ValidationError(f'Cannot read {path}: {exc}') from exc


def number(value, label, *, minimum=None, positive=False):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (str, int, float, np.number)):
        raise ValidationError(f'{label}: enter a finite number, not a boolean')
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValidationError(f'{label}: enter a finite number') from exc
    if not math.isfinite(result) or (minimum is not None and result < minimum) or (positive and result <= 0):
        raise ValidationError(f'{label}: invalid finite numeric range')
    return result


def array(value, label, ndim=1):
    try:
        obj = np.asarray(value, dtype=object)
        if any(isinstance(x, (bool, np.bool_)) for x in obj.flat):
            raise ValidationError(f'{label}: booleans are not numeric inputs')
        result = np.array(value, dtype=np.float64, copy=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError(f'{label}: expected a rectangular finite numeric array') from exc
    if result.ndim != ndim or not result.size or not np.isfinite(result).all():
        raise ValidationError(f'{label}: expected a nonempty finite {ndim}-dimensional array')
    return result


def integer(value, label, low, high):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or not low <= value <= high:
        raise ValidationError(f'{label}: integer required in [{low}, {high}]')
    return int(value)


def symbols_checked(symbols):
    if not isinstance(symbols, (list, tuple)) or not 1 <= len(symbols) <= 10:
        raise ValidationError('Declare one to ten asset symbols')
    if any(not isinstance(s, str) or not s.strip() or s != s.strip() or len(s) > 32 or any(ord(c)<32 for c in s) for s in symbols):
        raise ValidationError('Symbols must be nonempty identifiers without outer spaces (max 32 characters)')
    if len(set(symbols)) != len(symbols):
        raise ValidationError('Duplicate asset symbol')
    return tuple(symbols)


def session(value, label='Session'):
    if not isinstance(value, str):
        raise ValidationError(f'{label}: ISO date required')
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except ValueError as exc:
        raise ValidationError(f'{label}: use YYYY-MM-DD') from exc
    return value


def validate_scenario(raw, *, calibrated_parameters=None):
    if not isinstance(raw, dict) or raw.get('schema_version') != 1 or type(raw.get('schema_version')) is not int:
        raise ValidationError('Scenario schema_version must be 1')
    p = raw.get('portfolio')
    if not isinstance(p, dict) or p.get('currency') != 'USD':
        raise ValidationError('A USD portfolio is required')
    session(p.get('as_of_session'), 'As-of session')
    positions = p.get('positions')
    if not isinstance(positions, list) or any(not isinstance(x, dict) for x in positions):
        raise ValidationError('Positions must be a list of asset records')
    symbols = symbols_checked([x.get('symbol') for x in positions])
    cash = number(p.get('cash'), 'Cash', minimum=0)
    quantities, prices = [], []
    for x in positions:
        if x.get('instrument_type') != 'EQUITY':
            raise ValidationError(f"{x.get('symbol')}: v1 supports EQUITY only; options/derivatives rejected")
        quantities.append(number(x.get('quantity'), x['symbol']+' quantity', minimum=0))
        prices.append(number(x.get('initial_price'), x['symbol']+' initial price', positive=True))
    with np.errstate(over='ignore', invalid='ignore'):
        equity = cash + np.dot(quantities, prices)
    if not np.isfinite(equity) or equity <= 0:
        raise ValidationError('Initial equity must be finite and positive')
    model = raw.get('model', {})
    if not isinstance(model, dict) or model.get('kind') not in ('MANUAL', 'HISTORY'):
        raise ValidationError('Model kind must be MANUAL or HISTORY')
    if model['kind'] == 'HISTORY':
        from .calibration import validate_history
        history = raw.get('history', {})
        calibrated = validate_history(history.get('csv_text'), history.get('metadata'), symbols, calibrate=calibrated_parameters is None)
        if calibrated['dates'][-1] != p['as_of_session'] or not np.allclose(calibrated['prices'][-1], prices, rtol=1e-10, atol=1e-10):
            raise ValidationError('Snapshot date and initial prices must match the last history row')
        if calibrated_parameters is None:
            estimated, cov = calibrated['estimated_mean'], calibrated['covariance']
        else:
            estimated = array(calibrated_parameters.get('estimated_daily_log_mean'), 'Stored estimated means')
            cov = array(calibrated_parameters.get('daily_log_cov'), 'Stored covariance', 2)
            if estimated.shape!=(len(symbols),) or cov.shape!=(len(symbols),len(symbols)):
                raise ValidationError('Stored calibrated parameter dimensions mismatch')
        provenance = history['metadata']['source_kind']
        n_obs = calibrated['n_observations']
        estimation_dates = [calibrated['dates'][0], calibrated['dates'][-1]]
    else:
        ms = symbols_checked(model.get('symbols'))
        if set(ms) != set(symbols):
            raise ValidationError('Manual model symbols do not match portfolio')
        means = array(model.get('daily_log_mean'), 'Daily log means')
        covariance = array(model.get('daily_log_cov'), 'Daily log covariance', 2)
        if means.shape != (len(ms),) or covariance.shape != (len(ms), len(ms)):
            raise ValidationError('Manual model dimensions do not match symbols')
        mapping = [ms.index(s) for s in symbols]
        estimated, cov = means[mapping], covariance[np.ix_(mapping, mapping)]
        provenance, n_obs, estimation_dates = 'HYPOTHETICAL', None, None
    from .simulation import factor_covariance
    _, diagnostics = factor_covariance(cov)
    return {'symbols': list(symbols), 'quantities': quantities, 'prices': prices, 'cash': cash,
            'estimated_mean': estimated, 'covariance': cov, 'initial_equity': float(equity),
            'provenance': provenance, 'n_observations': n_obs, 'estimation_dates': estimation_dates,
            'covariance_diagnostics': diagnostics}
