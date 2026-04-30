# create_admin.py
from database import create_connection
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin():
    # Informations d'admin prédéfinies - MODIFIEZ CES VALEURS
    ADMIN_DETAILS = {
        'first_name': "Admin",
        'last_name': "Admin",
        'cin': "AB000",
        'date_of_birth': "21/07/2002",  # Format : jj/mm/aaaa
        'email': "admin@example.com",
        'password': "admin"
    }

    try:
        # Conversion de la date en format MySQL
        dob = datetime.strptime(ADMIN_DETAILS['date_of_birth'], '%d/%m/%Y').date()
        
        connection = create_connection()
        cursor = connection.cursor()
        
        # Vérification de l'existence de l'admin
        cursor.execute("""
            SELECT * FROM users 
            WHERE cin = %s OR email = %s
        """, (ADMIN_DETAILS['cin'], ADMIN_DETAILS['email']))
        
        if cursor.fetchone():
            print("Le compte admin existe déjà")
            return

        # Hachage du mot de passe
        hashed_password = generate_password_hash(ADMIN_DETAILS['password'])
        
        # Insertion de l'admin
        cursor.execute("""
            INSERT INTO users 
            (first_name, last_name, cin, date_of_birth, email, password, is_admin, status)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, 'approved')
        """, (
            ADMIN_DETAILS['first_name'],
            ADMIN_DETAILS['last_name'],
            ADMIN_DETAILS['cin'],
            dob,
            ADMIN_DETAILS['email'],
            hashed_password
        ))
        
        connection.commit()
        print("Compte admin créé avec succès !")
        
    except Exception as e:
        print(f"Erreur lors de la création de l'admin : {str(e)}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()

if __name__ == "__main__":
    create_admin()