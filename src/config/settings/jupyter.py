try:
    import jupyterlab
    notebook_default_url = '/lab'  # Using JupyterLab
except ImportError:
    notebook_default_url = '/tree'  # Using Jupyter

PATH_TO_NOTEBOOK_DIR = 'C:/projects/ergo_ms/api/src'

NOTEBOOK_ARGUMENTS = [
    '--ip', '0.0.0.0',
    '--port', '8888',
    '--notebook-dir', PATH_TO_NOTEBOOK_DIR,
    '--NotebookApp.default_url', notebook_default_url,
]
IPYTHON_KERNEL_DISPLAY_NAME = 'Django Kernel'

# if you want to use Chrome by default
# os.environ.setdefault('BROWSER', 'google-chrome')