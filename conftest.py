# conftest.py
import sys, os

# racine du projet
ROOT = os.path.dirname(__file__)

# 1) ajouter src/ au PYTHONPATH pour importer app.app, ms_banque, ms_profilrisque, etc.
sys.path.insert(0, os.path.abspath(os.path.join(ROOT, 'src')))

# 2) ajouter src/ms_montantmax/ au PYTHONPATH pour que
#    `import montantmax_pb2` dans montantmax_pb2_grpc.py fonctionne
sys.path.insert(0, os.path.abspath(os.path.join(ROOT, 'src', 'ms_montantmax')))
