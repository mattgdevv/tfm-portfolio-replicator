"""
Workflows Module
Módulo de workflows con comandos especializados y coordinador de flujos interactivos

IMPORTANTE: Para pipelines ETL automáticos usar scripts/etl_cli.py
Este módulo es para flujos interactivos solamente.
"""

from .interactive_flows import InteractiveFlows
from .commands.extraction_commands import ExtractionCommands
from .commands.analysis_commands import AnalysisCommands
from .commands.monitoring_commands import MonitoringCommands

__all__ = ['InteractiveFlows', 'ExtractionCommands', 'AnalysisCommands', 'MonitoringCommands']
