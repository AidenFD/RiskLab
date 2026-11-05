"""Complete-session raw-price calibration; no imputation or calendar inference."""
import csv
import io
from pathlib import Path
import numpy as np
from .inputs import ValidationError, read_json, symbols_checked, session, array


def validate_history(csv_text, metadata, symbols, *, calibrate=True):
    symbols = symbols_checked(symbols)
    if not isinstance(metadata, dict) or metadata.get('schema_version') != 1 or type(metadata.get('schema_version')) is not int:
        raise ValidationError('History metadata schema_version must be 1')
    if metadata.get('price_basis') != 'RAW' or metadata.get('currency') != 'USD' or metadata.get('action_free') is not True:
        raise ValidationError('History requires RAW, USD, and an explicit action_free: true declaration')
    if metadata.get('source_kind') not in ('SYNTHETIC','USER_DECLARED'):
        raise ValidationError('History source_kind must be SYNTHETIC or USER_DECLARED')
    if not isinstance(metadata.get('calendar_id'), str) or not metadata['calendar_id'].strip():
        raise ValidationError('Declared calendar_id is required')
    if list(metadata.get('symbols', [])) != list(symbols):
        raise ValidationError('Metadata symbols must match the portfolio order')
    expected = metadata.get('expected_sessions')
    if not isinstance(expected, list) or not expected:
        raise ValidationError('expected_sessions must list every required price session')
    for d in expected:
        session(d)
    if expected != sorted(set(expected)):
        raise ValidationError('Expected sessions must be strictly increasing and unique')
    if isinstance(csv_text,str) and len(csv_text.encode('utf-8'))>8000000:
        raise ValidationError('History CSV exceeds the 8 MB v1 import limit')
    if len(expected)>20000:
        raise ValidationError('History exceeds 20,000 price sessions')
    if not isinstance(csv_text, str):
        raise ValidationError('History CSV text is missing')
    reader = csv.reader(io.StringIO(csv_text.lstrip('\ufeff')), strict=True)
    try:
        header = next(reader)
        if len(header) != len(set(header)) or set(header) != {'Date',*symbols}:
            raise ValidationError('CSV requires Date and exactly one column per portfolio symbol')
        rows = list(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValidationError(f'Invalid CSV: {exc}') from exc
    if any(len(r) != len(header) for r in rows):
        raise ValidationError('Ragged or empty CSV row')
    dates = [r[header.index('Date')] for r in rows]
    if dates != expected:
        raise ValidationError('CSV dates differ from expected_sessions: missing, duplicate, reordered or extra session')
    values = []
    for line, row in enumerate(rows, 2):
        try:
            values.append([float(row[header.index(s)]) for s in symbols])
        except ValueError as exc:
            raise ValidationError(f'CSV row {line}: invalid price') from exc
    prices = array(values, 'History prices', 2)
    if (prices <= 0).any():
        raise ValidationError('History prices must be positive; no missing values may be filled')
    minimum = max(60, 10*len(symbols))
    if len(prices)-1 < minimum:
        raise ValidationError(f'Calibration requires at least {minimum} complete adjacent return observations')
    returns = np.diff(np.log(prices), axis=0) if calibrate else None
    mean, cov = fit_model(returns) if calibrate else (None, None)
    return {'dates': dates, 'prices': prices, 'estimated_mean': mean,
            'covariance': cov, 'metadata': metadata, 'n_observations': len(prices)-1}


def fit_model(returns):
    returns = array(returns, 'Log returns', 2)
    if len(returns) < 2:
        raise ValidationError('At least two observations required for sample covariance')
    with np.errstate(over='raise', invalid='raise'):
        mean = returns.mean(axis=0)
        cov = np.atleast_2d(np.cov(returns, rowvar=False, ddof=1))
    if not np.isfinite(cov).all():
        raise ValidationError('Nonfinite calibrated covariance')
    return mean, cov


def load_history(path, symbols):
    path = Path(path)
    text = path.read_text(encoding='utf-8-sig')
    return validate_history(text, read_json(path.with_suffix('.meta.json')), symbols)
