"""Paquete pragmatics_rst


Exposición pública mínima para uso como módulo.
"""
from .core import analyze_rst
from .batch import analyze_many


__all__ = ["analyze_rst", "analyze_many"]
