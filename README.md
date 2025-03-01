# 🔒 Progiclone : Outil Sécurisé d'Anonymisation de Bases de Données Dolibarr

## 🚀 Présentation

Progiclone est un script Python puissant conçu pour anonymiser de manière sécurisée les données sensibles dans les bases de données Dolibarr, garantissant la confidentialité et la protection des données avec un minimum d'effort.

![Licence GitHub](https://img.shields.io/badge/licence-MIT-blue.svg)
![Version Python](https://img.shields.io/badge/python-3.7+-green.svg)
![Support Base de Données](https://img.shields.io/badge/base%20de%20donn%C3%A9es-MySQL-orange.svg)

## ✨ Fonctionnalités

- 🔐 **Anonymisation Sécurisée des Données** : Remplace les informations sensibles par des données fictives réalistes
- 🌐 **Connectivité Flexible** : Supporte les connexions MySQL directes et via tunnel SSH
- 📊 **Couverture Complète** : Anonymise plusieurs tables de la base Dolibarr
- 🛡️ **Confidentialité des Données** : Préserve la structure des données tout en protégeant les informations personnelles
- 🔧 **Mode Non-Interactif** : Permet l'automatisation via ligne de commande ou fichier de configuration

## 📦 Installation

```bash
# Installation via pipx (recommandé)
pipx install progiclone

# Ou via pip
pip install progiclone
```

## 🔧 Utilisation

### Mode Interactif (par défaut)

```bash
progiclone
```

### Mode Non-Interactif

```bash
# Avec arguments en ligne de commande
progiclone --non-interactive \
    --mysql-host localhost \
    --mysql-user dolibarr \
    --mysql-password secret \
    --mysql-database dolibarr_db

# Avec tunnel SSH
progiclone --non-interactive \
    --use-ssh \
    --ssh-host example.com \
    --ssh-user root \
    --ssh-password ssh_secret \
    --mysql-host localhost \
    --mysql-user dolibarr \
    --mysql-password secret \
    --mysql-database dolibarr_db

# Avec un fichier de configuration
progiclone --non-interactive --config config.yml

# Anonymiser des tables spécifiques
progiclone --tables llx_societe llx_socpeople

# Afficher la version
progiclone --version

# Afficher l'aide
progiclone --help
```

### Configuration via Fichier

Vous pouvez créer un fichier de configuration YAML ou JSON. Exemple (config.yml) :

```yaml
mysql:
  host: localhost
  port: 3306
  user: dolibarr
  password: your_password
  database: dolibarr_db

# Configuration SSH (optionnelle)
ssh:
  host: example.com
  port: 22
  user: ssh_user
  password: ssh_password  # Soit password soit key
  key: ~/.ssh/id_rsa     # Chemin vers votre clé SSH

# Tables à anonymiser (optionnel)
tables:
  - llx_societe
  - llx_socpeople
  - llx_user
```

## 🛠 Tables Prises en Charge

Le script anonymise les tables Dolibarr suivantes :
- Tiers (llx_societe)
- Contacts (llx_socpeople)
- Utilisateurs (llx_user)
- Factures clients (llx_facture)
- Devis/Propositions commerciales (llx_propal)
- Commandes clients (llx_commande)
- Contrats (llx_contrat)
- Factures fournisseurs (llx_facture_fourn)
- Commandes fournisseurs (llx_commande_fournisseur)
- Projets (llx_projet)
- Tickets (llx_ticket)
- Événements/Actions (llx_actioncomm)

## 🔐 Méthodes de Connexion

1. **Connexion Chiffrée via SSH** (Recommandée)
   - Tunnel SSH sécurisé
   - Accès à la base de données chiffré
   - Sécurité avancée pour les serveurs distants

2. **Connexion MySQL Standard**
   - Connexion MySQL directe
   - Adaptée aux réseaux locaux ou de confiance

## 🛡️ Options de Connexion

1. Choisissez entre connexion SSH ou MySQL standard
2. Saisissez les informations de connexion (hôte, utilisateur, base de données)
3. Sélectionnez les tables à anonymiser

## ⚠️ Avertissement Important

- **Toujours effectuer une sauvegarde complète avant l'anonymisation**
- L'opération est **irréversible**
- À utiliser de préférence sur une base de données de test

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci de :
- Forker le projet
- Créer une branche de fonctionnalité
- Soumettre une pull request

## 📄 Licence

Distribué sous Licence MIT. Voir `LICENCE` pour plus d'informations.

## 👥 Créé par

VLTN x Progiseize

---

**🚨 Utilisation Responsable 🚨**
Cet outil est destiné à la protection des données personnelles. Utilisez-le de manière éthique et conformément aux réglementations en vigueur.