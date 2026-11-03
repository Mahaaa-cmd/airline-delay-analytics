"""Re-fetch the exact official request and verify against the bundled snapshot.

The endpoint is mutable. If BTS revises the results, stop instead of overwriting
the project's raw evidence. The preserved snapshot remains fully reproducible.
"""
import hashlib
import json
import io
import zipfile
from pathlib import Path
import requests

root = Path(__file__).resolve().parents[1] / 'data/raw'
provenance = json.loads((root / 'provenance.json').read_text())
response = requests.get(provenance['download_url'], timeout=240)
response.raise_for_status()
name = 'bts_delay_causes_2018_2025.zip'
with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
    csv = archive.read('Airline_Delay_Cause.csv')
expected = provenance['files']['Airline_Delay_Cause.csv']['sha256']
if hashlib.sha256(csv).hexdigest() != expected:
    raise SystemExit('BTS returned revised CSV data. Bundled snapshot was not changed. '
                     'Audit the new snapshot separately before updating provenance.')
if hashlib.sha256(response.content).hexdigest() == provenance['files'][name]['sha256']:
    print('Archive and CSV match the original snapshot exactly.')
else:
    print('CSV matches the original snapshot exactly; ZIP container bytes differ (for example, timestamps).')
print('Preserved original files were not overwritten.')
