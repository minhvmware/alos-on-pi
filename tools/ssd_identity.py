"""Explicit opt-in identity for offline maintenance scripts."""
import os


def expected_ssd_serial():
    value = os.environ.get('HOSHINO_SSD_SERIAL', '').strip()
    if not value or value == 'YOUR_SSD_SERIAL':
        raise RuntimeError('Set HOSHINO_SSD_SERIAL to the verified target SSD serial')
    return value
