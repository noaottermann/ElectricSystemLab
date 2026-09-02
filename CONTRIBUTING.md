# Guide de Contribution - Nodal Circuit Simulator

Merci de votre intérêt pour le développement de **Nodal** ! Ce document fournit toutes les directives nécessaires pour configurer votre environnement, développer de nouveaux composants ou fonctionnalités, et soumettre vos contributions en respectant les standards de qualité du projet.

---

## 1. Environnement de Développement

### Prérequis
- **Python 3.10+** (compatible 3.11, 3.12, 3.13, 3.14)
- **Git**

### Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/noaottermann/Nodal.git
cd Nodal

# 2. Créer un environnement virtuel
python -m venv .venv

# Sous Linux/macOS :
source .venv/bin/activate
# Sous Windows (PowerShell) :
.venv\Scripts\Activate.ps1

# 3. Installer les dépendances
pip install -r requirements.txt
pip install pytest pytest-cov mypy
```

### Vérification de l'installation

```bash
# Exécuter l'ensemble des tests
pytest

# Vérifier le typage statique
mypy model solver persistence config utils controller
```

---

## 2. Standards de Code

### 2.1. Typage Statique (MyPy)
- Tout nouveau code doit être **intégralement typé** avec les annotations standard Python 3.10+ (`int | None`, `list[str]`, etc.).
- Ne pas introduire de types implicites `Any` non justifiés.
- La commande `mypy` doit s'exécuter avec **0 erreur**.

### 2.2. Documentation (Google Docstrings)
Toutes les fonctions, méthodes et classes publiques doivent comporter une docstring au format Google :

```python
def solve(self, circuit: Circuit, duration: float = 0.01) -> dict[str, Any]:
    """Exécute l'analyse transitoire temporelle du circuit.

    Construit le système d'équations nodales modifiées (MNA) à chaque pas
    de temps et calcule les potentiels de nœuds et courants de branches.

    Args:
        circuit: Instance du circuit à simuler.
        duration: Durée totale de la simulation en secondes (défaut: 0.01s).

    Returns:
        Dictionnaire contenant l'axe temporel ('time') et les traces nodales.

    Raises:
        ValueError: Si le circuit ne comporte aucun nœud de masse (GND).
    """
```

### 2.3. Couverture de Tests
- Chaque nouvelle fonctionnalité ou correction de bogue doit être accompagnée de **tests unitaires correspondants** dans le dossier `tests/`.
- La couverture globale du projet doit être maintenue à **$\ge 80\%$**.

---

## 3. Comment Ajouter un Nouveau Composant Électrique

L'ajout d'un composant électrique s'effectue en 4 étapes simples grâce à l'architecture polymorphe de Nodal :

### Étape 1 : Créer la classe Modèle (`model/components.py`)

Héritez de [`Dipole`](file:///model/dipole.py) (2 bornes) ou de [`Component`](file:///model/component.py) ($N$ bornes) :

```python
class Memristor(Dipole):
    """Composant à résistance mémoire (Memristor)."""

    def __init__(
        self,
        dipole_id: int,
        node_a: Optional[Any],
        node_b: Optional[Any],
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        memristance: float = 1000.0,
    ) -> None:
        super().__init__(dipole_id, "Memristor", node_a, node_b, x=x, y=y, rotation=rotation)
        self.memristance = float(memristance)

    def get_params(self) -> dict[str, object]:
        return {"memristance": self.memristance}

    def set_params(self, params: dict[str, Any]) -> None:
        if "memristance" in params:
            self.memristance = float(params["memristance"])
```

### Étape 2 : Implémenter les fonctions de Stamping MNA (`solver/stamping.py`)

Définissez les fonctions d'estampillage matriciel pour les régimes DC, AC et Transitoire :

```python
def stamp_memristor_dc(component: Memristor, context: StampingContext) -> None:
    """Estampillage DC pour un memristor."""
    r_val = max(1e-9, component.memristance)
    g_val = 1.0 / r_val
    MatrixStamper.stamp_conductance(component.node_a, component.node_b, g_val, context)
```

Enregistrez ces fonctions dans [`solver/stamping_registry.py`](file:///solver/stamping_registry.py) :
```python
REGISTRY.register(Memristor, "dc", stamp_memristor_dc)
```

### Étape 3 : Créer l'Item Graphique (`view/component_item.py`)

Créez la classe de rendu graphique héritant de `ComponentItem` avec la méthode `paint(painter, option)` définissant le symbole normalisé.

### Étape 4 : Déclarer dans le Panneau & l'Éditeur

1. Ajoutez l'identifiant dans [`view/canvas/canvas_editing.py:EditingManager`](file:///view/canvas/canvas_editing.py).
2. Ajoutez l'entrée dans la catégorie correspondante dans [`view/components_panel.py`](file:///view/components_panel.py).
3. Ajoutez les tests unitaires dans `tests/test_model_comprehensive.py` et `tests/test_solvers_comprehensive.py`.

---

## 4. Processus de Contribution (Pull Requests)

1. **Créer une branche descriptive** :
   ```bash
   git checkout -b feat/ajout-memristor
   ```
2. **Écrire le code et les tests unitaires**.
3. **Valider localement la suite de tests et le typage** :
   ```bash
   pytest --cov
   mypy model solver persistence config utils controller
   ```
4. **Commiter avec des messages clairs et conventionnels** :
   - `feat: ajout du support du composant memristor`
   - `fix: correction du calcul de courant dans les transformateurs`
   - `test: ajout des tests de validation transitoire`
5. **Ouvrir une Pull Request** sur GitHub avec une description détaillée des changements et des captures d'écran si l'interface graphique est modifiée.