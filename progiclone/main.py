# Vérifier les dépendances avant tout
def check_dependencies():
    """Vérifie et installe les dépendances requises."""
    required_packages = [
        'pyfiglet',
        'tqdm',
        'Faker',
        'mysql-connector-python',
        'requests',
        'PyYAML',
        'sshtunnel',
    ]

    def install(package):
        print(f"Installation de {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError:
            print(f"\033[91mErreur lors de l'installation de {package}. Tentative avec pip3...\033[0m")
            try:
                subprocess.check_call(["pip3", "install", package])
            except subprocess.CalledProcessError:
                print(f"\033[91mÉchec de l'installation de {package}. Veuillez l'installer manuellement avec 'pip install {package}'\033[0m")
                sys.exit(1)

    print("Vérification des dépendances...")
    for package in required_packages:
        try:
            if package == 'PyYAML':
                import yaml
            elif package == 'mysql-connector-python':
                import mysql.connector
            else:
                __import__(package.lower().replace('-', '_'))
        except ImportError:
            print(f"Le module '{package}' est manquant. Installation automatique...")
            install(package)

    print("\n\033[92mToutes les dépendances sont présentes ou ont été installées avec succès.\033[0m\n")

# Vérifier les dépendances avant tout
if __name__ == "__main__":
    check_dependencies()

# Imports standards
import sys
import os
import shutil
import subprocess
import logging
import argparse
import json
import getpass  # Pour masquer le mot de passe lors de la saisie
import time
import signal
from importlib import import_module
import requests
from progiclone import __version__

def parse_args():
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Progiclone - Outil d'anonymisation sécurisé pour Dolibarr",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--version', action='version', version=f'Progiclone version {__version__}')
    
    # Arguments pour le mode non-interactif
    parser.add_argument('--non-interactive', action='store_true',
                       help='Exécuter en mode non-interactif')
    
    # Configuration MySQL
    mysql_group = parser.add_argument_group('Configuration MySQL')
    mysql_group.add_argument('--mysql-host', help='Hôte MySQL')
    mysql_group.add_argument('--mysql-port', type=int, default=3306, help='Port MySQL (défaut: 3306)')
    mysql_group.add_argument('--mysql-user', help='Utilisateur MySQL')
    mysql_group.add_argument('--mysql-password', help='Mot de passe MySQL')
    mysql_group.add_argument('--mysql-database', help='Nom de la base de données')
    
    # Configuration SSH
    ssh_group = parser.add_argument_group('Configuration SSH Tunnel')
    ssh_group.add_argument('--use-ssh', action='store_true', help='Utiliser un tunnel SSH')
    ssh_group.add_argument('--ssh-host', help='Hôte SSH')
    ssh_group.add_argument('--ssh-port', type=int, default=22, help='Port SSH (défaut: 22)')
    ssh_group.add_argument('--ssh-user', help='Utilisateur SSH')
    ssh_group.add_argument('--ssh-password', help='Mot de passe SSH')
    ssh_group.add_argument('--ssh-key', help='Chemin vers la clé SSH privée')
    
    # Configuration via fichier
    parser.add_argument('--config', help='Chemin vers le fichier de configuration (JSON ou YAML)')
    
    # Tables à anonymiser
    parser.add_argument('--tables', nargs='+', help='Liste des tables à anonymiser (toutes si non spécifié)')
    
    # Mode verbeux
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    
    return parser.parse_args()

