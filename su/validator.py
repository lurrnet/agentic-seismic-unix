class ValidationError(ValueError):
    pass


def validate_parameters(tool_spec, parameters, context=None):
    context = context or {}
    schema = tool_spec.get('parameters', {})
    out = {}

    for name, spec in schema.items():
        if name not in parameters:
            if 'default' in spec:
                value = spec['default']
            elif spec.get('required'):
                raise ValidationError(f'Missing required parameter: {name}')
            else:
                continue
        else:
            value = parameters[name]

        if spec.get('type') == 'float':
            value = float(value)
        elif spec.get('type') == 'int':
            value = int(value)
        elif spec.get('type') == 'string':
            value = str(value).strip()
            if not value:
                raise ValidationError(f'{name} must not be empty.')
        elif spec.get('type') == 'float_list':
            if isinstance(value, str):
                parts = [part.strip() for part in value.split(',') if part.strip()]
            elif isinstance(value, (list, tuple)):
                parts = list(value)
            else:
                raise ValidationError(f'{name} must be a numeric list.')
            try:
                value = [float(item) for item in parts]
            except (TypeError, ValueError) as exc:
                raise ValidationError(f'{name} must contain only numeric values.') from exc
            if len(value) < int(spec.get('min_items', 0)):
                raise ValidationError(f'{name} must contain at least {spec["min_items"]} values.')
            if 'max_items' in spec and len(value) > int(spec['max_items']):
                raise ValidationError(f'{name} must contain at most {spec["max_items"]} values.')

        if 'minimum' in spec and value < spec['minimum']:
            raise ValidationError(f'{name} must be >= {spec["minimum"]}')
        if 'maximum' in spec and value > spec['maximum']:
            raise ValidationError(f'{name} must be <= {spec["maximum"]}')
        if 'choices' in spec and value not in spec['choices']:
            allowed = ', '.join(str(x) for x in spec['choices'])
            raise ValidationError(f'{name} must be one of: {allowed}')
        out[name] = value

    validation = tool_spec.get('validation', {})
    if validation.get('ordered_frequencies'):
        vals = [out.get(k) for k in ('f1', 'f2', 'f3', 'f4')]
        if None not in vals and not (0 <= vals[0] < vals[1] < vals[2] < vals[3]):
            raise ValidationError('Frequencies must satisfy 0 <= F1 < F2 < F3 < F4.')

    if validation.get('ordered_bounds'):
        if 'min' in out and 'max' in out and not out['min'] <= out['max']:
            raise ValidationError('Selection bounds must satisfy min <= max.')

    same_length = validation.get('same_length')
    if same_length:
        lengths = [len(out[name]) for name in same_length if name in out]
        if len(lengths) == len(same_length) and len(set(lengths)) != 1:
            raise ValidationError(
                f'{" and ".join(same_length)} must contain the same number of values.'
            )

    ordered_list = validation.get('ordered_list')
    if ordered_list and ordered_list in out:
        values = out[ordered_list]
        if any(values[i] >= values[i + 1] for i in range(len(values) - 1)):
            raise ValidationError(f'{ordered_list} values must be strictly increasing.')

    time_list = validation.get('time_list_within_trace')
    if time_list and time_list in out:
        dt_s = float(context.get('dt_s', 0.0) or 0.0)
        ns = int(context.get('ns', 0) or 0)
        if dt_s > 0 and ns > 0:
            max_time = (ns - 1) * dt_s
            if any(value < 0 or value > max_time for value in out[time_list]):
                raise ValidationError(
                    f'{time_list} values must be within trace time range 0 to {max_time:.6g} s.'
                )

    key = validation.get('below_nyquist')
    if key and key in out and 'nyquist_hz' in context and out[key] >= float(context['nyquist_hz']):
        raise ValidationError(
            f'{key} must be below Nyquist ({float(context["nyquist_hz"]):.3f} Hz).'
        )

    return out
