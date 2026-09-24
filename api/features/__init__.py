"""features — the product surface of api, one package per feature.

Each feature owns its tables, its data module (the only place SQLAlchemy
appears) and its routes, and exposes a public surface through its __init__
(structure.md). Import across features only through that surface.
"""
