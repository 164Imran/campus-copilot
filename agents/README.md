# 🤖 Campus Copilot - Agents System

Ce dossier contient les agents intelligents du projet **Campus Copilot**, conçus pour automatiser la vie étudiante à la TUM.

## 🏢 1. Room Agent (`room_agent.py`)
Cet agent s'occupe de la gestion des réservations de salles de bibliothèque via le système officiel (SSO).

*   **Comment le lancer** :
    ```bash
    python agents/room_agent.py utiliser la fonction run_room_agent("Votre demande en langage naturel")
    ```
*   **Possibilités** :
    *   **Réserver** : *"Réserve-moi une salle pour demain à 14h"*
    *   **Annuler** : *"Annule ma réservation de mardi prochain"*
    *   **Vérifier** : *"Est-ce que j'ai une salle réservée pour jeudi ?"*

---

## 📅 2. Calendar Agent (`calendar_agent.py`)
Cet agent est le cerveau de votre emploi du temps. Il fusionne plusieurs sources pour créer un calendrier unique.

*   **Comment le lancer** (pour un test ou une synchro rapide) :
    ```bash
    python agents/calendar_agent.py
    ```
*   **Fonctionnalités Clés** :
    1.  **`sync_calendar`** : Fusionne automatiquement :
        *   Votre emploi du temps **TUMonline** (via l'URL ICAL).
        *   Vos **réservations de salles** effectuées par le Room Agent.
        *   Vos **événements manuels** (`manual_events.json`).
    2.  **`add_event`** : Permet d'ajouter manuellement un événement personnel qui sera persisté (ex: Mariage, Déjeuner, etc.).
    3.  **`get_user_schedule`** : Analyse votre emploi du temps pour les prochains jours pour vérifier vos disponibilités.

---

## 📂 Structure des Données
*   **`agent-booking/reservation_history.json`** : Historique de vos réservations de salles.
*   **`agent-calendar/manual_events.json`** : Vos événements ajoutés manuellement.
*   **`agent-calendar/local_event.ics`** : **Le fichier final fusionné** que vous pouvez importer dans Google Calendar ou Apple Calendar.

---
