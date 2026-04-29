import mysql.connector
from mysql.connector import Error


def create_connection():
    """Crée une connexion à la base de données MySQL/XAMPP"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',          
            database='Segment_db', 
            port=3306
        )
        print("✓ Connexion réussie à la base de données MySQL")
        return connection
    except Error as e:
        print(f"✗ Erreur lors de la connexion à MySQL: {e}")
        return None


def create_database_if_not_exists():
    """Crée la base de données si elle n'existe pas"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',   
            port=3306
        )
        cursor = connection.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS Segment_db")
        print("✓ Base de données 'Segment_db' créée ou existe déjà")

        cursor.close()
        connection.close()
        return True
    except Error as e:
        print(f"✗ Erreur lors de la création de la base de données: {e}")
        return False


def initialize_database():
    """Initialise la base de données avec les tables nécessaires"""
    print("Début de l'initialisation de la base de données...")

    if not create_database_if_not_exists():
        print("✗ Échec de la création de la base de données. Arrêt de l'initialisation.")
        return False

    connection = create_connection()
    if connection is None:
        print("✗ Échec de la connexion à la base de données. Arrêt de l'initialisation.")
        return False

    try:
        cursor = connection.cursor()

        print("Création de la table 'models'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INT AUTO_INCREMENT PRIMARY KEY,
                model_name VARCHAR(255) NOT NULL,
                model_type ENUM('segmentation', 'classification') NOT NULL,
                model_format ENUM('torchscript', 'state_dict') NOT NULL,
                model_path VARCHAR(255) NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Table 'models' créée avec succès")

        print("Création de la table 'users'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255) NOT NULL,
                cin VARCHAR(20) UNIQUE NOT NULL,
                date_of_birth DATE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Table 'users' créée avec succès")

        connection.commit()
        print("✓ Tous les changements ont été validés dans la base de données")

        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"✓ Tables dans la base de données: {[table[0] for table in tables]}")

        cursor.close()
        connection.close()
        print("✓ Initialisation de la base de données terminée avec succès!")
        return True

    except Error as e:
        print(f"✗ Erreur lors de l'initialisation de la base de données: {e}")
        if connection.is_connected():
            connection.rollback()
            connection.close()
        return False


def test_connection():
    """Teste la connexion à la base de données et affiche les informations système"""
    print("Test de la connexion à la base de données...")

    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='Segment_db',
            port=3306
        )

        cursor = connection.cursor()

        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✓ Version MySQL: {version[0]}")

        cursor.execute("SELECT DATABASE()")
        db = cursor.fetchone()
        print(f"✓ Base de données actuelle: {db[0]}")

        cursor.close()
        connection.close()

    except Error as e:
        print(f"✗ Échec du test de connexion: {e}")


def verify_tables():
    """Vérifie l'existence et la structure des tables"""
    print("Vérification des tables créées...")

    connection = create_connection()
    if connection is None:
        print("✗ Impossible de vérifier les tables - pas de connexion")
        return False

    try:
        cursor = connection.cursor()

        cursor.execute("DESCRIBE models")
        models_columns = cursor.fetchall()
        print(f"✓ Structure de la table 'models': {len(models_columns)} colonnes")

        cursor.execute("DESCRIBE users")
        users_columns = cursor.fetchall()
        print(f"✓ Structure de la table 'users': {len(users_columns)} colonnes")

        cursor.close()
        connection.close()
        return True

    except Error as e:
        print(f"✗ Erreur lors de la vérification des tables: {e}")
        if connection.is_connected():
            connection.close()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("SCRIPT DE CONFIGURATION DE LA BASE DE DONNÉES")
    print("=" * 60)

    test_connection()
    print()

    success = initialize_database()
    print()

    if success:
        verify_tables()

    print("=" * 60)
    if success:
        print("CONFIGURATION DE LA BASE DE DONNÉES TERMINÉE AVEC SUCCÈS!")
    else:
        print("ÉCHEC DE LA CONFIGURATION DE LA BASE DE DONNÉES!")
        print("\nConseils de dépannage:")
        print("1. Vérifiez que MySQL est lancé dans XAMPP")
        print("2. Vérifiez que le port est bien 3306")
        print("3. Vérifiez que l'utilisateur est root")
        print("4. Vérifiez que le mot de passe est vide dans XAMPP")
    print("=" * 60)