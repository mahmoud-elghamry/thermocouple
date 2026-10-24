"""JLC model rotations; 24-channel values came from its 2026-10-21 preview.

The other board profiles reuse package offsets as hypotheses. Their complete
polarized-reference lists must be checked in each new JLC placement preview.
"""

_PACKAGE = (
    ('TQFP-', 270), ('SOIC-', 270), ('HSOP-', 270),
    ('SOT-23', 180), ('SOT-363', 180), ('LED_D3.0mm', 180),
    ('PinHeader_', 270), ('Relay_DPDT_Omron_G6K', 270),
    ('Converter_DCDC_Murata_CRE1', 270),
)
ROTATIONS = {key: _PACKAGE for key in ('24', '8', '8l', '40')}
PREVIEW_CONFIRMED = {'24': '2026-10-21, REV A4 24-channel preview (release 011858)'}


def rotation(key, package):
    return next((degrees for prefix, degrees in ROTATIONS[key] if package.startswith(prefix)), 0)
