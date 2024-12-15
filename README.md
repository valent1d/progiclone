# 🔒 Doliclone : Outil Sécurisé d'Anonymisation de Bases de Données Dolibarr

## 🚀 Présentation

Doliclone est un script Python puissant conçu pour anonymiser de manière sécurisée les données sensibles dans les bases de données Dolibarr, garantissant la confidentialité et la protection des données avec un minimum d'effort.

![Licence GitHub](https://img.shields.io/badge/licence-MIT-blue.svg)
![Version Python](https://img.shields.io/badge/python-3.7+-green.svg)
![Support Base de Données](https://img.shields.io/badge/base%20de%20donn%C3%A9es-MySQL-orange.svg)

## ✨ Fonctionnalités

- 🔐 **Anonymisation Sécurisée des Données** : Remplace les informations sensibles par des données fictives réalistes
- 🌐 **Connectivité Flexible** : Supporte les connexions MySQL directes et via tunnel SSH
- 📊 **Couverture Complète** : Anonymise plusieurs tables de la base Dolibarr
- 🛡️ **Confidentialité des Données** : Préserve la structure des données tout en protégeant les informations personnelles

## 🛠 Tables Prises en Charge

Le script anonymise les tables Dolibarr suivantes :
- Tiers
- Contacts
- Utilisateurs
- Factures clients
- Devis/Propositions commerciales
- Commandes clients
- Contrats
- Factures fournisseurs
- Commandes fournisseurs
- Projets
- Tickets
- Événements/Actions

## 🔐 Méthodes de Connexion

1. **Connexion Chiffrée via SSH** (Recommandée)
   - Tunnel SSH sécurisé
   - Accès à la base de données chiffré
   - Sécurité avancée pour les serveurs distants

2. **Connexion MySQL Standard**
   - Connexion MySQL directe
   - Adaptée aux réseaux locaux ou de confiance

## 📦 Prérequis

- Python 3.7+
- Connecteur MySQL
- Tunnel SSH (optionnel, pour les connexions chiffrées)

## 🚀 Installation

```bash
# Cloner le dépôt
git clone https://github.com/valent1d/progiclone
```

## 🔧 Utilisation

```bash
# Exécuter le script
python VLTN-progiclone-script.py
```

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
