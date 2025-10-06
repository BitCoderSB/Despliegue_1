import io, re, requests, pandas as pd
from .auth import giovanni_token

TS_URL = "https://api.giovanni.earthdata.nasa.gov/timeseries"

def parse_giovanni_csv(csv_text: str) -> pd.DataFrame:
    lines = csv_text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^\s*Timestamp\s*,', line):
            header_idx = i; break
    if header_idx is None:
        raise RuntimeError("No se encontró 'Timestamp' en CSV Giovanni.")
    data_text = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(data_text))
    if "Timestamp" not in df.columns:
        time_col = [c for c in df.columns if c.lower().startswith("time")][0]
        df = df.rename(columns={time_col:"Timestamp"})
    val_cols = [c for c in df.columns if c != "Timestamp"]
    if not val_cols: raise RuntimeError("CSV Giovanni sin columna de valores.")
    val_col = val_cols[0]
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["Timestamp"]).set_index("Timestamp").sort_index()
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    return df[[val_col]]

def giovanni_timeseries(data_id: str, lat: float, lon: float, start_iso: str, end_iso: str, token: str | None=None) -> pd.DataFrame:
    token = token or giovanni_token()
    params = {"data": data_id, "location": f"[{lat},{lon}]", "time": f"{start_iso}/{end_iso}"}
    r = requests.get(TS_URL, params=params, headers={"authorizationtoken": token}, timeout=120)
    r.raise_for_status()

    try:
        return parse_giovanni_csv(r.text)
    except Exception:

        with io.StringIO(r.text) as f:
            headers_kv = {}
            for _ in range(40):
                pos = f.tell(); line = f.readline()
                if not line: break
                if line.startswith("Timestamp (UTC),"):
                    f.seek(pos); break
                try:
                    k,v = line.split(",",1); headers_kv[k.strip()] = v.strip()
                except ValueError:
                    pass
            colname = headers_kv.get("param_name", "value")
            df = pd.read_csv(f, header=0, names=("Timestamp", colname))
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
            df = df.dropna(subset=["Timestamp"]).set_index("Timestamp").sort_index()
            df.attrs["headers"] = headers_kv
            return df
