"""Execute with this Python interpreter, then create a portable HTML notebook."""
import json
import sys
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client.kernelspec import KernelSpecManager

root = Path(__file__).resolve().parents[1]
path = root / 'notebooks/airline_delay_analysis.ipynb'
nb = nbformat.read(path, as_version=4)
kernel_name = 'airline-project-' + uuid.uuid4().hex[:10]
with TemporaryDirectory() as directory:
    spec = Path(directory) / 'kernel'
    spec.mkdir()
    (spec / 'kernel.json').write_text(json.dumps({
        'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        'display_name': 'Airline project Python', 'language': 'python'}))
    manager = KernelSpecManager()
    manager.install_kernel_spec(str(spec), kernel_name=kernel_name, user=True)
    try:
        NotebookClient(nb, timeout=600, kernel_name=kernel_name,
                       resources={'metadata': {'path': str(root)}}).execute()
    finally:
        manager.remove_kernel_spec(kernel_name)
nbformat.write(nb, path)
body, _ = HTMLExporter().from_notebook_node(nb)
(root / 'reports/notebook.html').write_text(body)
print('Executed notebook and exported reports/notebook.html')
