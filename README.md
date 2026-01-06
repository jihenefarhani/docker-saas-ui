# 🐳 Docker SaaS UI – Python Project

## 📌 Présentation générale
**Docker SaaS UI** est une application web développée en **Python (Flask)** permettant de gérer des conteneurs Docker via une interface graphique moderne et intuitive, sans recourir directement à la ligne de commande.

L’application adopte une approche **SaaS (Software as a Service)** en intégrant :
- l’authentification des utilisateurs,
- la gestion des rôles (administrateur / utilisateur),
- l’automatisation des opérations Docker,
- la supervision en temps réel des ressources système.

📚 Ce projet a été réalisé dans le cadre d’un **projet académique Python** au cours de l’année universitaire.

---

## 🎯 Objectifs du projet
- Simplifier l’administration des conteneurs Docker
- Éviter l’utilisation directe et complexe de la CLI Docker
- Automatiser les opérations courantes (création, démarrage, arrêt, suppression)
- Fournir une interface sécurisée avec contrôle d’accès par rôle
- Mettre en pratique le développement web backend avec Python
- Appliquer des notions DevOps (Docker, supervision, logs)

---

## 🛠️ Technologies utilisées
- **Python 3.10+**
- **Flask**
- **Flask-Login**
- **Flask-SQLAlchemy**
- **Docker SDK for Python**
- **SQLite**
- **HTML / CSS / JavaScript**
- **Docker (Linux uniquement)**

---

## 📂 Structure du projet
```

docker-saas-ui/
├── app/
│ ├── app.py # Application Flask principale
│ ├── templates/ # Fichiers HTML
│ ├── static/ # CSS / JS
│ └── nginx_sites/ # Sites Nginx générés dynamiquement
├── instance/
│ └── users.db # Base de données SQLite
├── logs/
│ └── actions.log # Journal des actions
├── requirements.txt
├── README.md


```

---

## 🧪 Prérequis
- Système **Linux** (Ubuntu, Debian, Rocky Linux, etc.)
- **Python 3.10** ou supérieur
- **Docker** installé et en cours d’exécution
- Accès au socket Docker : `/var/run/docker.sock`

⚠️ **Docker sur Windows n’est pas supporté** pour ce projet.

---

## ⚙️ Installation et configuration

### 1️⃣ Cloner le projet
```bash
git clone https://github.com/jihenefarhani/docker-saas-ui.git
cd docker-saas-ui
```

### 2️⃣ Créer et activer l’environnement virtuel
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3️⃣ Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4️⃣ Initialiser la base de données
```bash
python
```

```bash
from app.app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    db.session.add(User(
        username="admin",
        password=generate_password_hash("admin123"),
        role="admin"
    ))
    db.session.add(User(
        username="user",
        password=generate_password_hash("user123"),
        role="user"
    ))
    db.session.commit()

```
```bash
exit()
```

### 5️⃣ Lancer l’application
```bash 
python app/app.py
```
---

## 🌐 Accès à l’application

URL : http://localhost:5000

---

## 📊 Fonctionnalités principales

- Authentification sécurisée

- Tableau de bord des conteneurs Docker

- Création de conteneurs (Nginx, applications Python)

- Start / Stop / Delete

- Logs en temps réel

- Supervision CPU / RAM

- Interface moderne type SaaS
