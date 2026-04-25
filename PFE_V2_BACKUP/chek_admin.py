# check_admin.py - Vérifier les données admin existantes
from database import create_connection

def check_all_users():
    """Affiche tous les utilisateurs dans la base de données"""
    print("🔍 Vérification de tous les utilisateurs...")
    
    connection = create_connection()
    if connection is None:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Récupérer tous les utilisateurs
        cursor.execute("""
            SELECT id, username, first_name, last_name, cin, email, is_admin, created_at
            FROM users
        """)
        
        users = cursor.fetchall()
        
        if not users:
            print("❌ Aucun utilisateur trouvé dans la base de données")
            return False
        
        print(f"✓ {len(users)} utilisateur(s) trouvé(s):")
        print("-" * 80)
        
        for user in users:
            print(f"ID: {user[0] or 'NULL'}")
            print(f"Username: {user[1] or 'NULL'}")
            print(f"First Name: {user[2] or 'NULL'}")
            print(f"Last Name: {user[3] or 'NULL'}")
            print(f"CIN: {user[4] or 'NULL'}")
            print(f"Email: {user[5] or 'NULL'}")
            print(f"Is Admin: {user[6] or 'NULL'}")
            print(f"Created: {user[7] or 'NULL'}")
            print("-" * 80)
        
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors de la vérification: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

def check_admin_login_data():
    """Vérifie spécifiquement les données de connexion admin"""
    print("\n🔍 Vérification des données de connexion admin...")
    
    connection = create_connection()
    if connection is None:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Chercher l'admin par email
        cursor.execute("""
            SELECT id, username, email, password, is_admin
            FROM users 
            WHERE email = 'admin@mail.com' OR is_admin = TRUE
        """)
        
        admin = cursor.fetchone()
        
        if admin:
            print("✓ Données de l'admin trouvées:")
            print(f"   - ID: {admin[0]}")
            print(f"   - Username: {admin[1] or 'NULL'}")
            print(f"   - Email: {admin[2] or 'NULL'}")
            print(f"   - Password (hash): {admin[3][:20] + '...' if admin[3] else 'NULL'}")
            print(f"   - Is Admin: {admin[4]}")
            
            # Vérifier si l'email est bien rempli
            if not admin[2]:
                print("❌ PROBLÈME: L'email est NULL ou vide!")
                return False
            else:
                print("✓ Email correctement rempli")
                return True
        else:
            print("❌ Aucun admin trouvé!")
            return False
            
    except Exception as e:
        print(f"✗ Erreur lors de la vérification: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    print("="*80)
    print("VÉRIFICATION DES DONNÉES ADMIN")
    print("="*80)
    
    check_all_users()
    check_admin_login_data()
    
    print("="*80)