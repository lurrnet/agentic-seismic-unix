from pathlib import Path
import re
import shutil
import uuid
import streamlit as st

from agent.seismic_agent import SeismicAgent, AgentConfigurationError
from agent.knowledge_mode import run_knowledge_turn
from agent.provider_factory import load_agent_config
from agent.toolkit import AgentToolkit
from agent.proposal_fallback import parse_explicit_user_command
from project.project import Project
from workflow.history import HistoryStore
from workflow.engine import WorkflowEngine
from su.registry import ToolRegistry
from su.executor