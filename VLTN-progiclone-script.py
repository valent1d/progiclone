import sys
import os
import subprocess
import logging
from importlib import import_module
import getpass  # Pour masquer le mot de passe lors de la saisie
import shutil
import time

# Liste des dépendances requises, excluant sshtunnel
REQUIRED_PACKAGES = [
    'pyfiglet',
    'tqdm',
    'Faker',
    'mysql-connector-python',
    'requests',
]

def install_package(package):
    """Installe un package via pip."""
    print(f"Installation de {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_dependencies():
    """Vérifie que toutes les dépendances sont installées, sinon tente de les installer."""
    for package in REQUIRED_PACKAGES:
        try:
            import_module(package)
        except ImportError:
            print(f"Le module '{package}' est manquant. Tentative d'installation...")
            install_package(package)

    print("\n\033[92mToutes les dépendances sont présentes ou ont été installées avec succès.\033[0m\n")
    # Efface l'écran
    os.system('clear')

def is_autossh_installed():
    """Vérifie si autossh est installé."""
    return shutil.which("autossh") is not None

def print_logo():
    logo = """
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

def get_autossh_info():
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

def get_mysql_info():
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
    def __init__(self, ssh_host, ssh_port, ssh_user, ssh_key, ssh_password, remote_bind_port, local_bind_port=3307):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_key = ssh_key
        self.ssh_password = ssh_password
        self.remote_bind_port = remote_bind_port
        self.local_bind_port = local_bind_port
        self.process = None

    def start_tunnel(self):
        print("\n\033[93mOuverture du tunnel SSH avec autossh...\033[0m 🚀")
        autossh_cmd = [
            "autossh",
            "-M", "0",  # Désactive le port de monitoring
            "-N",        # Ne pas exécuter de commande distante
            "-o", "ServerAliveInterval=30",  # Envoi un paquet de vie toutes les 30 secondes
            "-o", "ServerAliveCountMax=3",   # Ferme la connexion après 3 échecs de réponse
            "-R", f"{self.remote_bind_port}:localhost:3306",  # Redirection de port distant
            "-p", str(self.ssh_port),
            f"{self.ssh_user}@{self.ssh_host}"
        ]

        if self.ssh_key:
            autossh_cmd.extend(["-i", self.ssh_key])
        if self.ssh_password:
            # Utiliser sshpass pour gérer le mot de passe
            # Assurez-vous que sshpass est installé sur votre système
            if not shutil.which("sshpass"):
                print("\033[91mErreur: sshpass n'est pas installé. Veuillez l'installer pour utiliser un mot de passe SSH.\033[0m")
                sys.exit(1)
            autossh_cmd = [
                "sshpass", "-p", self.ssh_password
            ] + autossh_cmd

        try:
            self.process = subprocess.Popen(
                autossh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Attendre un peu pour s'assurer que le tunnel est établi
            time.sleep(5)
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                print("\033[91mErreur lors de l'établissement du tunnel SSH avec autossh.\033[0m")
                print(stdout.decode())
                print(stderr.decode())
                sys.exit(1)
            print(f"\033[92mTunnel SSH établi avec succès sur le port distant {self.remote_bind_port}. ✅\033[0m")
        except Exception as e:
            print(f"\033[91mErreur lors de l'exécution d'autossh : {e}\033[0m")
            sys.exit(1)

    def stop_tunnel(self):
        print("\n\033[93mFermeture du tunnel SSH...\033[0m 🔒")
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                print("\033[92mTunnel SSH fermé avec succès. ✅\033[0m")
            except subprocess.TimeoutExpired:
                self.process.kill()
                print("\033[91mLe processus autossh n'a pas pu être terminé et a été tué.\033[0m")

def main():
    # Vérification des dépendances
    check_and_install_dependencies()

    from tqdm import tqdm
    import mysql.connector
    from mysql.connector import Error

    print_logo()

    if not confirm_proceed():
        print("Opération annulée. ❌")
        sys.exit(0)

    choice = choose_connection_method()

    cnx = None  # Initialiser cnx à None avant les blocs de connexion

    if choice == '1':
        # Connexion chiffrée via SSH avec autossh
        if not is_autossh_installed():
            print("\033[91mErreur: autossh n'est pas installé. Veuillez l'installer avant de continuer.\033[0m")
            sys.exit(1)

        ssh_host, ssh_port, ssh_user, ssh_key, ssh_password = get_autossh_info()
        mysql_host, mysql_user, mysql_password, mysql_database, mysql_port = get_mysql_info()

        # Définir le port distant pour le tunnel SSH (par exemple, 3307)
        remote_bind_port = 3307

        # Démarrer le tunnel SSH avec autossh
        tunnel = AutosshTunnel(
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            ssh_key=ssh_key,
            ssh_password=ssh_password,
            remote_bind_port=remote_bind_port,
            local_bind_port=3306  # Port local pour MySQL
        )

        try:
            tunnel.start_tunnel()

            # Attendre un peu pour s'assurer que le tunnel est prêt
            time.sleep(5)

            # Connexion à la base de données via le tunnel
            print("\n\033[93mConnexion à la base de données MYSQL via le tunnel SSH...\033[0m 🚀")
            cnx = mysql.connector.connect(
                host="127.0.0.1",
                port=remote_bind_port,
                user=mysql_user,
                password=mysql_password,
                database=mysql_database
            )
            print("\033[92mConnexion MySQL réussie via le tunnel SSH. ✅\033[0m")

            # Début de l'anonymisation
            print("\n\033[93mDébut de l'anonymisation...\033[0m 🚀")
            anonymize_data(cnx, primary_keys, table_labels, tables_to_anonymize)

        except Exception as e:
            print(f"\033[91mUne erreur est survenue : {e}\033[0m")
            logging.error("Une erreur est survenue : %s", e)
            import traceback
            traceback.print_exc()
            sys.exit(1)

        finally:
            if cnx and cnx.is_connected():
                cnx.close()
                print("\033[92mConnexion MySQL fermée. ✅\033[0m")
            tunnel.stop_tunnel()

    else:
        # Connexion directe MySQL non chiffrée
        mysql_host, mysql_user, mysql_password, mysql_database, mysql_port = get_mysql_info()
        print("\n\033[96mConnexion directe MySQL...\033[0m")

        try:
            cnx = mysql.connector.connect(
                host=mysql_host,
                port=mysql_port,
                user=mysql_user,
                password=mysql_password,
                database=mysql_database,
                connection_timeout=10  # Timeout de 10 secondes
            )
            print("\033[92mConnexion MySQL directe réussie. ✅\033[0m")

            # Début de l'anonymisation
            print("\n\033[93mDébut de l'anonymisation...\033[0m 🚀")
            anonymize_data(cnx, primary_keys, table_labels, tables_to_anonymize)

        except Error as err:
            print(f"\033[91mErreur de connexion MySQL: {err}\033[0m")
            sys.exit(1)

        finally:
            if cnx and cnx.is_connected():
                cnx.close()
                print("\033[92mConnexion MySQL fermée. ✅\033[0m")

    print("\n\033[92mAnonymisation terminée avec succès ! ✅\033[0m")
    print("\nMerci d'avoir utilisé Doliclone par VLTN x Progiseize. À bientôt 👋!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMerci d'avoir utilisé Doliclone par VLTN x Progiseize. À bientôt 👋!")
