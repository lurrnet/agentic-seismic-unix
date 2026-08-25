import shlex


class WorkflowEngine:
    def __init__(self, executor, history):
        self.executor = executor
        self.history = history

    def run_processing_step(
        self, state, tool_name, input_path, output_path, parameters, reason
    ):
        result = self.executor.execute_tool(
            tool_name, input_path, output_path, parameters, state.metadata
        )

        command = result.get('command') or []
        command_text = shlex.join([str(part) for part in command]) if command else None
        if command_text:
            command_line = (
                f"{command_text} < {shlex.quote(str(input_path))} "
                f"> {shlex.quote(str(output_path))}"
            )
        else:
            command_line = None

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
        return record
