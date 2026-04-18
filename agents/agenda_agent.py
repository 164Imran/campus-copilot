# agents/agenda_agent.py
# TODO: À implémenter par l'équipe Agenda
#
# Interface requise par l'orchestrateur :
#
#   run_agenda_agent(moodle_data: list[dict]) -> dict
#
#   Paramètre reçu (moodle_data) :
#     Liste de cours extraits par run_moodle_agent(), chaque item contient :
#       - course       (str) : nom du cours
#       - pdf_path     (str) : chemin local vers le PDF (pour extraction des deadlines)
#       - pdf_filename (str) : nom du fichier
#       - summary      (str) : résumé du cours
#
#   Retour attendu (dict) :
#     - new_deadlines (int) : nombre de nouvelles deadlines détectées
#     - ics_url       (str) : URL du calendrier .ics mis à jour
#     - deadlines     (list, optionnel) : liste des deadlines [{title, date, course}]
#
# Exemple de retour :
#   {
#     "new_deadlines": 3,
#     "ics_url": "https://calendar.example.com/student.ics",
#     "deadlines": [
#       {"title": "Homework 4", "date": "2026-04-25", "course": "Analysis 1"}
#     ]
#   }

def run_agenda_agent(moodle_data: list) -> dict:
    raise NotImplementedError("Agent Agenda non encore implémenté")
