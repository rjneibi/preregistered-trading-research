def __getattr__(n):
    return lambda *a, **k: None
