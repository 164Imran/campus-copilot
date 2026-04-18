# CLAUDE.md — Campus Co-Pilot Orchestrateur

## Contexte
Hackathon TUM.ai Makeathon 2026 — Challenge Reply.
Construire un agent autonome qui transforme la vie étudiante à TUM.
Mon rôle : **orchestrateur central** qui route les demandes vers les bons agents.

## Stack imposé
- **LLM** : AWS Bedrock — Claude Sonnet (via boto3)
- **Backend** : Python + FastAPI
- **Pas de LangGraph** — trop complexe pour 48h, on fait du routing simple
- **Credentials AWS** : dans le fichier `.env`

## Structure du projet
```
hacks/
├── CLAUDE.md
├── .env                    # Credentials AWS + TUM
├── main.py                 # Point d'entrée FastAPI
├── orchestrator.py         # MON FICHIER PRINCIPAL
├── bedrock_client.py       # Client Claude centralisé
└── agents/
    ├── __init__.py
    ├── moodle_agent.py     # Fait par quelqu'un d'autre
    ├── agenda_agent.py     # Fait par quelqu'un d'autre
    └── room_agent.py       # Fait par quelqu'un d'autre
```

## Règles absolues
1. **Ne jamais modifier les fichiers dans agents/** — ce sont les autres membres de l'équipe
2. **Toujours avoir un fallback mock** si un agent plante
3. **Le routing doit fonctionner même si un agent est vide**
4. **Toutes les clés API dans .env, jamais dans le code**
5. **Feature Freeze samedi 22h — pas de nouvelles features après**

## Variables d'environnement requises
```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=xxxxx
AWS_DEFAULT_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5
```

## Ce que fait l'orchestrateur
1. Reçoit un message utilisateur en langage naturel
2. Appelle Claude pour décider quels agents sont nécessaires
3. Appelle les agents dans le bon ordre
4. Synthétise une réponse finale avec Claude
5. Retourne la réponse + les résultats bruts au frontend

## Agents disponibles
- **moodle** : résumer des cours, slides, nouveaux fichiers Moodle
  - ✅ **Connexion Moodle fonctionnelle** — extraction des cours en PDF opérationnelle
  - `run_moodle_agent()` retourne une liste de dicts : `{course, pdf_path, pdf_filename, summary}`
  - Le PDF est extrait localement et le chemin est passé à l'agent agenda pour en extraire les deadlines
- **agenda** : deadlines, calendrier, dates importantes
  - Reçoit `moodle_data` (liste de cours avec `pdf_path`) pour en extraire les deadlines
- **room** : réserver une salle d'étude, espace de travail

## Philosophie MVP
- Un agent qui répond avec un mock > un agent qui plante
- Le routing doit marcher en toutes circonstances
- La démo phrase : "Résume mes cours, ajoute les deadlines et réserve une salle demain à 14h"
- Cette phrase doit déclencher les 3 agents en cascade

## Commandes utiles
```bash
# Lancer le serveur
uvicorn main:app --reload --port 8000

# Tester l'orchestrateur directement
python orchestrator.py

# Vérifier Bedrock
python bedrock_client.py
```
