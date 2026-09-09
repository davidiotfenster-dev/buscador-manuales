import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import database

queries = [
    "CGNAT",
    "sensibilidad",
    "candado",
    "multicast",
    "Wave-1",
    "ruido electrico",
    "motor",
    "finales de carrera"
]

print("=== VERIFICACIÓN DE BÚSQUEDAS SOBRE NUEVOS DOCUMENTOS SAT ===")
for q in queries:
    res = database.buscar(query=q, role="admin")
    manuales = res.get("manuales", [])
    print(f"\n🔍 Consulta: '{q}' -> {len(manuales)} manuales encontrados:")
    for r in manuales[:2]:
        print(f"  📄 [{r['nombre_original']}] (Pág {r['numero_pagina']})")
        frag = r['fragmento'].replace('\n', ' ')[:120]
        print(f"     Snippet: {frag}...")