def load_config_file(config_path):
    """Charge la configuration depuis un fichier JSON ou YAML."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Le fichier de configuration {config_path} n'existe pas")
    
    ext = os.path.splitext(config_path)[1].lower()
    with open(config_path, 'r') as f:
        if ext == '.json':
            return json.load(f)
        elif ext in ['.yml', '.yaml']:
            return yaml.safe_load(f)
        else:
            raise ValueError("Le fichier de configuration doit être au format JSON ou YAML")

def get_config_from_args(args):
    """Construit la configuration à partir des arguments CLI ou du fichier de config."""
    if args.config:
        config = load_config_file(args.config)
    else:
        config = {
            'mysql': {
                'host': args.mysql_host,
                'port': args.mysql_port,
                'user': args.mysql_user,
                'password': args.mysql_password,
                'database': args.mysql_database
            }
        }
        
        if args.use_ssh:
            config['ssh'] = {
                'host': args.ssh_host,
                'port': args.ssh_port,
                'user': args.ssh_user,
                'password': args.ssh_password,
                'key': args.ssh_key
            }
            
        if args.tables:
            config['tables'] = args.tables
            
    return config

def check_updates():
    try:
        response = requests.get("https://pypi.org/pypi/progiclone/json", timeout=5)
        if response.status_code != 200:
            logging.debug(f"Erreur lors de la vérification des mises à jour : Code {response.status_code}")
            return
            
        latest = response.json()["info"]["version"]
        if latest > __version__:
            print(f"\n\033[93mNouvelle version {latest} disponible !")
            print("Pour mettre à jour : pipx upgrade progiclone\033[0m\n")
    except requests.Timeout:
        logging.debug("Timeout lors de la vérification des mises à jour")
    except requests.RequestException as e:
        logging.debug(f"Erreur réseau lors de la vérification des mises à jour : {str(e)}")
    except (KeyError, ValueError) as e:
        logging.debug(f"Erreur lors du parsing de la réponse PyPI : {str(e)}")
    except Exception as e:
        logging.debug(f"Erreur inattendue lors de la vérification des mises à jour : {str(e)}")

def is_autossh_installed():
    """Vérifie si autossh est installé."""
    return shutil.which("autossh") is not None

def print_logo():
    logo = r"""

    ____   ____   ____   ______ ____ ______ __    ____   _   __ ______
   / __ \ / __ \ / __ \ / ____//  _// ____// /   / __ \ / | / // ____/
  / /_/ // /_/ // / / // / __  / / / /    / /   / / / //  |/ // __/   
 / ____// _, _// /_/ // /_/ /_/ / / /___ / /___/ /_/ // /|  // /___   
