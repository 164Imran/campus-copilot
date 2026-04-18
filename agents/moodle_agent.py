# agents/moodle_agent.py
# TODO: À implémenter par l'équipe Moodle
#
# Interface requise par l'orchestrateur :
#
#   run_moodle_agent() -> list[dict]
#
#   Chaque dict doit contenir :
#     - course       (str)  : nom du cours, ex: "Analysis 1"
#     - pdf_path     (str)  : chemin local vers le PDF extrait, ex: "/tmp/analysis1.pdf"
#     - pdf_filename (str)  : nom du fichier PDF, ex: "analysis1_week10.pdf"
#     - summary      (str)  : résumé textuel du cours
#
# Exemple de retour :
#   [
#     {
#       "course": "Analysis 1",
#       "pdf_path": "/tmp/analysis1.pdf",
#       "pdf_filename": "analysis1_week10.pdf",
#       "summary": "Intégrales de Riemann, convergence des séries..."
#     },
#     ...
#   ]

def run_moodle_agent() -> list:
    raise NotImplementedError("Agent Moodle non encore implémenté")
