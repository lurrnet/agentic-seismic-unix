import shlex
from pathlib import Path
from types import SimpleNamespace

from security.policy import audit_event, enforce_processing_limits


class WorkflowEngine:
    def __init__(self, executor, history):
        self.executor = executor
        self.history = history

    def run_processing_step(
        self, state, tool_name, input_path, output_path, parameters, reason
    ):
        input_path = Path(input_path)
        output_path = Path(output_path)
        project_root = output_path.parent.parent
        project = SimpleNamespace(
            root=project_root,
            history_dir=project_root / 'history',
            project_id=getattr(state, 'project_id', project_root.name),
        )

        # Reserve conservative disk headroom before running. Two input-file
        # sizes accommodates most SU transforms while preventing disk abuse.
        expected_output_bytes = max(1, input_path.stat().st_size * 2)
        try:
            enforce_processing_limits(
                project, state, expected_output_bytes=expected_output_bytes
            )
        except Exception as exc:
            audit_event(
                project,
                'processing_rejected_by_security_policy',
                severity='warning',
                details={'tool': tool_name, 'error': str(exc)},
            )
            raise

        try:
            result = self.executor.execute_tool(
                tool_name, input_path, output_path, parameters, state.metadata
            )
        except Exception as exc:
            audit_event(
                project,
                'processing_execution_rejected_or_failed',
                severity='warning',
                details={'tool': tool_name, 'error': str(exc)},
            )
            raise

        command = result.get('command') or []
        command_text = shlex.join([str(part) for part in command]) if command else None
        command_line = (
            f"{command_text} < {shlex.quote(str(input_path))} "
            f"> {shlex.quote(str(output_path))}"
            if command_text
            else None
        )

        record = {
            'step_id': state.current_step + 1,
            'parent_step': state.current_step,
            'tool': tool_name,
            'input': str(input_path),
            'output': str(output_path),
            'parameters': result['parameters'],
            'reason': reason,
            'status': result['status'],
            'duration_sec': result['duration_sec'],
            'command': command,
            'command_line': command_line,
        }
        self.history.append(record)
        audit_event(
            project,
            'processing_executed',
            details={
                'tool': tool_name,
                'step_id': record['step_id'],
                'duration_sec': record['duration_sec'],
            },
        )
        return record
