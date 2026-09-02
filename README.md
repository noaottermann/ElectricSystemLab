# Nodal

Nodal est une application de simulation de circuits électriques basée sur une interface graphique. Elle permet de concevoir, analyser et simuler des systèmes électriques composés de dipôles, en utilisant différentes méthodes de résolution (DC, AC, transitoire).

## Table des matières

- [Nodal](#nodal)
  - [Table des matières](#table-des-matières)
  - [Caractéristiques](#caractéristiques)
  - [Prérequis](#prérequis)
  - [Installation](#installation)
  - [Utilisation](#utilisation)
    - [Lancement de l'application](#lancement-de-lapplication)
    - [Interface utilisateur](#interface-utilisateur)
    - [Workflow typique](#workflow-typique)
  - [Documentation Complète](#documentation-complète)
  - [Architecture](#architecture)
  - [Structure du projet](#structure-du-projet)
  - [Développement](#développement)
    - [Configuration de l'environnement de développement](#configuration-de-lenvironnement-de-développement)
    - [Conventions de code](#conventions-de-code)
    - [Ajout de nouveaux composants](#ajout-de-nouveaux-composants)
  - [Tests](#tests)
  - [Licence](#licence)

## Caractéristiques

- Interface graphique intuitive basée sur PyQt5
- Création et édition de circuits électriques en mode visuel
- Support de multiples types de dipôles électriques
- Trois moteurs de simulation :
  - Analyse DC (régime continu)
  - Analyse AC (régime harmonique)
  - Analyse transitoire
- Gestion automatique des nœuds et des connexions
- Grille de travail avec alignement magnétique
- Exportation et importation de circuits
- Visualisation graphique des résultats
- Support multilingue (français, anglais)
- Thèmes personnalisables
- Liaisons clavier configurables

## Prérequis

- Python 3.8 ou supérieur
- PyQt5 (>=5.15.9)
- NumPy (>=1.24.0)

## Installation

1. Clonez le dépôt :
```bash
git clone <repository-url>
cd Nodal
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

### Lancement de l'application

Exécutez le fichier principal :
```bash
python main.py
```

L'application se lancera avec un écran de démarrage et affichera la fenêtre principale en mode maximisé.

### Interface utilisateur

- **Panneau de composants** : Sélectionnez et ajoutez des dipôles au circuit
- **Panneau d'outils** : Accédez aux outils d'édition (suppression, propriétés, etc.)
- **Grille de travail** : Concevez votre circuit en plaçant et connectant des composants
- **Panneau de graphiques** : Visualisez les résultats de simulation
- **Panneau d'exemples** : Charger des circuits prédéfinis

### Workflow typique

1. Ajoutez des dipôles et des nœuds à votre circuit
2. Connectez les composants avec des fils
3. Configurez les paramètres des composants (valeurs, propriétés)
4. Lancez une simulation (DC, AC ou transitoire)
5. Analysez les résultats via les graphiques et les données

## Documentation Complète

- **[Architecture Technique (ARCHITECTURE.md)](ARCHITECTURE.md)** : Conception MVC détaillée, matrices MNA et patterns.
- **[Guide de Contribution (CONTRIBUTING.md)](CONTRIBUTING.md)** : Guide d'ajout de composants, tests et standards.

## Architecture

L'application suit le pattern Modèle-Vue-Contrôleur (MVC) strict :

- **Modèle** (`model/`) : Physique électrique et graphe topologique agnostiques de Qt (`Component`, `Dipole`, `Circuit`, `Node`, `Wire`).
- **Solveurs** (`solver/`) : Moteurs d'analyse nodale modifiée MNA (`DCSolver`, `ACSolver`, `TransientSolver`) avec stamping polymorphe.
- **Contrôleur** (`controller/`) : Orchestration métier, transformations géométriques, flux de fichiers et simulations.
- **Vue** (`view/`) : Interface PyQt5 modulaire découpée en sous-packages (`view/canvas/`, `view/main_window/`, `view/dialogs/`, `view/components_panel.py`).
- **Persistance** (`persistence/`) : Sérialisation JSON et exportateurs CSV.

## Structure du projet

```
Nodal/
├── main.py                  # Point d'entrée de l'application
├── requirements.txt         # Dépendances Python
├── pyproject.toml           # Configuration Pytest & MyPy
├── AI_AGENT_GUIDE.md        # Guide exhaustif pour IA & développeurs
├── ARCHITECTURE.md          # Documentation technique détaillée
├── CONTRIBUTING.md          # Guide pour les contributeurs
├── README.md                # Présentation générale
├── config/                  # Configuration & constantes physiques
├── model/                   # Modèle de données & composants
├── controller/              # Contrôleurs MVC & services
├── solver/                  # Moteurs de simulation MNA
├── persistence/             # Sérialisation JSON & exports
├── utils/                   # Localisation i18n & gestion d'assets
├── view/                    # Interface graphique modulaire PyQt5
│   ├── canvas/              # Canevas graphique (scène, vue, snap, undo)
│   ├── main_window/         # Fenêtre principale, barres d'outils, menus
│   ├── dialogs/             # Boîtes de dialogue de paramétrage
│   └── components_panel.py  # Palette de composants avec cache d'icônes
├── locales/                 # Fichiers de traduction (fr, en)
└── tests/                   # Suite de tests unitaires et d'intégration
```

## Développement

### Configuration de l'environnement de développement

1. Installez les dépendances de développement :
```bash
pip install -r requirements.txt
```

2. Assurez-vous que la structure du projet est respectée
3. Avant de committer, vérifiez que les tests passent

### Conventions de code

- Format PEP 8
- Documentation des fonctions avec docstrings en français
- Variables et fonctions en français
- Types hints recommandés

### Ajout de nouveaux composants

Pour ajouter un nouveau dipôle :

1. Définissez-le dans `model/components.py`
2. Créez l'icône correspondante dans `assets/components/`
3. Ajoutez les paramètres éditables dans le contrôleur
4. Implémentez le modèle mathématique dans les solveurs concernés

## Tests

Exécutez les tests avec :

```bash
python -m pytest tests/
```

Les tests couvrent :
- Modèle de circuit et composants
- Sérialisation et désérialisation
- Solveurs de simulation
- Interface utilisateur
- Importation/Exportation

## Licence

Ce projet est distribué sous la licence MIT. Consultez le fichier [LICENSE](LICENSE) pour plus de détails.

---

**Auteurs** : Noa Ottermann & Kaveh Khabir
**Version** : 1.0.0