/_/    /_/ |_| \____/ \____//___/ \____//_____/\____//_/ |_//_____/   
                                                                      
    
            ====== Dev by VLTN x Progiseize ======     
    """
    print("\033[96m" + logo + "\033[0m")
    print("===================================================")
    print(" ⚙️  Script d'anonymisation sécurisé pour Dolibarr")
    print("===================================================\n")
    print("\033[1m⚠️  Avant de continuer, assurez-vous d'avoir fait une sauvegarde complète de votre base de données !\033[0m")
    print("\033[1mOu utilisez une base de test. L'opération est irréversible.\033[0m\n")

def confirm_proceed():
    print("\033[93mCe script va procéder à l'anonymisation des données sensibles dans votre base Dolibarr.\033[0m")
    print("\033[93mIl va modifier de nombreuses tables.\033[0m")
    print("\033[93mVoulez-vous continuer ? (Y/N)\033[0m")

    while True:
        choice = input("> ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            print("Veuillez répondre par Y ou N.")

def signal_handler(sig, frame):
    print("\nMerci d'avoir utilisé Progiclone par VLTN x Progiseize. À bientôt 👋!")
    sys.exit(0)

def choose_connection_method():
    print("\nVeuillez choisir une méthode de connexion à la base de données :")
    print("🔐 1 - Connexion MYSQL cryptée via SSH avec autossh (le plus sécurisé) - nécessite un accès SSH au serveur")
    print("🔓 2 - Connexion MySQL standard (non cryptée) A utiliser si vous n'avez pas d'accès SSH au serveur")
    while True:
        choice = input("> ").strip()
        if choice in ['1', '2']:
            return choice
        else:
            print("Veuillez saisir 1 ou 2.")

def get_autossh_info(dev_mode=False):
    """Obtient les informations de connexion SSH."""
    print("\n=== Informations de connexion SSH (pour connexion chiffrée) ===")
    ssh_host = input("🌐 Host SSH (FQDN/IP de votre serveur SSH): ")
    ssh_port = input("🔌 Port SSH (par défaut 22): ") or "22"
    ssh_user = input("🥷 Utilisateur SSH: ")
    use_key = input("🔑 Utiliser une clé SSH ? (Y/N): ").strip().lower()
    ssh_key = None
    ssh_password = None
    if use_key == 'y':
        ssh_key = input("🗃️ Chemin vers la clé SSH privée (ex: ~/.ssh/id_rsa): ")
    else:
        ssh_password = getpass.getpass("🔒 Mot de passe SSH: ")

    return ssh_host, int(ssh_port), ssh_user, ssh_key, ssh_password

def get_mysql_info(dev_mode=False):
    """Obtient les informations de connexion MySQL."""
    print("\n=== Informations de connexion MySQL ===")
    host = input("Host MySQL (FQDN/IP de votre serveur MySQL): ") or "localhost"
    user = input("Utilisateur MySQL: ")
    password = getpass.getpass("Mot de passe MySQL: ")
    database = input("Nom de la base MySQL: ")
    port = input("Port MySQL (par défaut 3306): ") or "3306"
    return host, user, password, database, int(port)

def ask_for_table(cnx, table_name, primary_keys, table_labels):
    from tqdm import tqdm
    from mysql.connector import Error
    # Calcule le nombre de lignes et estime la durée
    cursor = cnx.cursor()
    pk_field = primary_keys.get(table_name, "rowid")
    try:
        cursor.execute(f"SELECT COUNT({pk_field}) FROM {table_name}")
        count_row = cursor.fetchone()[0]
    except Error as err:
        print(f"\033[91mErreur lors du comptage des lignes de {table_name}: {err}\033[0m")
        return False

    estimated_seconds = count_row / 25.0
    if estimated_seconds < 60:
        estimated_time_str = f"{int(estimated_seconds)}s environ"
    else:
        estimated_minutes = estimated_seconds / 60.0
        estimated_time_str = f"{estimated_minutes:.1f} min environ"

    print(f"\n⌛ Estimation du temps pour {table_name}: ~{estimated_time_str}")

    label = table_labels.get(table_name, "")
    print()
    if table_name == "llx_user":
        print("\033[93mNote: Les logins et mots de passe ne seront pas modifiés, le reste le sera.\033[0m\n")

    print(f"Souhaitez-vous anonymiser la table \033[94m{table_name} {label}\033[0m ? (Y/N)")
    while True:
        choice = input("> ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            print("Veuillez répondre par Y ou N.")

def anonymize_table(cnx, table_name, fields_dict, primary_keys, table_labels):
    from tqdm import tqdm
    from mysql.connector import Error
    cursor = cnx.cursor()
    print(f"\n\033[96mAnonymisation de la table {table_name}...\033[0m")
    pk_field = primary_keys.get(table_name, "rowid")

    try:
        cursor.execute(f"SELECT {pk_field} FROM {table_name}")
        rows = cursor.fetchall()
        row_ids = [r[0] for r in rows]
    except Error as err:
        print(f"\033[91mErreur lors de la sélection des IDs de {table_name}: {err}\033[0m")
        return

    if not row_ids:
        print(f"Aucune donnée à anonymiser dans {table_name}.")
        return

    fields_to_update = list(fields_dict.keys())
    set_clause = ", ".join([f"{f}=%s" for f in fields_to_update])

    for rid in tqdm(row_ids, desc=f"Traitement {table_name}", unit="enregistrement"):
        data = [fields_dict[f]() for f in fields_to_update]
        query = f"UPDATE {table_name} SET {set_clause} WHERE {pk_field}=%s"
        try:
            cursor.execute(query, data + [rid])
        except Error as err:
            print(f"\033[91mErreur lors de la mise à jour de {table_name} ID {rid}: {err}\033[0m")
            continue

    try:
        cnx.commit()
        print(f"\033[92mTable {table_name} anonymisée avec succès ! ✅\033[0m")
    except Error as err:
        print(f"\033[91mErreur lors du commit des modifications pour {table_name}: {err}\033[0m")

def anonymize_data(cnx, primary_keys, table_labels, tables_to_anonymize):
    for (table_name, fields_dict) in tables_to_anonymize:
        if ask_for_table(cnx, table_name, primary_keys, table_labels):
            anonymize_table(cnx, table_name, fields_dict, primary_keys, table_labels)
        else:
            print(f"\033[93mTable {table_name} ignorée. ❌\033[0m")

# Définition des champs anonymisés
from faker import Faker

fake = Faker('fr_FR')

def short_import_key():
    return fake.uuid4().replace('-', '')[:14]

societe_fields = {
    "nom": lambda: fake.company(),
    "name_alias": lambda: fake.company(),
    "ref_ext": lambda: fake.uuid4(),
    "ref_int": lambda: fake.uuid4(),
    "address": lambda: fake.address().replace('\n', ', '),
    "zip": lambda: fake.postcode(),
    "town": lambda: fake.city(),
    "phone": lambda: fake.phone_number(),
    "fax": lambda: fake.phone_number(),
    "url": lambda: fake.url(),
    "email": lambda: fake.email(),
    "socialnetworks": lambda: fake.text(max_nb_chars=200),
    "siren": lambda: fake.bothify(text='#########'),
    "siret": lambda: fake.bothify(text='##############'),
    "ape": lambda: fake.bothify(text='????##'),
    "idprof4": lambda: fake.bothify(text='IDP4####'),
    "idprof5": lambda: fake.bothify(text='IDP5####'),
    "idprof6": lambda: fake.bothify(text='IDP6####'),
    "tva_intra": lambda: fake.bothify(text='FR##????####'),
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "model_pdf": lambda: fake.word(),
    "last_main_doc": lambda: fake.word(),
    "supplier_account": lambda: fake.bothify(text='SUPACC####'),
    "fk_prospectlevel": lambda: fake.bothify(text='PROSP##'),
    "location_incoterms": lambda: fake.city(),
    "deposit_percent": lambda: fake.numerify(text='##'),
    "canvas": lambda: fake.word(),
    "import_key": short_import_key,
    "webservices_url": lambda: fake.url(),
    "webservices_key": lambda: fake.uuid4(),
    "barcode": lambda: fake.ean13(),
    "accountancy_code_sell": lambda: fake.bothify(text='ACS####'),
    "accountancy_code_buy": lambda: fake.bothify(text='ACB####'),
    "multicurrency_code": lambda: "EUR",
    "default_lang": lambda: "fr_FR",
    "logo": lambda: fake.word(),
    "logo_squarred": lambda: fake.word()
}

socpeople_fields = {
    "ref_ext": lambda: fake.uuid4(),
    "civility": lambda: fake.random_element(elements=["M.", "Mme", "Dr", "Me"]),
    "lastname": lambda: fake.last_name(),
    "firstname": lambda: fake.first_name(),
    "address": lambda: fake.address().replace('\n', ', '),
    "zip": lambda: fake.postcode(),
    "town": lambda: fake.city(),
    "poste": lambda: fake.job(),
    "phone": lambda: fake.phone_number(),
    "phone_perso": lambda: fake.phone_number(),
    "phone_mobile": lambda: fake.phone_number(),
    "fax": lambda: fake.phone_number(),
    "email": lambda: fake.email(),
    "socialnetworks": lambda: fake.text(max_nb_chars=200),
    "photo": lambda: fake.word(),
    "fk_prospectlevel": lambda: fake.bothify(text='PROSP##'),
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "default_lang": lambda: "fr_FR",
    "canvas": lambda: fake.word(),
    "import_key": short_import_key
}

user_fields = {
    "ref_employee": lambda: fake.bothify(text='EMP####'),
    "ref_ext": lambda: fake.uuid4(),
    "gender": lambda: fake.random_element(elements=["male", "female", "other"]),
    "civility": lambda: fake.random_element(elements=["M.", "Mme", "Dr", "Me"]),
    "lastname": lambda: fake.last_name(),
    "firstname": lambda: fake.first_name(),
    "address": lambda: fake.address().replace('\n', ', '),
    "zip": lambda: fake.postcode(),
    "town": lambda: fake.city(),
    "job": lambda: fake.job(),
    "office_phone": lambda: fake.phone_number(),
    "office_fax": lambda: fake.phone_number(),
    "user_mobile": lambda: fake.phone_number(),
    "personal_mobile": lambda: fake.phone_number(),
    "email": lambda: fake.email(),
    "personal_email": lambda: fake.email(),
    "socialnetworks": lambda: fake.text(max_nb_chars=200),
    "signature": lambda: fake.text(max_nb_chars=200),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "note_private": lambda: fake.text(max_nb_chars=500),
    "model_pdf": lambda: fake.word(),
    "ldap_sid": lambda: fake.uuid4(),
    "openid": lambda: fake.url(),
    "photo": lambda: fake.word(),
    "lang": lambda: "fr_FR",
    "color": lambda: fake.hex_color().lstrip('#'),
    "barcode": lambda: fake.ean13(),
    "accountancy_code": lambda: fake.bothify(text='ACCT####'),
    "import_key": short_import_key,
    "iplastlogin": lambda: fake.ipv4(),
    "ippreviouslogin": lambda: fake.ipv4(),
    "twofactor_qrcode": lambda: fake.text(max_nb_chars=200),
    "twofactor_params": lambda: fake.text(max_nb_chars=200),
    "national_registration_number": lambda: fake.bothify(text='##########'),
    "birth_place": lambda: fake.city(),
    "email_oauth2": lambda: fake.email(),
    "last_main_doc": lambda: fake.word()
}

facture_fields = {
    "ref": lambda: "FAKEFAC-" + fake.uuid4().replace('-', '')[:10],
    "ref_ext": lambda: fake.uuid4(),
    "ref_int": lambda: fake.uuid4(),
    "ref_client": lambda: fake.bothify(text='FAKECLIENT-####'),
    "increment": lambda: fake.bothify(text='INC####'),
    "close_code": lambda: fake.bothify(text='CLOSE####'),
    "close_note": lambda: fake.sentence(nb_words=5),
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "model_pdf": lambda: fake.word(),
    "location_incoterms": lambda: fake.city(),
    "import_key": short_import_key,
    "extraparams": lambda: fake.bothify(text='PARAMS####'),
    "multicurrency_code": lambda: "EUR",
    "last_main_doc": lambda: fake.word(),
    "module_source": lambda: fake.word(),
    "pos_source": lambda: fake.word()
}

propal_fields = {
    "ref": lambda: "FAKEPROP-" + fake.uuid4().replace('-', '')[:10],
    "ref_client": lambda: fake.bothify(text='FAKECLIENT-####'),
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "model_pdf": lambda: fake.word()
}

commande_fields = {
    "ref": lambda: "FAKECMD-" + fake.uuid4().replace('-', '')[:10],
    "ref_client": lambda: fake.bothify(text='FAKECLIENT-####'),
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "model_pdf": lambda: fake.word()
}

contrat_fields = {
    "ref": lambda: "FAKECTR-" + fake.uuid4().replace('-', '')[:10],
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500)
}

facture_fourn_fields = {
    "ref": lambda: "FAKEFACF-" + fake.uuid4().replace('-', '')[:10],
    "ref_supplier": lambda: "FAKEFOURN-" + fake.uuid4().replace('-', '')[:5],
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "model_pdf": lambda: fake.word()
}

commande_fourn_fields = {
    "ref": lambda: "FAKECMDF-" + fake.uuid4().replace('-', '')[:10],
    "ref_supplier": lambda: "FAKEFOURN-" + fake.uuid4().replace('-', '')[:5],
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "model_pdf": lambda: fake.word()
}

projet_fields = {
    "ref": lambda: "FAKEPROJ-" + fake.uuid4().replace('-', '')[:10],
    "title": lambda: fake.sentence(nb_words=3),
    "description": lambda: fake.text(max_nb_chars=500),
    "note_private": lambda: fake.text(max_nb_chars=500),
    "note_public": lambda: fake.text(max_nb_chars=500),
    "model_pdf": lambda: fake.word(),
    "last_main_doc": lambda: fake.word(),
    "import_key": short_import_key,
    "email_msgid": lambda: "<" + fake.uuid4().replace('-', '') + "@example.com>",
    "ip": lambda: fake.ipv4(),
    "location": lambda: fake.city(),
    "extraparams": lambda: fake.bothify(text='PARAMS####')
}

ticket_fields = {
    "ref": lambda: "FAKETICKET-" + fake.uuid4().replace('-', '')[:10],
    "track_id": lambda: "TRACK-" + fake.uuid4().replace('-', '')[:10],
    "origin_email": lambda: fake.email(),
    "subject": lambda: "Ticket " + fake.sentence(nb_words=3),
    "message": lambda: fake.text(max_nb_chars=1000),
    "type_code": lambda: fake.bothify(text='TYPE####'),
    "category_code": lambda: fake.bothify(text='CAT####'),
    "severity_code": lambda: fake.bothify(text='SEV####'),
    "timing": lambda: fake.bothify(text='TIME##'),
    "import_key": short_import_key,
    "email_msgid": lambda: "<" + fake.uuid4().replace('-', '') + "@example.com>",
    "ip": lambda: fake.ipv4()
}

actioncomm_fields = {
    "ref": lambda: "FAKEEVENT-" + fake.uuid4().replace('-', '')[:10],
    "ref_ext": lambda: "FAKEEXT-" + fake.uuid4().replace('-', '')[:10],
    "code": lambda: fake.bothify(text='CODE####'),
    "location": lambda: fake.city(),
    "label": lambda: "Event " + fake.sentence(nb_words=3),
    "note": lambda: fake.text(max_nb_chars=1000),
    "email_subject": lambda: "Re: " + fake.sentence(nb_words=3),
    "email_msgid": lambda: "<" + fake.uuid4().replace('-', '') + "@example.com>",
    "email_from": lambda: fake.email(),
    "email_sender": lambda: fake.email(),
    "email_to": lambda: fake.email(),
    "email_tocc": lambda: fake.email(),
    "email_tobcc": lambda: fake.email(),
    "errors_to": lambda: fake.email(),
    "recurid": lambda: "RECUR-" + fake.uuid4().replace('-', '')[:8],
    "recurrule": lambda: fake.word(),
    "elementtype": lambda: fake.word(),
    "import_key": short_import_key,
    "extraparams": lambda: fake.bothify(text='PARAMS####'),
    "reply_to": lambda: fake.email(),
    "ip": lambda: fake.ipv4()
}

# Clés primaires personnalisées
primary_keys = {
    "llx_actioncomm": "id",
    "llx_societe": "rowid",
    "llx_socpeople": "rowid",
    "llx_user": "rowid",
    "llx_facture": "rowid",
    "llx_propal": "rowid",
    "llx_commande": "rowid",
    "llx_contrat": "rowid",
    "llx_facture_fourn": "rowid",
    "llx_commande_fournisseur": "rowid",
    "llx_projet": "rowid",
    "llx_ticket": "rowid",
}

# Labels pour les tables
table_labels = {
    "llx_societe": "(Tiers)",
    "llx_socpeople": "(Contacts)",
    "llx_user": "(Utilisateurs)",
    "llx_facture": "(Factures clients)",
    "llx_propal": "(Devis/Propositions commerciales)",
    "llx_commande": "(Commandes clients)",
    "llx_contrat": "(Contrats)",
    "llx_facture_fourn": "(Factures fournisseurs)",
    "llx_commande_fournisseur": "(Commandes fournisseurs)",
    "llx_projet": "(Projets)",
    "llx_ticket": "(Tickets)",
    "llx_actioncomm": "(Événements/Actions)"
}

# Liste des tables
tables_to_anonymize = [
    ("llx_societe", societe_fields),
    ("llx_socpeople", socpeople_fields),
    ("llx_user", user_fields),
    ("llx_facture", facture_fields),
    ("llx_propal", propal_fields),
    ("llx_commande", commande_fields),
    ("llx_contrat", contrat_fields),
    ("llx_facture_fourn", facture_fourn_fields),
    ("llx_commande_fournisseur", commande_fourn_fields),
    ("llx_projet", projet_fields),
    ("llx_ticket", ticket_fields),
    ("llx_actioncomm", actioncomm_fields)
]

class AutosshTunnel:
    def __init__(self, ssh_host, ssh_port, ssh_user, ssh_key, ssh_password, remote_bind_port):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_key = ssh_key
        self.ssh_password = ssh_password
        self.remote_bind_port = remote_bind_port
        self.local_bind_port = 3307
        self.process = None

    def wait_for_port(self, port, host='127.0.0.1', timeout=20):
        """Attend que le port soit disponible."""
        import socket
        import time
        start_time = time.time()
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    return True
            except:
                pass
            finally:
                if sock:
                    sock.close()
            
            if time.time() - start_time > timeout:
                return False
            
            time.sleep(1)
            print(".", end="", flush=True)

    def start_tunnel(self):
        # Vérifier si sshpass est installé
        if self.ssh_password and not shutil.which("sshpass"):
            raise Exception("sshpass n'est pas installé. Veuillez l'installer pour utiliser l'authentification par mot de passe.")

        autossh_cmd = []
        if self.ssh_password:
            autossh_cmd.extend(["sshpass", "-p", self.ssh_password])

        autossh_cmd.extend([
            "ssh",
            "-N",
            "-v",  # Mode verbeux pour le débogage
            "-L", f"127.0.0.1:{self.local_bind_port}:{self.ssh_host}:{self.remote_bind_port}",
            "-p", str(self.ssh_port),
            "-o", "ExitOnForwardFailure=yes",  # Échouer si le forward échoue
            "-o", "ServerAliveInterval=30",     # Garder la connexion active
            "-o", "ServerAliveCountMax=3",      # Nombre max de tentatives
            "-o", "StrictHostKeyChecking=no",   # Désactiver la vérification de la clé hôte
            f"{self.ssh_user}@{self.ssh_host}"
        ])

        if self.ssh_key:
            autossh_cmd.extend(["-i", self.ssh_key])

        # Masquer le mot de passe dans la commande affichée
        display_cmd = autossh_cmd.copy()
        if self.ssh_password:
            pwd_index = display_cmd.index("-p") + 1
            display_cmd[pwd_index] = "********"
        
        print(f"\n\033[93mDémarrage du tunnel SSH avec la commande : {' '.join(display_cmd)}\033[0m")

        try:
            # Vérifier si le port local est déjà utilisé
            import socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                test_socket.bind(('127.0.0.1', self.local_bind_port))
                test_socket.close()
            except socket.error:
                raise Exception(f"Le port {self.local_bind_port} est déjà utilisé")

            self.process = subprocess.Popen(
                autossh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            print("\nAttente de l'établissement du tunnel", end="", flush=True)
            if not self.wait_for_port(self.local_bind_port):
                stdout, stderr = self.process.communicate()
                print(f"\n\033[91mSortie standard : {stdout.decode()}\033[0m")
                print(f"\033[91mErreur standard : {stderr.decode()}\033[0m")
                raise Exception("Impossible d'établir le tunnel SSH après 20 secondes")

            print(f"\n\033[92mTunnel SSH établi sur le port local {self.local_bind_port}. ✅\033[0m")

        except Exception as e:
            if self.process:
                self.process.terminate()
            raise Exception(f"Erreur tunnel SSH: {str(e)}")

    def stop_tunnel(self):
        print("\n\033[93mFermeture du tunnel SSH...\033[0m 🔒")
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                print("\033[92mTunnel SSH fermé avec succès. ✅\033[0m")
            except subprocess.TimeoutExpired:
                self.process.kill()
                print("\033[91mLe processus SSH a été tué de force.\033[0m")


def test_mysql_connection(host, port, user, password, database, timeout=10):
    time.sleep(5)  # Attendre que le tunnel soit bien établi
    try:
        cnx = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connection_timeout=timeout,
            allow_local_infile=True,
            charset='utf8mb4'
        )
        if cnx.is_connected():
            cursor = cnx.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.close()
            cnx.close()
            return True, f"MySQL version {version[0]}"
    except Error as err:
        return False, str(err)
    except Exception as e:
        return False, str(e)

def main():
    # Parse les arguments
    args = parse_args()

    # Configuration du logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(message)s')

    # En mode non-interactif, on n'affiche pas le logo
    if not args.non_interactive:
        print_logo()

    # Si on est en mode non-interactif, on vérifie qu'on a soit un fichier de config
    # soit tous les arguments MySQL nécessaires
    if args.non_interactive:
        if not args.config and not (args.mysql_host and args.mysql_user and args.mysql_database):
            print("\033[91mErreur: En mode non-interactif, vous devez fournir soit un fichier de configuration")
            print("soit tous les paramètres MySQL nécessaires (host, user, database)\033[0m")
            sys.exit(1)
    else:
        if not confirm_proceed():
            print("Opération annulée. ❌")
            sys.exit(0)

    # Récupération de la configuration
    try:
        config = get_config_from_args(args)
    except Exception as e:
        print(f"\033[91mErreur lors du chargement de la configuration: {str(e)}\033[0m")
        sys.exit(1)

    # En mode interactif sans config complète, on demande les informations manquantes
    if not args.non_interactive:
        if args.use_ssh or (args.config and 'ssh' in config):
            if not all([config.get('ssh', {}).get(k) for k in ['host', 'user']]):
                ssh_info = get_autossh_info(False)
                config['ssh'] = {
                    'host': ssh_info[0],
                    'port': ssh_info[1],
                    'user': ssh_info[2],
                    'key': ssh_info[3],
                    'password': ssh_info[4]
                }
        
        if not all([config.get('mysql', {}).get(k) for k in ['host', 'user', 'database']]):
            mysql_info = get_mysql_info(False)
            config['mysql'] = {
                'host': mysql_info[0],
                'user': mysql_info[1],
                'password': mysql_info[2],
                'database': mysql_info[3],
                'port': mysql_info[4]
            }

    cnx = None
    mysql_config = config.get('mysql', {})
    
    # Si on utilise SSH
    if 'ssh' in config:
        if not is_autossh_installed():
            print("\033[91mErreur: autossh n'est pas installé. Veuillez l'installer avant de continuer.\033[0m")
            sys.exit(1)

        ssh_config = config['ssh']
        
        # Démarrer le tunnel SSH
        tunnel = AutosshTunnel(
            ssh_host=ssh_config['host'],
            ssh_port=ssh_config.get('port', 22),
            ssh_user=ssh_config['user'],
            ssh_key=ssh_config.get('key'),
            ssh_password=ssh_config.get('password'),
            remote_bind_port=mysql_config.get('port', 3306)
        )

        try:
            tunnel.start_tunnel()
            time.sleep(5)

            print("\n\033[93mConnexion à la base de données MYSQL via le tunnel SSH...\033[0m 🚀")
            
            # Configurations de connexion
            connection_configs = [
                {
                    'host': 'localhost',
                    'port': tunnel.local_bind_port,
                    'user': mysql_config['user'],
                    'password': mysql_config.get('password', ''),
                    'database': mysql_config['database'],
                    'use_pure': True,
                    'connection_timeout': 20,
                    'auth_plugin': 'mysql_native_password',
                    'allow_local_infile': True
                },
                {
                    'host': 'localhost',
                    'port': tunnel.local_bind_port,
                    'user': mysql_config['user'],
                    'password': mysql_config.get('password', ''),
                    'database': mysql_config['database'],
                    'use_pure': False,
                    'connection_timeout': 20,
                    'allow_local_infile': True
                },
                {
                    'host': '127.0.0.1',
                    'port': tunnel.local_bind_port,
                    'user': mysql_config['user'],
                    'password': mysql_config.get('password', ''),
                    'database': mysql_config['database'],
                    'use_pure': True,
                    'connection_timeout': 20,
                    'allow_local_infile': True
                }
            ]

            last_error = None
            for config in connection_configs:
                try:
                    safe_config = config.copy()
                    safe_config['password'] = '********'
                    if not args.non_interactive:
                        print(f"\n\033[93mTentative de connexion avec la configuration : {safe_config}\033[0m")
                    cnx = mysql.connector.connect(**config)
                    print("\033[92mConnexion MySQL réussie via le tunnel SSH. ✅\033[0m")
                    break
                except Exception as e:
                    last_error = str(e)
                    if mysql_config.get('password') and mysql_config['password'] in last_error:
                        last_error = last_error.replace(mysql_config['password'], '********')
                    if mysql_config['user'] and mysql_config['user'] in last_error:
                        last_error = last_error.replace(mysql_config['user'], '********')
                    if not args.non_interactive:
                        print(f"\033[91mÉchec de la tentative : {last_error}\033[0m")
            else:
                raise Exception(f"Impossible d'établir une connexion MySQL : {last_error}")

            print("\n\033[93mDébut de l'anonymisation...\033[0m 🚀")
            
            # Si des tables spécifiques sont demandées
            if args.tables:
                tables_to_process = [(t, d) for t, d in tables_to_anonymize if t in args.tables]
            else:
                tables_to_process = tables_to_anonymize

            anonymize_data(cnx, primary_keys, table_labels, tables_to_process)

        except Exception as e:
            print(f"\033[91mUne erreur est survenue : {e}\033[0m")
            logging.error("Une erreur est survenue : %s", e)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        finally:
            if cnx and cnx.is_connected():
                cnx.close()
                print("\033[92mConnexion MySQL fermée. ✅\033[0m")
            tunnel.stop_tunnel()

    else:
        # Connexion directe MySQL
        print("\n\033[96mConnexion directe MySQL...\033[0m")

        try:
            cnx = mysql.connector.connect(
                host=mysql_config['host'],
                port=mysql_config.get('port', 3306),
                user=mysql_config['user'],
                password=mysql_config.get('password', ''),
                database=mysql_config['database'],
                connection_timeout=10
            )
            print("\033[92mConnexion MySQL directe réussie. ✅\033[0m")

            print("\n\033[93mDébut de l'anonymisation...\033[0m 🚀")
            
            # Si des tables spécifiques sont demandées
            if args.tables:
                tables_to_process = [(t, d) for t, d in tables_to_anonymize if t in args.tables]
            else:
                tables_to_process = tables_to_anonymize

            anonymize_data(cnx, primary_keys, table_labels, tables_to_process)

        except Error as err:
            print(f"\033[91mErreur de connexion MySQL: {err}\033[0m")
            sys.exit(1)

        finally:
            if cnx and cnx.is_connected():
                cnx.close()
                print("\033[92mConnexion MySQL fermée. ✅\033[0m")

    print("\n\033[92mAnonymisation terminée avec succès ! ✅\033[0m")
    print("\nMerci d'avoir utilisé Progiclone par VLTN x Progiseize. À bientôt 👋!")

if __name__ == "__main__":
    try:
        check_updates()
        main()
    except KeyboardInterrupt:
        print("\nMerci d'avoir utilisé Progiclone par VLTN x Progiseize. À bientôt 👋!")
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
