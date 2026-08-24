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

    key = validation.get('below_nyquist')
    if key and key in out and 'nyquist_hz' in context and out[key] >= float(context['nyquist_hz']):
        raise ValidationError(
            f'{key} must be below Nyquist ({float(context["nyquist_hz"]):.3f} Hz).'
        )

    return out
