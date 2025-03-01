import os
import pysftp
import tempfile
from PIL import Image
import piexif
from datetime import datetime

class SFTPImageCompressor:
    def __init__(self, hostname, username, password=None, private_key=None):
        self.sftp_params = {
            'host': hostname,
            'username': username,
            'password': password,
            'private_key': private_key
        }
        self.temp_dir = tempfile.mkdtemp()
        self.compressed_count = 0
        self.total_saved = 0

    def compress_image(self, local_path):
        try:
            try:
                exif_dict = piexif.load(local_path)
            except:
                exif_dict = None

            img = Image.open(local_path)
            original_size = os.path.getsize(local_path)
            quality = 95
            min_quality = 80

            while quality >= min_quality:
                temp_path = f"{local_path}_temp"
                img.save(temp_path, 'JPEG', quality=quality, optimize=True)
                new_size = os.path.getsize(temp_path)

                if new_size < original_size * 0.8 or quality == min_quality:
                    if exif_dict:
                        piexif.insert(piexif.dump(exif_dict), temp_path)
                    os.replace(temp_path, local_path)
                    saved = original_size - new_size
                    self.compressed_count += 1
                    self.total_saved += saved
                    print(f"Compressé: {os.path.basename(local_path)} - Économie: {saved/1024:.2f}KB")
                    break

                os.remove(temp_path)
                quality -= 5

        except Exception as e:
            print(f"Erreur avec {local_path}: {str(e)}")

    def process_remote_directory(self, remote_path='/img'):
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # Pour le développement uniquement

        print(f"Connexion au serveur {self.sftp_params['host']}...")

        with pysftp.Connection(
                host=self.sftp_params['host'],
                username=self.sftp_params['username'],
                password=self.sftp_params['password'],
                private_key=self.sftp_params['private_key'],
                cnopts=cnopts
        ) as sftp:
            print("Connexion établie")

            # Créer un dossier de backup sur le serveur
            backup_dir = f"backup_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            sftp.mkdir(backup_dir)

            def process_directory(remote_dir):
                for entry in sftp.listdir_attr(remote_dir):
                    remote_path = f"{remote_dir}/{entry.filename}"

                    if sftp.isfile(remote_path):
                        if entry.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            # Backup
                            backup_path = f"{backup_dir}/{remote_path.lstrip('/')}"
                            sftp.makedirs(os.path.dirname(backup_path))
                            sftp.copy(remote_path, backup_path)

                            # Download
                            local_path = os.path.join(self.temp_dir, entry.filename)
                            sftp.get(remote_path, local_path)

                            # Compress
                            self.compress_image(local_path)

                            # Upload back
                            sftp.put(local_path, remote_path)
                            os.remove(local_path)

                    elif sftp.isdir(remote_path) and not entry.filename.startswith('.'):
                        process_directory(remote_path)

            process_directory(remote_path)
            print(f"\nRésumé:")
            print(f"Images compressées: {self.compressed_count}")
            print(f"Espace total économisé: {self.total_saved/1024/1024:.2f}MB")
            print(f"Backup créé sur le serveur: {backup_dir}")

# Utilisation
if __name__ == "__main__":
    compressor = SFTPImageCompressor(
        hostname='87.106.192.207',
        username='autourdesplantes.fr_5cicvrjb4wh',
        password='Z4q-7h!v@A'  # Ou utilisez private_key='/chemin/vers/cle'
    )
    compressor.process_remote_directory()
