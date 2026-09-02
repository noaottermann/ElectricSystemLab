# Nodal

Nodal est une application de simulation de circuits électriques basée sur une interface graphique. Elle permet de concevoir, analyser et simuler des systèmes électriques composés de dipôles, en utilisant différentes méthodes de résolution (DC, AC, transitoire).

## Table des matières

- [Caractéristiques](#caractéristiques)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Architecture](#architecture)
- [Structure du projet](#structure-du-projet)
- [Développement](#développement)
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

## Architecture

### Modèle MVC

L'application suit le pattern Modèle-Vue-Contrôleur (MVC) :

- **Modèle** (`model/`) : Représentation abstraite du circuit et de ses composants
- **Vue** (`view/`) : Interface graphique et visualisation
- **Contrôleur** (`controller/`) : Logique métier et coordination entre modèle et vue

### Modules principaux

#### Modèle (`model/`)
- `circuit.py` : Classe Circuit, gestion globale du circuit
- `components.py` : Définition des dipôles disponibles
- `dipole.py` : Classe Dipole, composant électrique de base
- `node.py` : Classe Node, nœud du circuit
- `wire.py` : Classe Wire, connexion entre composants

#### Contrôleur (`controller/`)
- `app_controller.py` : Contrôleur principal de l'application
- `circuit_controller.py` : Gestion du circuit
- `simulation_controller.py` : Orchestration des simulations
- `file_controller.py` : Importation et exportation de circuits
- `edit_controller.py` : Édition des composants

#### Vue (`view/`)
- `main_window.py` : Fenêtre principale
- `canvas.py` : Zone de dessin du circuit
- `component_item.py` : Représentation visuelle d'un dipôle
- `node_item.py` : Représentation visuelle d'un nœud
- `wire_item.py` : Représentation visuelle d'une connexion
- `components_panel.py` : Panneau de sélection des composants
- `tools_panel.py` : Panneau d'outils
- `graphs_panel.py` : Panneau de visualisation des résultats
- `examples_panel.py` : Panneau des exemples
- `grid.py` : Grille de travail

#### Solveur (`solver/`)
- `base_solver.py` : Classe de base pour tous les solveurs
- `dc_solver.py` : Solveur pour l'analyse DC
- `ac_solver.py` : Solveur pour l'analyse AC
- `transient_solver.py` : Solveur pour l'analyse transitoire
- `utils.py` : Fonctions utilitaires pour les calculs

#### Utilitaires (`utils/`)
- `translator.py` : Gestion de la localisation
- `assets.py` : Gestion des ressources (icônes, images)

#### Configuration (`config/`)
- `settings.py` : Paramètres applicatifs
- `keybinds.py` : Liaisons clavier
- `themes.py` : Thèmes de l'application

#### Persistance (`persistence/`)
- `serializer.py` : Sérialisation des circuits (JSON)
- `importer.py` : Importation depuis divers formats
- `exporter.py` : Exportation vers divers formats

## Structure du projet

```
Nodal/
├── main.py                  # Point d'entrée de l'application
├── requirements.txt         # Dépendances Python
├── LICENSE                  # Licence MIT
├── README.md               # Ce fichier
├── model/                  # Couche modèle
│   ├── circuit.py
│   ├── components.py
│   ├── dipole.py
│   ├── node.py
│   └── wire.py
├── controller/             # Couche contrôleur
│   ├── app_controller.py
│   ├── circuit_controller.py
│   ├── simulation_controller.py
│   ├── file_controller.py
│   └── edit_controller.py
├── view/                   # Couche vue
│   ├── main_window.py
│   ├── canvas.py
│   ├── component_item.py
│   ├── node_item.py
│   ├── wire_item.py
│   ├── components_panel.py
│   ├── tools_panel.py
│   ├── graphs_panel.py
│   ├── examples_panel.py
│   ├── grid.py
│   └── splash_screen.py
├── solver/                 # Moteurs de simulation
│   ├── base_solver.py
│   ├── dc_solver.py
│   ├── ac_solver.py
│   ├── transient_solver.py
│   ├── stamping.py
│   ├── stamping_registry.py
│   └── utils.py
├── persistence/            # Sérialisation et persistance des circuits
│   ├── serializer.py
│   ├── importer.py
│   └── exporter.py
├── assets/                 # Ressources graphiques
│   ├── categories/
│   ├── components/
│   ├── panels/
│   ├── simulation/
│   ├── toolbar/
│   └── gen_icons_all.py
├── locales/                # Fichiers de traduction
│   ├── fr.json
│   └── en.json
└── tests/                  # Tests unitaires
    ├── test_circuit.py
    ├── test_model.py
    ├── test_solver.py
    ├── test_io.py
    ├── test_simulation_controller.py
    ├── test_graph_panel_utils.py
    ├── test_view_components_panel.py
    ├── test_graphics_button.py
    └── test_interactive_graphs.py
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
