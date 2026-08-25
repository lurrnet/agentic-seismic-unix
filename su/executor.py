from pathlib import Path
import subprocess
import threading
import time

from security.policy import get_security_limits
from .validator import validate_parameters


class SUExecutionError(RuntimeError):
    pass


_EXECUTION_LOCK = threading.Lock()


def _decode(data):
    return (data or b'').decode('utf-8', errors='replace')


def _format_value(value):
    if isinstance(value, (list, tuple)):
        return ','.join(f'{float(item):g}' for item in value)
    return value


class SUExecutor:
    def __init__(self, registry):
        self.registry = registry

    def run_binary(self, args, stdin_path=None, stdout_path=None):
        fin = fout = None
        started = time.perf_counter()
        timeout = get_security_limits()['su_timeout_seconds']
        if not _EXECUTION_LOCK.acquire(blocking=False):
            raise SUExecutionError(
                'Another Seismic Unix processing job is already running. '
                'Concurrent SU execution is disabled by the security policy.'
            )
        try:
            if stdin_path is not None:
                fin = open(stdin_path, 'rb')
            if stdout_path is not None:
                fout = open(stdout_path, 'wb')
            try:
                process = subprocess.run(
                    args,
                    stdin=fin,
                    stdout=fout if fout else subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired as exc:
                raise SUExecutionError(
                    f'Command exceeded security timeout of {timeout} seconds: '
                    f'{" ".join(str(x) for x in args)}'
                ) from exc
            if process.returncode != 0:
                raise SUExecutionError(
                    f'Command failed ({process.returncode}): '
                    f'{" ".join(str(x) for x in args)}\n{_decode(process.stderr)}'
                )
            return {
                'status': 'success',
                'command': args,
                'duration_sec': time.perf_counter() - started,
                'stdout': _decode(process.stdout),
                'stderr': _decode(process.stderr),
            }
        finally:
            if fin:
                fin.close()
            if fout:
                fout.close()
            _EXECUTION_LOCK.release()

    def execute_tool(self, tool_name, input_path, output_path, parameters, context=None):
        spec = self.registry.get(tool_name)
        params = validate_parameters(spec, parameters, context=context)
        execution = spec.get('execution', {})
        executable = execution.get('executable')
        if not executable:
            raise SUExecutionError(f'Tool {tool_name} has no executable definition.')
        formatted = {key: _format_value(value) for key, value in params.items()}
        args = [executable] + [
            template.format(**formatted)
            for template in execution.get('argument_template', [])
        ]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = self.run_binary(args, stdin_path=input_path, stdout_path=output_path)
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise SUExecutionError(f'{tool_name} produced an empty output file.')
        except Exception:
            try:
                if output_path.exists():
                    output_path.unlink()
            except OSError:
                pass
            raise
        result.update({
            'tool': tool_name,
            'input': str(input_path),
            'output': str(output_path),
            'parameters': params,
        })
        return result
