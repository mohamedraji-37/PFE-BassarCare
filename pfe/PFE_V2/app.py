# Importation des bibliothèques nécessaires
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, send_from_directory, send_file
from flask_babel import Babel, gettext as _, get_locale
from database import create_connection # Module personnalisé pour la connexion à la base de données
import mysql.connector
from mysql.connector import Error
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import os
import io
from datetime import datetime
from PIL import Image
import traceback
import cv2
from torchvision import transforms
from werkzeug.security import generate_password_hash, check_password_hash
from model import build_unet # Modèle U-Net personnalisé
import time
import traceback
from typing import Union
from fpdf import FPDF
from torchvision import models
import logging
import smtplib
from email.mime.text import MIMEText
import json
import sys
import re

# Initialisation de l'application Flask
app = Flask(__name__)
# Clé secrète pour les sessions
app.secret_key = 'dev_key_temporaire'
app.config['SESSION_TYPE'] = 'filesystem'
# Dossier pour stocker les fichiers uploadés
app.config['UPLOAD_FOLDER'] = 'uploads'
# Taille maximale des fichiers uploadés (1GB)
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024

# Configuration Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'fr'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

LANGUAGES = {
    'fr': 'Français',
    'en': 'English',
    'ar': 'العربية'
}

def select_locale():
    return session.get('lang', 'fr')

babel = Babel(app, locale_selector=select_locale)

@app.context_processor
def inject_languages():
    return {
        'LANGUAGES': LANGUAGES,
        'CURRENT_LANG': str(get_locale())
    }

# Configuration des répertoires pour les modèles
MODEL_BASE_DIR = "stored_models"
SEGMENTATION_DIR = os.path.join(MODEL_BASE_DIR, "segmentation")
CLASSIFICATION_DIR = os.path.join(MODEL_BASE_DIR, "classification")

os.makedirs(SEGMENTATION_DIR, exist_ok=True)
os.makedirs(CLASSIFICATION_DIR, exist_ok=True)

# Configuration du système de logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------
# MODÈLES DEEP LEARNING

class EfficientNetClassifier(nn.Module):
    def __init__(self, num_classes=2, model_name='efficientnet_b4'):
        super(EfficientNetClassifier, self).__init__()
        
        print(f"🏗️ Initialisation d'EfficientNet: {model_name} avec {num_classes} classes")
        
        if model_name == 'efficientnet_b4':
            # ✅ ARCHITECTURE EXACTEMENT IDENTIQUE À VOTRE CODE D'ENTRAÎNEMENT
            self.model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.IMAGENET1K_V1)
            
            # ⚠️ PROBLÈME IDENTIFIÉ: Votre code d'entraînement fait ceci:
            # num_features = model.classifier[1].in_features
            # model.classifier = nn.Sequential(nn.Dropout(0.4), nn.Linear(num_features, NUM_CLASSES))
            
            num_features = self.model.classifier[1].in_features
            self.model.classifier = nn.Sequential(
                nn.Dropout(0.4),  # ✅ Même dropout que dans l'entraînement
                nn.Linear(num_features, num_classes)  # ✅ Même structure finale
            )
            
            print(f"📐 Architecture créée (IDENTIQUE à l'entraînement):")
            print(f"   Features extraites: {num_features}")
            print(f"   Dropout: 0.4")
            print(f"   Linear: {num_features} -> {num_classes}")
    
    def forward(self, x):
        # ✅ Forward pass simple et direct
        return self.model(x)
    
    def load_trained_weights(self, state_dict_path, device=None):
        """
        Méthode de chargement PARFAITEMENT compatible avec votre modèle d'entraînement
        """
        try:
            if device is None:
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            print(f"🔄 Chargement depuis: {state_dict_path}")
            
            # Vérification de l'existence du fichier
            if not os.path.exists(state_dict_path):
                raise FileNotFoundError(f"Le fichier {state_dict_path} n'existe pas")
            
            # ✅ Chargement direct du state_dict (comme sauvegardé par votre code d'entraînement)
            checkpoint = torch.load(state_dict_path, map_location=device, weights_only=False)
            
            print(f"🔍 Type du checkpoint: {type(checkpoint)}")
            
            if isinstance(checkpoint, dict):
                print(f"🔍 Nombre de paramètres: {len(checkpoint)}")
                
                # Votre code d'entraînement utilise: torch.save(model.state_dict(), 'best_glaucoma_model.pth')
                # Donc checkpoint EST directement le state_dict
                missing_keys, unexpected_keys = self.load_state_dict(checkpoint, strict=False)
                
                print(f"✅ Chargement réussi!")
                print(f"   - Paramètres chargés: {len(checkpoint) - len(missing_keys)}")
                print(f"   - Clés manquantes: {len(missing_keys)}")
                print(f"   - Clés inattendues: {len(unexpected_keys)}")
                
                if missing_keys:
                    print(f"⚠️ Clés manquantes: {missing_keys[:3]}{'...' if len(missing_keys) > 3 else ''}")
                if unexpected_keys:
                    print(f"⚠️ Clés inattendues: {unexpected_keys[:3]}{'...' if len(unexpected_keys) > 3 else ''}")
                
                return missing_keys, unexpected_keys
            else:
                raise ValueError(f"Format de checkpoint inattendu: {type(checkpoint)}")
                
        except Exception as e:
            print(f"❌ Erreur dans load_trained_weights: {str(e)}")
            print(f"📍 Traceback:")
            print(traceback.format_exc())
            raise

# ---------------------------
# ---------------------------------------------------------------
# GESTION DES REQUÊTES ET AUTHENTIFICATION
# ---------------------------------------------------------------

# Vérification de la connexion avant chaque requête
@app.before_request
def require_login():
    # Routes accessibles sans connexion
    allowed_routes = ['login', 'signup', 'static', 'uploaded_file', 'home', 'contact', 'set_language']
    if request.endpoint not in allowed_routes and not session.get('logged_in'):
        return redirect(url_for('login'))

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

# ---------------------------------------------------------------
# ROUTES D'AUTHENTIFICATION
# ---------------------------------------------------------------

# Page d'accueil
@app.route('/')
def home():
    return render_template('home/home.html') 

# Connexion des utilisateurs
@app.route('/login', methods=['GET', 'POST'])
def login():
    # session.clear()  # À retirer après les tests : pour supprimer la session
    # Redirection si déjà connecté
    if session.get('logged_in'):
        return redirect(url_for('admin_dashboard' if session.get('is_admin') else 'user_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        # Vérification des champs obligatoires
        if not email or not password:
            flash('Both fields are required', 'danger')
            return redirect(url_for('login'))

        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            # Recherche de l'utilisateur dans la base de données
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if not user:
                flash('email not found', 'danger')
                return redirect(url_for('login'))

            # Vérification du mot de passe hashé
            if check_password_hash(user['password'], password):
                # Mise à jour de la session
                if user['status'] != 'approved':
                    flash('Votre compte est en attente d\'approbation par l\'administrateur', 'warning')
                    return redirect(url_for('login'))
                session.update({
                    'logged_in': True,
                    'user_id': user['id'],
                    'email': user['email'],
                    'is_admin': user['is_admin'],
                    'cin': user['cin'],
                    'first_name': user['first_name'],      # <-- Add this
                    'last_name': user['last_name'] 
                })
                return redirect(url_for('admin_dashboard' if user['is_admin'] else 'user_dashboard'))
            
            flash('Incorrect password', 'danger')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')
            return redirect(url_for('login'))
        finally:
            if cursor: cursor.close()
            if connection: connection.close()

    return render_template('auth/sign-in.html')

# Inscription des nouveaux utilisateurs
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('logged_in'):
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        cin = request.form.get('cin', '').strip()
        dob_str = request.form.get('date_of_birth')  # Format: dd/mm/yyyy
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        # Validation des champs obligatoires
        if not all([first_name, last_name, cin, dob_str, email, password]):
            flash('Tous les champs sont obligatoires', 'danger')
            return redirect(url_for('signup'))
        
        try:
            connection = create_connection()
            cursor = connection.cursor()
            # Vérification des doublons CIN/email
            cursor.execute("SELECT * FROM users WHERE cin = %s OR email = %s", (cin, email))
            if cursor.fetchone():
                flash('CIN ou nom d\'utilisateur déjà utilisé', 'danger')
                return redirect(url_for('signup'))
            # Hashage du mot de passe et insertion en base
            hashed_pw = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users 
                (first_name, last_name, cin, date_of_birth, email, password, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            """, (first_name, last_name, cin, dob_str, email, hashed_pw))
            connection.commit()
            flash('Merci pour votre inscription ! L\'administrateur va examiner votre demande.', 'success')
            return redirect(url_for('login'))

        except mysql.connector.IntegrityError:
            flash('Erreur de base de données', 'danger')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'danger')
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
    
    return render_template('auth/sign-up.html')
                                                                                                                                                                                                                                                                                                                                                                                                         
# Déconnexion
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------------------------------------------------
# ROUTES ADMINISTRATEUR
# ---------------------------------------------------------------

# Tableau de bord administrateur
@app.route('/admin/dashboard')
def admin_dashboard():
    # Vérification des privilèges admin
    if not session.get('is_admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('login'))
    
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Récupération des paramètres de recherche
        search_seg = request.args.get('search_seg', '')
        search_cls = request.args.get('search_cls', '')
        search_user = request.args.get('search_user', '')

        # Récupération des modèles de segmentation
        cursor.execute("""
            SELECT * FROM models 
            WHERE model_type = 'segmentation'
            AND model_name LIKE %s 
            ORDER BY upload_date DESC
        """, (f'%{search_seg}%',))
        segmentation_models = cursor.fetchall()

        # Récupération des modèles de classification
        cursor.execute("""
            SELECT * FROM models 
            WHERE model_type = 'classification'
            AND model_name LIKE %s 
            ORDER BY upload_date DESC
        """, (f'%{search_cls}%',))
        classification_models = cursor.fetchall()

        # Récupération des utilisateurs
        cursor.execute("""
            SELECT * FROM users 
            WHERE email LIKE %s 
            ORDER BY created_at DESC
        """, (f'%{search_user}%',))
        users = cursor.fetchall()

        # Résultats en attente de validation admin
        cursor.execute("""
            SELECT id, image_id, 'classification' AS result_type,
                   predicted_class, confidence, statut, created_at, image_path,
                   prob_normal, prob_glaucoma,
                   NULL AS iou, NULL AS dice, NULL AS precision_val,
                   NULL AS recall_val, NULL AS accuracy
            FROM results_classification WHERE statut = 'en_attente'
            UNION ALL
            SELECT id, image_id, 'segmentation' AS result_type,
                   NULL AS predicted_class, NULL AS confidence, statut, created_at, image_path,
                   NULL AS prob_normal, NULL AS prob_glaucoma,
                   iou, dice, precision_val, recall_val, accuracy
            FROM results_segmentation WHERE statut = 'en_attente'
            ORDER BY created_at DESC
        """)
        resultats_en_attente = cursor.fetchall()
        nb_en_attente = len(resultats_en_attente)

        # ── Statistiques descriptives ──────────────────────────
        cursor.execute("""
            SELECT predicted_class, confidence, image_id, created_at
            FROM results_classification
            WHERE statut = 'approuve'
            ORDER BY created_at DESC
        """)
        stat_rows = cursor.fetchall()
        stat_total = len(stat_rows)
        stat_glaucome = sum(1 for r in stat_rows if r['predicted_class'] == 'Glaucome')
        stat_normal = stat_total - stat_glaucome
        stat_conf_moy = round(sum(r['confidence'] for r in stat_rows) / stat_total * 100, 1) if stat_total else 0
        for r in stat_rows:
            if r.get('created_at'):
                r['created_at'] = str(r['created_at'])[:16]
        stats = {
            'total': stat_total,
            'glaucome': stat_glaucome,
            'normal': stat_normal,
            'conf_moy': stat_conf_moy,
            'pct_glaucome': round(stat_glaucome / stat_total * 100, 1) if stat_total else 0,
            'pct_normal': round(stat_normal / stat_total * 100, 1) if stat_total else 0,
            'patients': stat_rows,
        }

        return render_template('admin/dashboard.html',
                             segmentation_models=segmentation_models,
                             classification_models=classification_models,
                             users=users,
                             resultats_en_attente=resultats_en_attente,
                             nb_en_attente=nb_en_attente,
                             stats=stats)
    finally:
        cursor.close()
        connection.close()

# ---------------------------------------------------------------
# ROUTE : Statistiques descriptives (Admin)
# ---------------------------------------------------------------

@app.route('/admin/statistiques')
def admin_statistiques():
    """Retourne les statistiques descriptives des résultats de classification."""
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT predicted_class, confidence, image_id, created_at, image_path
            FROM results_classification
            WHERE statut IN ('approuve', 'telecharge')
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        total = len(rows)
        glaucome = sum(1 for r in rows if r['predicted_class'] == 'Glaucome')
        normal = total - glaucome
        conf_moy = round(sum(r['confidence'] for r in rows) / total * 100, 1) if total else 0
        pct_glaucome = round(glaucome / total * 100, 1) if total else 0
        pct_normal = round(normal / total * 100, 1) if total else 0
        # Formatage des dates pour l'affichage
        for r in rows:
            if r.get('created_at'):
                r['created_at'] = str(r['created_at'])[:16]
        return jsonify({
            'total': total,
            'glaucome': glaucome,
            'normal': normal,
            'conf_moy': conf_moy,
            'pct_glaucome': pct_glaucome,
            'pct_normal': pct_normal,
            'patients': rows
        })
    finally:
        cursor.close()
        connection.close()


# Téléchargement de modèle par l'admin
@app.route('/admin/upload_model', methods=['POST'])
def upload_model():
    # Vérification des privilèges
    if not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    connection = None
    cursor = None
    try:
        # Récupération des données du formulaire
        model_name = request.form.get('model_name')
        model_file = request.files.get('model_file')
        model_type = request.form.get('model_type', 'segmentation')

        # Validation des champs obligatoires
        if not model_name or not model_file:
            flash('Missing required fields', 'danger')
            return redirect(url_for('admin_dashboard'))

        if model_file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        # Vérification de l'extension du fichier
        file_ext = model_file.filename.rsplit('.', 1)[1].lower() if '.' in model_file.filename else ''
        allowed_extensions = {'pt', 'pth'}
        
        if file_ext not in allowed_extensions:
            flash(f'Invalid file type: .{file_ext}. Allowed: .pth, .pt', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        model_format = 'torchscript' if file_ext == 'pt' else 'state_dict'
        # Vérification de la taille du fichier
        MAX_SIZE = 300 * 1024 * 1024
        model_file.seek(0, os.SEEK_END)
        file_size = model_file.tell()
        model_file.seek(0)
        
        if file_size > MAX_SIZE:
            flash(f'File too large ({file_size/1024/1024:.2f}MB > {MAX_SIZE/1024/1024}MB)', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        # Sauvegarde du fichier
        save_dir = os.path.join(MODEL_BASE_DIR, model_type)
        os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{model_file.filename}"
        filepath = os.path.join(save_dir, filename)
        model_file.save(filepath)

        # Enregistrement en base de données
        connection = create_connection()
        cursor = connection.cursor()
        relative_path = os.path.join(model_type, filename)
        cursor.execute(
            "INSERT INTO models (model_name, model_type, model_format, model_path) VALUES (%s, %s, %s, %s)",
            (model_name, model_type, model_format, relative_path)
        )
        connection.commit()
        
        flash(f'Model {model_name} uploaded successfully!', 'success')

    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        # Nettoyage en cas d'erreur
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        if connection:
            connection.rollback()
    finally:
        if cursor: cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for('admin_dashboard'))

# Suppression d'un modèle
@app.route('/admin/delete_model/<int:model_id>')
def delete_model(model_id):
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        # Récupération du chemin du modèle
        cursor.execute("SELECT model_path FROM models WHERE id = %s", (model_id,))
        model_path = cursor.fetchone()['model_path']
        # Suppression de la base de données
        cursor.execute("DELETE FROM models WHERE id = %s", (model_id,))
        connection.commit()
        # Suppression physique du fichier
        full_path = os.path.join(MODEL_BASE_DIR, model_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            
        flash('Model deleted', 'success')
    except Exception as e:
        flash('Delete failed', 'danger')
    finally:
        cursor.close()
        connection.close()
    
    return redirect(url_for('admin_dashboard'))

# mise a jour d'un modèle
@app.route('/admin/edit_model/<int:model_id>', methods=['POST'])
def edit_model(model_id):
    if not session.get('is_admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('login'))
    
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Fetch model details
        cursor.execute("SELECT * FROM models WHERE id = %s", (model_id,))
        model_data = cursor.fetchone()
        
        if not model_data:
            flash('Model not found', 'danger')
            return redirect(url_for('admin_dashboard'))
            
        new_name = request.form.get('model_name')
        new_file = request.files.get('model_file')
        
        if not new_name:
            flash('Model name is required', 'danger')
            return jsonify({'success': False, 'error': 'Model name is required'})
            
        # Handle file update if provided
        if new_file and new_file.filename != '':
            # Validate file type and size (same as upload logic)
            file_ext = new_file.filename.rsplit('.', 1)[1].lower() if '.' in new_file.filename else ''
            allowed_extensions = {'pt', 'pth'}
            
            if file_ext not in allowed_extensions:
                return jsonify({'success': False, 'error': f'Invalid file type: .{file_ext}. Allowed: .pth, .pt'})
            
            # Save new file
            save_dir = os.path.join(MODEL_BASE_DIR, model_data['model_type'])
            os.makedirs(save_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{new_file.filename}"
            filepath = os.path.join(save_dir, filename)
            new_file.save(filepath)
            
            # Update database with new path
            relative_path = os.path.join(model_data['model_type'], filename)
            cursor.execute(
                "UPDATE models SET model_name = %s, model_path = %s WHERE id = %s",
                (new_name, relative_path, model_id)
            )
        else:
            # Only update name
            cursor.execute(
                "UPDATE models SET model_name = %s WHERE id = %s",
                (new_name, model_id)
            )
            
        connection.commit()
        return jsonify({'success': True, 'message': 'Model updated successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()
        connection.close()
        
# Suppression d'un utilisateur
@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if not session.get('is_admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('login'))
    
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        connection.commit()
        flash('Utilisateur a été supprimé avec succes', 'success')
    except Exception as e:
        flash(f'Suppression echoué: {str(e)}', 'danger')
    finally:
        cursor.close()
        connection.close()
    
    return redirect(url_for('admin_dashboard'))

# Envoi d'email de notification à l'utilisateur
def send_account_status_email(user_email, user_first_name, status):
    """Send an email to the user when their account is approved or rejected."""
    subject = ""
    body = ""
    if status == "approved":
        subject = "Votre compte a été approuvé"
        body = f"Bonjour {user_first_name},\n\nVotre compte sur BassarCare a été approuvé ! Vous pouvez maintenant vous connecter à la plateforme.\n\nCordialement,\nL'équipe BassarCare"
    elif status == "rejected":
        subject = "Votre inscription a été rejetée"
        body = f"Bonjour {user_first_name},\n\nNous sommes désolés de vous informer que votre demande d'inscription sur BassarCare a été rejetée.\n\nCordialement,\nL'équipe BassarCare"
    else:
        return

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'aababou19@gmail.com'
    msg['To'] = user_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('aababou19@gmail.com', 'jann uxxu ivwl evxv')
            smtp.send_message(msg)
    except Exception as e:
        print(f"Erreur d'envoi d'email: {e}")

#admin accepte nouveau utilisateur
@app.route('/admin/approve_user/<int:user_id>')
def approve_user(user_id):
    if not session.get('is_admin'):
        flash('Non autorisé', 'danger')
        return redirect(url_for('login'))
    
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT email, first_name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("UPDATE users SET status = 'approved' WHERE id = %s", (user_id,))
        connection.commit()
        # Envoi de l'email de notification
        if user:
            send_account_status_email(user['email'], user['first_name'], "approved")
        flash('Utilisateur approuvé avec succès', 'success')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        cursor.close()
        connection.close()
    
    return redirect(url_for('admin_dashboard'))

#admin n accepte pas l utilisateur
@app.route('/admin/reject_user/<int:user_id>')
def reject_user(user_id):
    if not session.get('is_admin'):
        flash('Non autorisé', 'danger')
        return redirect(url_for('login'))
    
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT email, first_name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("UPDATE users SET status = 'rejected' WHERE id = %s", (user_id,))
        connection.commit()
        # Envoi de l'email de notification
        if user:
            send_account_status_email(user['email'], user['first_name'], "rejected")
        flash('Demande utilisateur rejetée', 'success')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        cursor.close()
        connection.close()
    
    return redirect(url_for('admin_dashboard'))


# ---------------------------------------------------------------
# GESTION DES RÉSULTATS (Admin)
# ---------------------------------------------------------------

@app.route('/admin/soumettre_validation/<result_type>/<int:result_id>', methods=['POST'])
def soumettre_validation(result_type, result_id):
    """Permet au technicien de soumettre un résultat approuvé à la validation admin (passage en 'en_attente')."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Non autorisé'}), 403
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute(
            f"UPDATE {table} SET statut = 'en_attente', soumis_admin = 1 WHERE id = %s AND user_id = %s",
            (result_id, session['user_id'])
        )
        connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/admin/approuver_resultat/<result_type>/<int:result_id>')
def approuver_resultat(result_type, result_id):
    if not session.get('is_admin'):
        flash('Non autorisé', 'danger')
        return redirect(url_for('login'))
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute(f"UPDATE {table} SET statut = 'approuve' WHERE id = %s", (result_id,))
        connection.commit()
        flash('Résultat approuvé avec succès.', 'success')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for('admin_dashboard') + '#resultats')

@app.route('/admin/refuser_resultat/<result_type>/<int:result_id>')
def refuser_resultat(result_type, result_id):
    if not session.get('is_admin'):
        flash('Non autorisé', 'danger')
        return redirect(url_for('login'))
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute(f"UPDATE {table} SET statut = 'refuse' WHERE id = %s", (result_id,))
        connection.commit()
        flash('Résultat refusé.', 'warning')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for('admin_dashboard') + '#resultats')






# ---------------------------------------------------------------
# ROUTES ADMIN : RAPPORT TEXTE & PDF
# ---------------------------------------------------------------

@app.route('/admin/rapport_texte/<result_type>/<int:result_id>')
def admin_rapport_texte(result_type, result_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Non autorise'}), 403
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (result_id,))
        r = cursor.fetchone()
        if not r:
            return jsonify({'error': 'Resultat non trouve'}), 404
        # Recuperer les infos du technicien (meme rapport que celui recu par le client)
        cursor.execute("SELECT first_name, last_name, cin FROM users WHERE id = %s", (r.get('user_id'),))
        user = cursor.fetchone()
        full_name = f"{user['first_name']} {user['last_name']}".strip() if user else 'Inconnu'
        user_cin = str(user['cin']) if user else 'Inconnu'
        if result_type == 'classification':
            classification_results = {
                'predicted_class_name': r.get('predicted_class', 'N/A'),
                'confidence': float(r.get('confidence', 0)),
                'prob_normal': float(r.get('prob_normal', 0)),
                'prob_glaucoma': float(r.get('prob_glaucoma', 0)),
            }
            rapport = generate_classification_report(
                classification_results,
                r.get('image_id', 'Inconnu'),
                operator_name=full_name,
                patient_id=user_cin
            )
            rapport = remove_non_latin1(rapport)
        else:
            lines_txt = [
                "Rapport d'Analyse - Segmentation",
                f"Technicien : {full_name}",
                f"Identifiant patient : {user_cin}",
                f"Image : {r.get('image_id', 'Inconnu')}",
                "",
                "Metriques de segmentation :",
            ]
            for col, label in [('iou','IoU'),('dice','Dice'),('precision_val','Precision'),('recall_val','Rappel'),('accuracy','Exactitude')]:
                val = r.get(col)
                if val is not None:
                    lines_txt.append(f"  {label} : {float(val)*100:.2f}%")
            rapport = "\n".join(lines_txt)
        return jsonify({'rapport': rapport})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@app.route('/admin/rapport_pdf/<result_type>/<int:result_id>')
def admin_rapport_pdf(result_type, result_id):
    if not session.get('is_admin'):
        flash('Non autorise', 'danger')
        return redirect(url_for('login'))
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (result_id,))
        r = cursor.fetchone()
        if not r:
            flash('Resultat non trouve.', 'danger')
            return redirect(url_for('admin_dashboard'))
        # Recuperer les infos du technicien (meme rapport que celui recu par le client)
        cursor.execute("SELECT first_name, last_name, cin FROM users WHERE id = %s", (r.get('user_id'),))
        user = cursor.fetchone()
        full_name = f"{user['first_name']} {user['last_name']}".strip() if user else 'Inconnu'
        user_cin = str(user['cin']) if user else 'Inconnu'
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        logo_path = os.path.join('static', 'assets', 'new_logo_black.png')
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=30)
            pdf.set_xy(45, 10)
        else:
            pdf.set_xy(10, 10)
        pdf.set_font("Arial", 'B', 18)
        titre_type = "Classification" if result_type == 'classification' else "Segmentation"
        pdf.cell(0, 10, "       Bassar, votre analyse retinienne", ln=True, align='L')
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Rapport d'Analyse - {titre_type}", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        now = datetime.now()
        pdf.cell(0, 10, f"Genere le: {now.strftime('%d/%m/%Y a %H:%M:%S')}", ln=True, align='C')
        pdf.cell(0, 10, f"Utilisateur: {full_name}", ln=True, align='C')
        pdf.cell(0, 10, f"Identifiant du patient: {user_cin}", ln=True, align='C')
        pdf.ln(5)
        image_path = r.get('image_path', '')
        if image_path and os.path.exists(image_path):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Image analysee:", ln=True)
            pdf.image(image_path, x=pdf.get_x(), y=pdf.get_y(), w=80)
            pdf.ln(75)
        pdf.ln(10)
        if result_type == 'classification':
            classification_results = {
                'predicted_class_name': r.get('predicted_class', 'N/A'),
                'confidence': float(r.get('confidence', 0)),
                'prob_normal': float(r.get('prob_normal', 0)),
                'prob_glaucoma': float(r.get('prob_glaucoma', 0)),
            }
            report_text = generate_classification_report(
                classification_results,
                r.get('image_id', 'Inconnu'),
                operator_name=full_name,
                patient_id=user_cin
            )
            report_text = remove_non_latin1(report_text)
            pdf.set_font("Arial", '', 11)
            for line in report_text.splitlines():
                pdf.multi_cell(0, 8, line)
        else:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Metriques de segmentation:", ln=True)
            pdf.set_font("Arial", '', 11)
            metric_explanations = {
                'IoU': "Mesure le chevauchement entre la zone predite et la zone reelle.",
                'Dice': "Evalue la similarite entre l'image predite et la verite terrain.",
                'Precision': "Proportion des pixels predits positifs qui sont corrects.",
                'Rappel': "Capacite du modele a detecter tous les pixels reellement positifs.",
                'Exactitude': "Pourcentage global de pixels correctement classes."
            }
            for col, label in [('iou','IoU'),('dice','Dice'),('precision_val','Precision'),('recall_val','Rappel'),('accuracy','Exactitude')]:
                val = r.get(col)
                if val is not None:
                    explanation = metric_explanations.get(label, "")
                    pdf.set_font("Arial", 'B', 11)
                    pdf.cell(50, 10, f"{label}: {float(val)*100:.2f}%", ln=0)
                    pdf.set_font("Arial", '', 10)
                    pdf.multi_cell(0, 10, explanation)
                    pdf.ln(2)
            result_path = r.get('result_path', '')
            if result_path and os.path.exists(result_path):
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, "Image segmentee:", ln=True)
                pdf.image(result_path, x=pdf.get_x(), y=pdf.get_y(), w=80)
                pdf.ln(90)
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        download_name = f"rapport_admin_{result_type}_{result_id}.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=download_name,
            mimetype="application/pdf"
        )
    except Exception as e:
        flash(f'Erreur generation PDF: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()
        connection.close()

# ---------------------------------------------------------------
# ROUTES UTILISATEUR
# ---------------------------------------------------------------

# Tableau de bord utilisateur
@app.route('/user/dashboard', methods=['GET', 'POST'])
def user_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    models = []
    error = None
    resultats_en_attente = []
    connection = None
    cursor = None
    full_name = ''
    active_mode = request.args.get('mode', 'classification')
    user = None

    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        # Get user data for profile section
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        full_name = f"{user['first_name']} {user['last_name']}"
        
        # Récupération des modèles disponibles
        cursor.execute("""
            SELECT id, model_name, model_type 
            FROM models 
            WHERE model_type IN ('segmentation', 'classification')
            ORDER BY model_type, upload_date DESC
        """)
        models = cursor.fetchall()

        # Résultats en attente (persistent entre sessions)
        cursor.execute("""
            SELECT id, image_id, 'classification' AS result_type,
                   predicted_class, CAST(confidence AS DECIMAL(10,4)) AS confidence, statut, created_at
            FROM results_classification WHERE statut = 'en_attente' AND user_id = %s
            UNION ALL
            SELECT id, image_id, 'segmentation' AS result_type,
                   NULL AS predicted_class, CAST(NULL AS DECIMAL(10,4)) AS confidence, statut, created_at
            FROM results_segmentation WHERE statut = 'en_attente' AND user_id = %s
            ORDER BY created_at DESC
        """, (session['user_id'], session['user_id']))
        resultats_en_attente = cursor.fetchall()

        # Note : les résultats approuvés/refusés ne sont PAS chargés au démarrage.
        # Ils apparaissent uniquement pendant la session via le polling JS (/user/check_approbations).

        if request.method == 'POST':
            # Traitement de l'image uploadée
            if 'image' not in request.files:
                raise ValueError("No file uploaded")

            image_file = request.files['image']
            filename = save_uploaded_file(image_file)
            
            if not filename:
                raise ValueError("Invalid file format")
            
            # Sélection du modèle à utiliser
            selected_model_id = request.form.get('model_id')
            if selected_model_id:
                cursor.execute("""
                    SELECT id, model_path, model_format, model_type 
                    FROM models 
                    WHERE id = %s
                """, (selected_model_id,))
            else:
                # Utilisation du dernier modèle par défaut
                cursor.execute("""
                    SELECT id, model_path, model_format, model_type 
                    FROM models 
                    WHERE model_type = 'segmentation'
                    ORDER BY upload_date DESC 
                    LIMIT 1
                """)

            model_data = cursor.fetchone()
            if not model_data:
                raise ValueError("No available models for processing")
            # Chargement du modèle et prétraitement de l'image
            model = get_model_from_db(model_data['id'])
            input_tensor = preprocess_image(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Inférence du modèle
            with torch.no_grad():
                output = model(input_tensor)
            # Sauvegarde des résultats
            result_filename = f"result_{filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
            
            if model_data['model_type'] == 'segmentation':
                save_segmentation_result(output, save_path)
            else:
                raise NotImplementedError("Classification processing not implemented")

            connection.commit()

        

    except Exception as e:
        if connection: connection.rollback()
        error = str(e)
        if "not implemented" in error.lower():
            error = "Classification processing is not available yet"
        flash(error, 'danger')
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

    return render_template('user/dashboard.html',
                         models=models,
                         error=error,
                         full_name=full_name,
                         active_mode=active_mode,
                         user_cin=user['cin'] if user else '',
                         resultats_en_attente=resultats_en_attente)

# page de profile d'utilisateur
@app.route('/user/profile', methods=['GET', 'POST'])
def user_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    
    if request.method == 'POST':
        try:
            # Handle profile update
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            date_of_birth = request.form.get('date_of_birth')
            
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, user_id))
            if cursor.fetchone():
                flash('Cet email est déjà utilisé par un autre utilisateur', 'danger')
            else:
                cursor.execute("""
                    UPDATE users 
                    SET first_name = %s, last_name = %s, email = %s, date_of_birth = %s
                    WHERE id = %s
                """, (first_name, last_name, email, date_of_birth, user_id))
                connection.commit()
                flash('Profil mis à jour avec succès!', 'success')
        except Exception as e:
            connection.rollback()
            flash(f'Erreur lors de la mise à jour du profil: {str(e)}', 'danger')
    # Get user data
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    # Create full name
    full_name = f"{user['first_name']} {user['last_name']}"
    
    cursor.close()
    connection.close()
    return render_template('user/profile.html', user=user, full_name=full_name)

#Supprimer le compte
@app.route('/user/delete_account', methods=['POST'])
def delete_account():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        connection.commit()
        
        session.clear()  # Clear session after deletion
        flash('Votre compte a été supprimé avec succès', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        flash(f'Échec de la suppression du compte: {str(e)}', 'danger')
        return redirect(url_for('user_profile'))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

# ---------------------------------------------------------------
# FONCTIONS UTILITAIRES
# ---------------------------------------------------------------
def create_training_compatible_model(num_classes=2, device=None):
    """
    Crée un modèle avec EXACTEMENT la même architecture que votre code d'entraînement
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    print("🏗️ Création du modèle compatible avec l'entraînement...")
    
    # ✅ Code IDENTIQUE à votre fonction load_efficientnet_b4()
    model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.IMAGENET1K_V1)
    
    # ✅ Modification IDENTIQUE à votre entraînement
    num_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(0.4),
        nn.Linear(num_features, num_classes)
    )
    
    model = model.to(device)
    
    print(f"✅ Modèle créé avec {num_features} -> {num_classes} features")
    print(f"✅ Device: {device}")
    
    return model
# Création d'une superposition visuelle image/masque
def create_overlay(original: np.ndarray, mask: np.ndarray, alpha: float = 0.4) -> np.ndarray:
    """Crée une superposition visuelle entre l'image originale et le masque"""
    try:
        # Conversion en niveaux de gris si nécessaire
        if mask.ndim == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        # Redimensionnement du masque si nécessaire    
        if original.shape[:2] != mask.shape[:2]:
            mask = cv2.resize(mask, (original.shape[1], original.shape[0]))
        
        # Création d'un masque rouge
        mask_color = np.zeros_like(original)
        mask_color[mask > 0] = [0, 0, 255]  # Couleur rouge
        
        # Fusion des images
        overlay = cv2.addWeighted(original, 1 - alpha, mask_color, alpha, 0)
        return overlay
        
    except Exception as e:
        print(f"⚠ Overlay creation error: {str(e)}")
        return original  # Retourne l'image originale en cas d'erreur

#traitement d image    
@app.route('/process-image', methods=['POST'])
def process_image():
    connection = None
    cursor = None
    try:
        # Initial validation
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
            
        file = request.files['image']
        model_id = request.form.get('model_id')
        
        if not model_id or not file:
            return jsonify({'error': 'Missing required fields'}), 400

        # Save uploaded file
        filename = save_uploaded_file(file)
        if not filename:
            return jsonify({'error': 'Invalid file format'}), 400

        # Database connection
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM models WHERE id = %s", (model_id,))
        model_data = cursor.fetchone()
        
        if not model_data:
            return jsonify({'error': 'Model not found'}), 404

        # Load model with debugging
        start_load = time.time()
        model = get_model_from_db(model_data['id'], create_connection, MODEL_BASE_DIR)
        print(f"🕒 Model loading took: {time.time() - start_load:.2f}s")

        # Preprocessing with validation
        input_tensor = preprocess_image(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        print(f"🔵 Input tensor shape: {input_tensor.shape}")
        print(f"🔵 Input range - Min: {input_tensor.min().item():.4f}, Max: {input_tensor.max().item():.4f}")

        # Model inference
        start_infer = time.time()
        with torch.no_grad():
            model.eval()
            output = model(input_tensor)
            
            # Raw output statistics
            print(f"🔴 Raw output stats:")
            print(f"Shape: {output.shape}")
            print(f"Min: {output.min().item():.4f}")
            print(f"Max: {output.max().item():.4f}")
            print(f"Mean: {output.mean().item():.4f}")
            print(f"Std: {output.std().item():.4f}")

            # Apply sigmoid
            probabilities = torch.sigmoid(output)
            print(f"🟢 Post-sigmoid stats:")
            print(f"Min: {probabilities.min().item():.4f}")
            print(f"Max: {probabilities.max().item():.4f}")
            print(f"Mean: {probabilities.mean().item():.4f}")

        print(f"🕒 Inference took: {time.time() - start_infer:.2f}s")

        # Save results
        result_filename = f"result_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        
        # Process and save mask
        try:
            # Convert to numpy and threshold
            mask_np = probabilities.squeeze().cpu().numpy()
            print(f"🟠 Numpy mask stats:")
            print(f"Shape: {mask_np.shape}")
            print(f"Min: {mask_np.min():.4f}")
            print(f"Max: {mask_np.max():.4f}")
            
            mask = (mask_np > 0.5).astype(np.uint8) * 255
            cv2.imwrite(save_path, mask)
            
            # Calculate basic metrics
            total_pixels = mask.size
            foreground_pixels = np.count_nonzero(mask)
            foreground_percent = (foreground_pixels / total_pixels) * 100
            print(f"✅ Mask saved with {foreground_percent:.2f}% foreground")

            # Initialize response with basic metrics
            response = {
                'original': url_for('uploaded_file', filename=filename),
                'processed': url_for('uploaded_file', filename=result_filename),
                'metrics': {
                    'foreground_percent': round(foreground_percent, 2),
                    'total_pixels': int(total_pixels),
                    'foreground_pixels': int(foreground_pixels)
                }
            }

            # Calculate advanced metrics if ground truth exists
            if 'ground_truth' in request.files and request.files['ground_truth'].filename != '':
                # Load ground truth
                gt_file = request.files['ground_truth']
                gt_filename = save_uploaded_file(gt_file)
                gt_path = os.path.join(app.config['UPLOAD_FOLDER'], gt_filename)
                gt_mask = cv2.imread(gt_path, cv2.IMREAD_GRAYSCALE)
                gt_mask = (gt_mask > 127).astype(np.uint8)

                # Resize if necessary
                if gt_mask.shape != mask.shape:
                    gt_mask = cv2.resize(gt_mask, (mask.shape[1], mask.shape[0]))

                # Calculate metrics
                y_pred = (mask > 0).astype(np.uint8)
                y_true = gt_mask

                tp = np.logical_and(y_pred == 1, y_true == 1).sum()
                fp = np.logical_and(y_pred == 1, y_true == 0).sum()
                fn = np.logical_and(y_pred == 0, y_true == 1).sum()
                tn = np.logical_and(y_pred == 0, y_true == 0).sum()

                epsilon = 1e-7
                metrics = {
                    'iou': float(tp / (tp + fp + fn + epsilon)),
                    'dice': float((2 * tp) / (2 * tp + fp + fn + epsilon)),
                    'precision': float(tp / (tp + fp + epsilon)),
                    'recall': float(tp / (tp + fn + epsilon)),
                    'accuracy': float((tp + tn) / (tp + tn + fp + fn + epsilon))
                }
                response['metrics'].update(metrics)

        except Exception as save_error:
            print(f"❌ Mask saving failed: {str(save_error)}")
            raise

        # Create overlay
        try:
            original = cv2.imread(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            overlay = create_overlay(original, mask)
            overlay_path = os.path.join(app.config['UPLOAD_FOLDER'], f"overlay_{filename}")
            cv2.imwrite(overlay_path, overlay)
            response['overlay'] = url_for('uploaded_file', filename=f"overlay_{filename}")
        except Exception as overlay_error:
            print(f"⚠ Overlay creation failed: {str(overlay_error)}")

        # Sauvegarde dans results_segmentation
        # Le technicien choisit : 'en_attente' (validation admin) ou 'approuve' (direct)
        try:
            conn_seg = create_connection()
            cur_seg = conn_seg.cursor()
            # Récupérer les métriques calculées (si ground truth fourni)
            m = response.get('metrics', {})
            demande_validation = request.form.get('demande_validation', 'false').lower() == 'true'
            statut_seg = 'en_attente' if demande_validation else 'approuve'
            cur_seg.execute("""
                INSERT INTO results_segmentation
                (user_id, image_id, image_path, result_path,
                 iou, dice, precision_val, recall_val, accuracy,
                 statut, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                session.get('user_id'),
                filename,
                os.path.join(app.config['UPLOAD_FOLDER'], filename),
                os.path.join(app.config['UPLOAD_FOLDER'], result_filename),
                m.get('iou', None),
                m.get('dice', None),
                m.get('precision', None),
                m.get('recall', None),
                m.get('accuracy', None),
                statut_seg
            ))
            conn_seg.commit()
            response['result_id'] = cur_seg.lastrowid
            response['statut'] = statut_seg
        except Exception as seg_db_err:
            print(f"⚠ Sauvegarde segmentation échouée: {str(seg_db_err)}")
        finally:
            if 'cur_seg' in locals(): cur_seg.close()
            if 'conn_seg' in locals() and conn_seg.is_connected(): conn_seg.close()

        return jsonify(response)

    except Exception as e:
        app.logger.error(f"🔥 Processing error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected(): 
            connection.close()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

@app.route('/test-server', methods=['GET'])
def test_server():
    """
    Route simple pour tester que le serveur fonctionne
    """
    try:
        return jsonify({
            'status': 'OK',
            'message': 'Serveur fonctionnel',
            'torch_version': torch.__version__,
            'cuda_available': torch.cuda.is_available()
        })
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'message': str(e)
        }), 500

#recuperation de modele d'apres la base de donnees
def get_model_from_db(model_id, connection_creator, model_base_dir):
    """Charge un modèle à partir de la base de données avec vérifications rigoureuses"""
    connection = None
    cursor = None
    try:
        # 1. Database connection
        connection = connection_creator()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT model_path, model_format, model_type FROM models WHERE id = %s",
            (model_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise ValueError(f"❌ Model ID {model_id} not found in database")
        
        # 2. Validate model file existence
        full_path = os.path.join(model_base_dir, result['model_path'])
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"🚨 Model file missing at {full_path}")
        
        print(f"🔍 Loading model from: {full_path}")
        
        # 3. Initialize fresh model (must match training architecture)
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = build_unet().to(device)  # Your actual model class
        
        # 4. Advanced state dict handling
        try:
            checkpoint = torch.load(full_path, map_location=device)
            
            # Handle different checkpoint formats
            if 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            elif 'model' in checkpoint:
                state_dict = checkpoint['model']
            elif isinstance(checkpoint, nn.Module):
                state_dict = checkpoint.state_dict()
            else:
                state_dict = checkpoint
            
            # Remove module prefix if present (for DDP trained models)
            state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
            
            # Load with strict=False to handle potential mismatches
            load_result = model.load_state_dict(state_dict, strict=False)
            
            # Print missing/unexpected keys for debugging
            if load_result.missing_keys:
                print(f"⚠ Missing keys: {load_result.missing_keys}")
            if load_result.unexpected_keys:
                print(f"⚠ Unexpected keys: {load_result.unexpected_keys}")
        
        except Exception as e:
            raise RuntimeError(f"🔥 Failed to load weights: {str(e)}") from e
        
        # 5. Validate model initialization
        print("✅ Model loaded successfully")
        
        # CORRECTION: Utiliser le nom de la classe correctement
        try:
            model_name = model.__class__.__name__
            print(f"📐 Model architecture: {model_name}")
        except:
            print("📐 Model architecture: Unknown")
        
        # Debug: Print first conv layer weights (avec vérification)
        try:
            # Vérifier si le chemin d'accès aux couches existe
            if hasattr(model, 'e1') and hasattr(model.e1, 'conv') and hasattr(model.e1.conv, 'conv1'):
                first_conv = model.e1.conv.conv1.weight
                print(f"⚙ First conv layer weights (mean±std): {first_conv.mean().item():.4f} ± {first_conv.std().item():.4f}")
            else:
                print("⚙ First conv layer path not found - skipping weight analysis")
        except Exception as e:
            print(f"⚙ Could not analyze first conv layer: {e}")
        
        # Debug: Check for NaN/inf values
        nan_params = []
        inf_params = []
        
        for name, param in model.named_parameters():
            if torch.isnan(param).any():
                nan_params.append(name)
            if torch.isinf(param).any():
                inf_params.append(name)
        
        if nan_params:
            raise ValueError(f"🤯 NaN values detected in: {nan_params}")
        if inf_params:
            raise ValueError(f"🤯 Inf values detected in: {inf_params}")
        
        model.eval()
        return model
    
    except Exception as e:
        print(f"❌ Critical error loading model: {str(e)}")
        print("🛠 Debugging info:")
        if 'full_path' in locals():
            print(f"- Model path: {full_path}")
        if 'checkpoint' in locals():
            print(f"- Checkpoint keys: {list(checkpoint.keys())}")
        else:
            print("- Checkpoint keys: N/A")
        print(f"- Device: {device if 'device' in locals() else 'N/A'}")
        print(traceback.format_exc())
        raise RuntimeError("Model loading failed") from e
    
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

# Sauvegarde des fichiers uploadés
def save_uploaded_file(file):
    if file.filename == '':
        return None
    # Génération d'un nom de fichier unique avec timestamp
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return filename

# Prétraitement des images (identique à l'entraînement)
def preprocess_image(image_path):
    """Réplique exacte du prétraitement utilisé pendant l'entraînement"""
    # # Chargement et redimensionnement (comme DriveDataset)
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image at {image_path}")
    
    # Normalisation et formatage
    image = cv2.resize(image, (512, 512))
    image = image.astype(np.float32) / 255.0  
    
    # Channel order
    image = np.transpose(image, (2, 0, 1))  # Conversion HWC vers CHW
    
    # Debug check
    print(f"\n🔵 Input Stats:")
    print(f"Min: {image.min():.4f}")
    print(f"Max: {image.max():.4f}")
    print(f"Mean: {image.mean():.4f}")
    
    return torch.from_numpy(image).unsqueeze(0)

def load_compatible_model(model_path):
    """
    Charge le modèle avec gestion d'erreur robuste
    """
    logger.info(f"🔄 Chargement du modèle depuis: {model_path}")
    
    try:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Création du modèle avec architecture d'entraînement
        model = models.efficientnet_b4(weights=None)
        num_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(num_features, 2)
        )
        
        logger.info(f"🏗️ Modèle créé avec {num_features} -> 2 classes")
        
        # Chargement des poids
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        logger.info(f"📁 Checkpoint chargé: {type(checkpoint)}")
        
        missing_keys, unexpected_keys = model.load_state_dict(checkpoint, strict=False)
        
        logger.info(f"✅ Poids chargés:")
        logger.info(f"   - Missing keys: {len(missing_keys)}")
        logger.info(f"   - Unexpected keys: {len(unexpected_keys)}")
        
        model = model.to(device)
        
        # Test rapide
        model.eval()
        with torch.no_grad():
            test_input = torch.randn(1, 3, 380, 380).to(device)
            test_output = model(test_input)
            logger.info(f"🧪 Test OK - Output shape: {test_output.shape}")
        
        return model
        
    except Exception as e:
        logger.error(f"❌ Erreur chargement modèle: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def test_model_compatibility(model_path):
    """
    Fonction pour tester si le modèle charge correctement et donne des prédictions cohérentes
    """
    try:
        print("🧪 Test de compatibilité du modèle...")
        
        # Chargement du modèle
        model = load_compatible_model(model_path)
        
        # Création d'un tensor de test (même format que vos données d'entraînement)
        device = next(model.parameters()).device
        test_input = torch.randn(1, 3, 380, 380).to(device)  # Taille d'entrée de votre entraînement
        
        # Test de prédiction
        with torch.no_grad():
            outputs = model(test_input)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs, 1)
        print(f"✅ Test réussi!")
        print(f"   - Format de sortie: {outputs.shape}")
        print(f"   - Classe prédite: {predicted.item()}")
        print(f"   - Probabilities: {probabilities[0].tolist()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test échoué: {str(e)}")
        return False

def perform_classification(model, img_tensor, device):
    """
    Fonction centralisée pour effectuer la classification
    Retourne tous les résultats nécessaires pour le rapport
    """
    model.eval()
    with torch.no_grad():
        outputs = model(img_tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        _, predicted = torch.max(outputs, 1)
        
        predicted_class = predicted[0].item()
        confidence = probabilities[0][predicted_class].item()
        prob_glaucoma = probabilities[0][0].item()  # index 0 = Glaucome
        prob_normal = probabilities[0][1].item()    # index 1 = Normal
        
        class_names = ['Glaucome', 'Normal']
        
        # Retour structuré avec tous les résultats
        return {
            'predicted_class_idx': predicted_class,
            'predicted_class_name': class_names[predicted_class],
            'confidence': confidence,
            'prob_normal': prob_normal,
            'prob_glaucoma': prob_glaucoma,
            'probabilities': probabilities,
            'outputs': outputs,
            'class_names': class_names
        }

def test_model_compatibility(model_path, device=None):
    """
    Test de compatibilité entre votre modèle entraîné et les fonctions corrigées
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    print("🧪 Test de compatibilité du modèle...")
    
    try:
        # Créer le modèle avec l'architecture d'entraînement
        model = create_training_compatible_model(num_classes=2, device=device)
        
        # Charger les poids
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint, strict=False)
        
        # Test d'inférence
        model.eval()
        with torch.no_grad():
            test_input = torch.randn(1, 3, 380, 380).to(device)
            output = model(test_input)
            probabilities = torch.nn.functional.softmax(output, dim=1)
            
            print(f"✅ Test réussi!")
            print(f"   Forme d'entrée: {test_input.shape}")
            print(f"   Forme de sortie: {output.shape}")
            print(f"   Probabilités: {probabilities}")
            print(f"   Somme des probabilités: {probabilities.sum():.6f}")
            
            return True
            
    except Exception as e:
        print(f"❌ Test échoué: {str(e)}")
        print(traceback.format_exc())
        return False
#enregistrement de resultat
def save_segmentation_result(output, save_path):
    """Process and save segmentation results with proper tensor handling"""
    try:
        # Ensure output is a tensor and apply sigmoid
        if isinstance(output, np.ndarray):
            output = torch.from_numpy(output)
            
        # Process output tensor
        output = output.detach().cpu()
        probabilities = torch.sigmoid(output)
        
        # Convert to numpy array for OpenCV
        mask_np = probabilities.numpy().squeeze()  # Remove batch and channel dims
        
        # Threshold and scale
        mask = (mask_np > 0.5).astype(np.uint8) * 255
        
        # Save result
        cv2.imwrite(save_path, mask)
        
        # Debug output
        print(f"Processed mask - Foreground %: {(mask > 0).mean() * 100:.2f}%")

    except Exception as e:
        print(f"❌ Error saving segmentation result: {str(e)}")
        # Create error image
        error_img = np.zeros((512, 512), dtype=np.uint8)
        cv2.putText(error_img, "Processing Error", (50, 256), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
        cv2.imwrite(save_path, error_img)

# generation de rapport de partie classification Glaucoma TXT
def generate_classification_report(classification_results, filename, patient_id=None, operator_name=None):
    """
    Génère un rapport médical professionnel pour la classification du glaucome
    Conforme aux standards hospitaliers
    
    Args:
        classification_results (dict): Résultats de la classification IA
        filename (str): Nom du fichier image analysé
        patient_id (str, optional): Identifiant patient
        operator_name (str, optional): Nom de l'opérateur
    
    Returns:
        str: Rapport médical formaté
    """
    try:
        # Extraction des données de classification
        predicted_class_name = classification_results['predicted_class_name']
        confidence = classification_results['confidence']
        prob_normal = classification_results.get('prob_normal', 0)
        prob_glaucoma = classification_results.get('prob_glaucoma', 0)
        
        prob_normal_corrected = prob_normal
        prob_glaucoma_corrected = prob_glaucoma
        
        # Détermination du diagnostic basé sur la probabilité la plus élevée
        if prob_normal_corrected > prob_glaucoma_corrected:
            predicted_class_corrected = "NORMALE"
            is_glaucoma_case = False
            confidence_corrected = prob_normal_corrected
        else:
            predicted_class_corrected = "GLAUCOME"
            is_glaucoma_case = True
            confidence_corrected = prob_glaucoma_corrected
        
        # Métadonnées du rapport
        from datetime import datetime
        current_time = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
        
        # Évaluation du niveau de risque (avec correction d'inversion)
        def get_risk_level():
            # Utiliser is_glaucoma_case pour déterminer le vrai cas
            if is_glaucoma_case:  # Cas de glaucome réel
                if confidence_corrected >= 0.90:
                    return " RISQUE ÉLEVÉ", "Consultation ophtalmologique URGENTE requise"
                elif confidence_corrected >= 0.70:
                    return " RISQUE MODÉRÉ-ÉLEVÉ", "Consultation dans les 48-72h recommandée"
                else:
                    return " RISQUE MODÉRÉ", "Surveillance et consultation sous 1 semaine"
            else:  # Cas normal réel
                if confidence_corrected >= 0.90:
                    return " RISQUE FAIBLE", "Contrôle de routine selon protocole"
                else:
                    return " INCERTAIN", "Réévaluation clinique recommandée"
        
        risk_level, recommendation = get_risk_level()
        
        # Interprétation clinique détaillée (avec correction d'inversion)
        def get_clinical_interpretation():
            if is_glaucoma_case:  # Cas de glaucome réel
                interpretation = f"Analyse automatisée révèle des signes morphologiques compatibles avec un glaucome (probabilité: {prob_glaucoma_corrected*100:.1f}%)."
                if confidence_corrected >= 0.90:
                    interpretation += " Indices morphologiques fortement évocateurs de glaucome."
                elif confidence_corrected >= 0.70:
                    interpretation += " Signes suspects nécessitant une évaluation clinique approfondie."
                else:
                    interpretation += " Anomalies détectées requérant des examens complémentaires."
                interpretation += " Rechercher: excavation papillaire pathologique, amincissement de l'anneau neuro-rétinien, asymétrie inter-oculaire."
            else:  # Cas normal réel
                interpretation = f"Morphologie papillaire dans les limites acceptables (probabilité normale: {prob_normal_corrected*100:.1f}%)."
                if confidence_corrected < 0.80:
                    interpretation += " Certains paramètres nécessitent une confirmation par examen clinique."
            return interpretation
        
        clinical_interpretation = get_clinical_interpretation()
        
        # Génération du rapport structuré
        report = f"""
                         

* INFORMATIONS GÉNÉRALES
   - Date/Heure: {current_time}
   - Image analysée: {filename}

* RÉSULTATS DE CLASSIFICATION
   - Diagnostic IA: {predicted_class_corrected}
   - Niveau de confiance: {confidence_corrected*100:.1f}%
   - {risk_level}

* ANALYSE PROBABILISTE DÉTAILLÉE
   - Probabilité Glaucome: {prob_glaucoma_corrected*100:.1f}%
   - Probabilité Normale: {prob_normal_corrected*100:.1f}%
   - Seuil de décision: 50.0%
   

* INTERPRÉTATION CLINIQUE
   {clinical_interpretation}

* RECOMMANDATIONS CLINIQUES
   - {recommendation}
   - Corréler avec l'examen clinique, la tonométrie et la périmétrie
   - Considérer l'anamnèse familiale et les facteurs de risque
   - Documentation photographique recommandée pour suivi évolutif

*  AVERTISSEMENT MÉDICAL RÉGLEMENTAIRE
   Cette analyse constitue un outil d'aide au diagnostic et ne remplace
   en aucun cas l'évaluation clinique par un ophtalmologiste qualifié.
   Le diagnostic définitif doit toujours être établi par un spécialiste
   sur la base d'un examen clinique complet.

_______________________________________________________________________________
BassarCare | 
Généré automatiquement - Document à conserver
_______________________________________________________________________________
"""
        
        return report.strip()
        
    except KeyError as e:
        return f"❌ ERREUR - Données manquantes dans les résultats: {str(e)}\nVérifier l'intégrité des données de classification."
    
    except Exception as e:
        return f"❌ ERREUR SYSTÈME - Impossible de générer le rapport: {str(e)}\nContacter le support technique."

def get_medical_interpretation(predicted_class, confidence_percentage):
    """
    Fonction d'interprétation médicale (maintenue pour compatibilité)
    """
    if predicted_class.lower() == "glaucoma":
        if confidence_percentage >= 90:
            return "Forte suspicion de glaucome - Consultation urgente recommandée"
        elif confidence_percentage >= 70:
            return "Suspicion modérée de glaucome - Évaluation clinique nécessaire"
        else:
            return "Signes suspects détectés - Surveillance recommandée"
    else:
        if confidence_percentage >= 90:
            return "Aspect normal - Contrôle de routine"
        else:
            return "Résultat incertain - Confirmation clinique souhaitable"

def test_classification_locally(image_path, model_path):
    """
    Test local de la classification - VERSION SYNCHRONISÉE
    """
    print("🧪 Test local de classification...")
   
    try:
        # Chargement du modèle
        model = load_compatible_model(model_path)
       
        # Préparation de l'image (EXACTEMENT comme dans la route)
        transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
       
        img = Image.open(image_path).convert('RGB')
        img_tensor = transform(img).unsqueeze(0)
       
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        img_tensor = img_tensor.to(device)
        model = model.to(device)
       
        # Classification avec la fonction centralisée
        results = perform_classification(model, img_tensor, device)
        
        # Affichage des résultats (IDENTIQUES à la route)
        print(f"✅ Résultat:")
        print(f"   Classe: {results['predicted_class_name']}")
        print(f"   Confiance: {results['confidence']*100:.2f}%")
        print(f"   Probabilités: Normal={results['prob_normal']*100:.2f}%, Glaucome={results['prob_glaucoma']*100:.2f}%")
        
        # Génération du rapport avec les MÊMES données
        filename = os.path.basename(image_path)
        report = generate_classification_report(results, filename)
        print(f"\n📋 RAPPORT:")
        print(report)
        
        return True, results
       
    except Exception as e:
        print(f"❌ Erreur test local: {str(e)}")
        print(traceback.format_exc())
        return False, None
    
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/get-models')
def get_models():
    category = request.args.get('category', 'eyes')
    process_type = request.args.get('type', 'segmentation')
    
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, model_name 
            FROM models 
            WHERE model_type = %s 
            ORDER BY model_name ASC
        """, (process_type,))
        
        models = cursor.fetchall()
        return jsonify(models)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/download-results', methods=['POST'])
def download_results():
    data = request.json
    original_filename = data.get('original')
    processed_filename = data.get('processed')
    metrics = data.get('metrics', {})

    original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
    processed_path = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Rapport de Résultat de Segmentation", ln=True, align='C')

    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)

    # Images
    if os.path.exists(original_path):
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Image Originale", ln=True)
        pdf.image(original_path, w=100)

    if os.path.exists(processed_path):
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Image Traité", ln=True)
        pdf.image(processed_path, w=100)

    # Metrics
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Métriques:", ln=True)
    pdf.set_font("Arial", '', 12)
    for key, value in metrics.items():
        pdf.cell(0, 10, f"{key.capitalize()}: {value}", ln=True)

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    output = io.BytesIO(pdf_bytes)

    return send_file(
        output,
        as_attachment=True,
        download_name="rapport_segmentation.pdf",
        mimetype="application/pdf"
    )

def get_classification_model_from_db_fixed(model_id, connection_creator, model_base_dir):
    """
    Version PARFAITEMENT compatible avec votre modèle d'entraînement
    """
    connection = None
    cursor = None
    try:
        # 1. Connexion à la base de données
        connection = connection_creator()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT model_path, model_format, model_type FROM models WHERE id = %s",
            (model_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise ValueError(f"❌ Modèle ID {model_id} non trouvé")
        
        if result['model_type'] != 'classification':
            raise ValueError(f"❌ Le modèle n'est pas un modèle de classification")

        # 2. Validation du fichier
        full_path = os.path.join(model_base_dir, result['model_path'])
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"🚨 Fichier manquant: {full_path}")

        print(f"🔍 Chargement depuis: {full_path}")

        # 3. ✅ SOLUTION: Utiliser la MÊME fonction que dans l'entraînement
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Créer le modèle avec l'architecture d'entraînement
        model = create_training_compatible_model(num_classes=2, device=device)
        
        # Chargement direct du state_dict
        print("🔄 Chargement des poids...")
        checkpoint = torch.load(full_path, map_location=device, weights_only=False)
        
        # Votre entraînement sauvegarde avec torch.save(model.state_dict(), ...)
        missing_keys, unexpected_keys = model.load_state_dict(checkpoint, strict=False)
        
        print(f"✅ Poids chargés!")
        print(f"   - Clés manquantes: {len(missing_keys)}")
        print(f"   - Clés inattendues: {len(unexpected_keys)}")

        # 4. Test de validation
        print("🧪 Test de validation...")
        model.eval()
        with torch.no_grad():
            # ✅ Test avec les bonnes dimensions (380x380 comme dans votre entraînement)
            dummy_input = torch.randn(1, 3, 380, 380).to(device)
            dummy_output = model(dummy_input)
            
            print(f"✅ Test réussi - Forme de sortie: {dummy_output.shape}")
            print(f"✅ Range: [{dummy_output.min():.4f}, {dummy_output.max():.4f}]")
            
            # Vérification des classes
            if dummy_output.shape[1] != 2:
                raise ValueError(f"❌ Sortie incorrecte: {dummy_output.shape[1]} classes vs 2 attendues")

        print("🎉 Modèle chargé et validé avec succès!")
        return model

    except Exception as e:
        error_msg = f"❌ Erreur critique: {str(e)}"
        print(error_msg)
        print("📍 Traceback complet:")
        print(traceback.format_exc())
        raise RuntimeError(f"Échec du chargement: {str(e)}") from e

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def detect_model_architecture(checkpoint, model_name):
    """
    Détecte l'architecture du modèle basée sur le checkpoint et le nom
    """
    # Détection basée sur le nom du modèle
    model_name_lower = model_name.lower()
    if 'efficientnet' in model_name_lower or 'efficient' in model_name_lower:
        return 'efficientnet_b4'
    elif 'resnet' in model_name_lower:
        return 'resnet18'
    
    # Détection basée sur la structure du checkpoint
    if isinstance(checkpoint, dict):
        # Recherche dans state_dict ou model
        state_dict = checkpoint.get('state_dict', checkpoint.get('model', checkpoint))
        
        if any('efficientnet' in key for key in state_dict.keys()):
            return 'efficientnet_b4'
        elif any('resnet' in key for key in state_dict.keys()):
            return 'resnet18'
        elif any('features' in key and 'classifier' in str(state_dict.keys()) for key in state_dict.keys()):
            return 'efficientnet_b4'  # Structure typique d'EfficientNet
    
    # Défaut: EfficientNet-B4
    return 'efficientnet_b4'

def extract_state_dict(checkpoint):
    """
    Extrait le state_dict du checkpoint selon différents formats possibles
    """
    if isinstance(checkpoint, dict):
        # Formats courants de sauvegarde
        for key in ['state_dict', 'model_state_dict', 'model', 'net']:
            if key in checkpoint:
                return checkpoint[key]
        
        # Si le checkpoint est directement un state_dict
        if all(isinstance(v, torch.Tensor) for v in checkpoint.values()):
            return checkpoint
            
        # Cas particulier: le checkpoint contient d'autres métadonnées
        tensor_keys = {k: v for k, v in checkpoint.items() if isinstance(v, torch.Tensor)}
        if tensor_keys:
            return tensor_keys
    
    elif hasattr(checkpoint, 'state_dict'):
        # Le checkpoint est un modèle PyTorch
        return checkpoint.state_dict()
    
    else:
        raise ValueError(f"Format de checkpoint non reconnu: {type(checkpoint)}")

def clean_state_dict(state_dict, model_architecture):
    """
    Nettoie et adapte le state_dict pour l'architecture cible
    """
    cleaned_dict = {}
    
    for key, value in state_dict.items():
        # Supprimer les préfixes courants
        cleaned_key = key
        for prefix in ['module.', 'model.', '_orig_mod.']:
            if cleaned_key.startswith(prefix):
                cleaned_key = cleaned_key[len(prefix):]
        
        # Adaptation spécifique selon l'architecture
        if model_architecture == 'efficientnet_b4':
            # Ajouter le préfixe efficientnet si nécessaire
            if not cleaned_key.startswith('efficientnet.'):
                cleaned_key = f'efficientnet.{cleaned_key}'
                
        elif model_architecture == 'resnet18':
            # Ajouter le préfixe resnet si nécessaire
            if not cleaned_key.startswith('resnet.'):
                cleaned_key = f'resnet.{cleaned_key}'
        
        # Ignorer les couches de classification qui peuvent avoir des dimensions différentes
        if any(classifier_key in cleaned_key for classifier_key in ['classifier.', 'fc.', 'head.']):
            print(f"⚠️ Ignoré: {cleaned_key} (couche de classification)")
            continue
            
        cleaned_dict[cleaned_key] = value
    
    return cleaned_dict

def validate_loaded_model(model):
    """
    Valide que le modèle a été chargé correctement
    """
    # Vérifier que le modèle n'est pas vide
    param_count = sum(p.numel() for p in model.parameters())
    if param_count == 0:
        raise ValueError("❌ Le modèle n'a aucun paramètre")
    
    print(f"📊 Nombre total de paramètres: {param_count:,}")
    
    # Vérifier l'absence de valeurs NaN/Inf dans les paramètres
    for name, param in model.named_parameters():
        if torch.isnan(param).any():
            raise ValueError(f"❌ Valeurs NaN détectées dans {name}")
        if torch.isinf(param).any():
            raise ValueError(f"❌ Valeurs infinies détectées dans {name}")
    
    # Afficher quelques statistiques sur les premiers poids
    first_param = next(model.parameters())
    print(f"📈 Statistiques du premier paramètre:")
    print(f"   - Shape: {first_param.shape}")
    print(f"   - Mean: {first_param.mean().item():.6f}")
    print(f"   - Std: {first_param.std().item():.6f}")
    print(f"   - Min: {first_param.min().item():.6f}")
    print(f"   - Max: {first_param.max().item():.6f}")

# Classification logic
@app.route('/classify-image', methods=['POST'])
def classify_image_debug():
    """
    Version synchronisée avec le test local - Route complète
    """
    connection = None
    cursor = None
    
    # Log de début
    logger.info("🚀 Début de la classification...")
    
    try:
        # 1. VALIDATION DES ENTRÉES - AVEC DEBUG
        logger.info("📋 Validation des entrées...")
        
        if 'image' not in request.files:
            logger.error("❌ Aucune image dans la requête")
            return jsonify({'error': 'Aucune image téléchargée', 'step': 'validation'}), 400
            
        file = request.files['image']
        model_id = request.form.get('model_id')
        
        logger.info(f"📁 Fichier reçu: {file.filename}")
        logger.info(f"🆔 Model ID: {model_id}")
        
        if not model_id:
            logger.error("❌ Aucun model_id fourni")
            return jsonify({'error': 'Aucun modèle sélectionné', 'step': 'validation'}), 400

        # 2. SAUVEGARDE DE L'IMAGE - AVEC DEBUG
        logger.info("💾 Sauvegarde de l'image...")
        
        try:
            filename = save_uploaded_file(file)
            if not filename:
                logger.error("❌ Échec de sauvegarde du fichier")
                return jsonify({'error': 'Format de fichier invalide', 'step': 'file_save'}), 400
            
            logger.info(f"✅ Image sauvegardée: {filename}")
            
        except Exception as save_error:
            logger.error(f"❌ Erreur de sauvegarde: {str(save_error)}")
            return jsonify({'error': f'Erreur de sauvegarde: {str(save_error)}', 'step': 'file_save'}), 500
        
        # 3. VÉRIFICATION DE LA BASE DE DONNÉES - AVEC DEBUG
        logger.info("🗄️ Vérification de la base de données...")
        
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT model_type, model_path FROM models WHERE id = %s", (model_id,))
            model_info = cursor.fetchone()
            
            logger.info(f"📊 Info modèle: {model_info}")
            
            if not model_info:
                logger.error(f"❌ Modèle {model_id} non trouvé en base")
                return jsonify({'error': f'Modèle {model_id} non trouvé', 'step': 'database'}), 404
                
            if model_info['model_type'] != 'classification':
                logger.error(f"❌ Type de modèle incorrect: {model_info['model_type']}")
                return jsonify({'error': 'Le modèle n\'est pas un modèle de classification', 'step': 'database'}), 400
            
            logger.info("✅ Modèle validé en base de données")
            
        except Exception as db_error:
            logger.error(f"❌ Erreur base de données: {str(db_error)}")
            return jsonify({'error': f'Erreur base de données: {str(db_error)}', 'step': 'database'}), 500
        
        # 4. CHARGEMENT DU MODÈLE - AVEC DEBUG DÉTAILLÉ
        logger.info("🧠 Chargement du modèle...")
        
        try:
            # Vérification de l'existence du fichier modèle
            model_path = os.path.join(MODEL_BASE_DIR, model_info['model_path'])
            logger.info(f"📍 Chemin du modèle: {model_path}")
            
            if not os.path.exists(model_path):
                logger.error(f"❌ Fichier modèle introuvable: {model_path}")
                return jsonify({'error': f'Fichier modèle introuvable: {model_path}', 'step': 'model_file'}), 404
            
            # Chargement du modèle avec la fonction corrigée
            model = load_compatible_model(model_path)
            logger.info("✅ Modèle chargé avec succès")
            
        except Exception as model_error:
            logger.error(f"❌ Erreur de chargement du modèle: {str(model_error)}")
            logger.error(f"📍 Traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Erreur de chargement du modèle: {str(model_error)}', 'step': 'model_load'}), 500

        # 5. PRÉPARATION DE L'IMAGE - AVEC DEBUG
        logger.info("🖼️ Préparation de l'image...")
        
        try:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            logger.info(f"📍 Chemin image: {img_path}")
            
            if not os.path.exists(img_path):
                logger.error(f"❌ Image non trouvée: {img_path}")
                return jsonify({'error': f'Image non trouvée: {img_path}', 'step': 'image_load'}), 404
            
            # Transformations EXACTES de l'entraînement
            transform = transforms.Compose([
                transforms.Resize((380, 380)),  # ✅ Même taille que l'entraînement
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
            img = Image.open(img_path).convert('RGB')
            logger.info(f"🖼️ Image chargée: {img.size}")
            
            img_tensor = transform(img).unsqueeze(0)
            logger.info(f"🔢 Tensor image: {img_tensor.shape}")
            
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            img_tensor = img_tensor.to(device)
            model = model.to(device)
            
            logger.info(f"⚙️ Device utilisé: {device}")
            
        except Exception as img_error:
            logger.error(f"❌ Erreur de préparation image: {str(img_error)}")
            return jsonify({'error': f'Erreur de préparation image: {str(img_error)}', 'step': 'image_prep'}), 500
        
        # 6. PRÉDICTION AVEC FONCTION CENTRALISÉE - AVEC DEBUG COMPLET
        logger.info("🔮 Prédiction...")
        
        try:
            # Utilisation de la fonction centralisée pour garantir la synchronisation
            classification_results = perform_classification(model, img_tensor, device)
            
            logger.info(f"🔢 Outputs shape: {classification_results['outputs'].shape}")
            logger.info(f"🔢 Outputs values: {classification_results['outputs']}")
            logger.info(f"🎯 Classe prédite: {classification_results['predicted_class_name']}")
            logger.info(f"🎯 Confiance: {classification_results['confidence']:.4f}")
            logger.info(f"🎯 Prob Normal: {classification_results['prob_normal']:.4f}")
            logger.info(f"🎯 Prob Glaucome: {classification_results['prob_glaucoma']:.4f}")
            
            # Vérification de la cohérence des résultats
            if len(classification_results['outputs'].shape) != 2 or classification_results['outputs'].shape[1] != 2:
                logger.error(f"❌ Format de sortie incorrect: {classification_results['outputs'].shape}")
                return jsonify({'error': f"Format de sortie incorrect: {classification_results['outputs'].shape}", 'step': 'prediction'}), 500

                
        except Exception as pred_error:
            logger.error(f"❌ Erreur de prédiction: {str(pred_error)}")
            logger.error(f"📍 Traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Erreur de prédiction: {str(pred_error)}', 'step': 'prediction'}), 500
        
        # 7. GÉNÉRATION DE LA RÉPONSE AVEC DONNÉES SYNCHRONISÉES - AVEC DEBUG
        logger.info("📝 Génération de la réponse...")
        
        try:
            # Génération du rapport avec les MÊMES données de classification
            try:
                report = generate_classification_report(classification_results, filename)
                logger.info("✅ Rapport généré avec succès")
            except Exception as report_error:
                logger.warning(f"⚠️ Erreur génération rapport: {str(report_error)}")
                # Rapport de fallback avec les données de classification
                report = f"""
📊 ANALYSE RAPIDE:
- Classe: {classification_results['predicted_class_name']}
- Confiance: {classification_results['confidence']*100:.2f}%
- Probabilités: Normal={classification_results['prob_glaucoma']*100:.2f}%, Glaucome={classification_results['prob_normal']*100:.2f}%
"""
            
            # Construction de la réponse JSON avec les données centralisées
            response_data = {
                'success': True,
                'predicted_class': classification_results['predicted_class_name'],
                'confidence': float(classification_results['confidence'] * 100),
                'probabilities': {
                    'Normal': float(classification_results['prob_normal'] * 100),
                    'Glaucome': float(classification_results['prob_glaucoma'] * 100)
                },
                'report': report,
                'original': url_for('uploaded_file', filename=filename),
                'debug_info': {
                    'model_path': model_info['model_path'],
                    'image_filename': filename,
                    'device': str(device),
                    'outputs_shape': list(classification_results['outputs'].shape),
                    'predicted_class_idx': classification_results['predicted_class_idx']
                }
            }
            
            logger.info("✅ Réponse générée avec succès")
            logger.info(f"📊 Réponse: {json.dumps(response_data, indent=2)}")

            # Sauvegarde du résultat en base
            # Le technicien choisit : 'en_attente' (validation admin) ou 'approuve' (direct)
            try:
                conn_save = create_connection()
                cur_save = conn_save.cursor()
                demande_validation_cls = request.form.get('demande_validation', 'false').lower() == 'true'
                statut_cls = 'en_attente' if demande_validation_cls else 'approuve'
                cur_save.execute("""
    INSERT INTO results_classification
    (user_id, image_id, image_path, predicted_class, confidence,
     prob_normal, prob_glaucoma, statut, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
""", (
    session.get('user_id'),
    filename,
    os.path.join(app.config['UPLOAD_FOLDER'], filename),
    classification_results['predicted_class_name'],
    float(classification_results['confidence']),
    float(classification_results['prob_normal']),
    float(classification_results['prob_glaucoma']),
    statut_cls
))
                conn_save.commit()
                response_data['result_id'] = cur_save.lastrowid
                response_data['statut'] = statut_cls
                logger.info(f"✅ Résultat sauvegardé ({statut_cls}), id={cur_save.lastrowid}")
            except Exception as db_save_error:
                logger.warning(f"⚠️ Sauvegarde résultat échouée: {str(db_save_error)}")
            finally:
                if 'cur_save' in locals(): cur_save.close()
                if 'conn_save' in locals() and conn_save.is_connected(): conn_save.close()

            return jsonify(response_data)
            
        except Exception as response_error:
            logger.error(f"❌ Erreur génération réponse: {str(response_error)}")
            logger.error(f"📍 Traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Erreur génération réponse: {str(response_error)}', 'step': 'response'}), 500

    except Exception as e:
        # GESTION D'ERREUR GLOBALE AVEC MAXIMUM DE DEBUG
        error_msg = f"Erreur critique de classification: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.error(f"📍 Traceback complet:")
        logger.error(traceback.format_exc())
        
        # Informations système pour le debug
        debug_info = {
            'python_version': sys.version,
            'torch_version': torch.__version__,
            'cuda_available': torch.cuda.is_available(),
            'error_type': type(e).__name__,
            'error_message': str(e)
        }
        
        return jsonify({
            'error': error_msg,
            'step': 'global_error',
            'debug_info': debug_info,
            'traceback': traceback.format_exc()
        }), 500
        
    finally:
        # Nettoyage GARANTI
        try:
            if cursor: 
                cursor.close()
                logger.info("🧹 Cursor fermé")
            if connection and connection.is_connected(): 
                connection.close()
                logger.info("🧹 Connexion DB fermée")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("🧹 Cache CUDA vidé")
        except Exception as cleanup_error:
            logger.error(f"⚠️ Erreur de nettoyage: {str(cleanup_error)}")

#clean the report text
def remove_non_latin1(text):
    """Remove characters not supported by latin-1 (e.g., emojis)"""
    return ''.join(c if 0 <= ord(c) <= 255 else '?' for c in text)

# routing for downloading the classification pdf report
@app.route('/download-classification-pdf', methods=['POST'])
def download_classification_pdf():
    data = request.json
    classification_results = data.get('classification_results')
    image_data = data.get('image_data')
    image_url = data.get('image_url')
    user_cin = session.get('cin', 'Utilisateur inconnu')
    user_fname = session.get('first_name', '')
    user_lname = session.get('last_name', '')
    full_name = f"{user_fname} {user_lname}".strip() or 'Utilisateur inconnu'

    image_path = None
    image_bytes = None

    # 1. If image_data (base64) is present, decode it
    if image_data and image_data.startswith('data:image'):
        import base64
        header, encoded = image_data.split(',', 1)
        image_bytes = base64.b64decode(encoded)
    # 2. Else, try to use image_url as a file path
    elif image_url and image_url.startswith('/uploads/'):
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_url.split('/')[-1])

    # 3. Generate the PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Logo
    logo_path = os.path.join('static', 'assets', 'new_logo_black.png')
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)
        pdf.set_xy(45, 10)
    else:
        pdf.set_xy(10, 10)

    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "       Bassar, votre analyse rétinienne", ln=True, align='L')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Rapport d'Analyse - Classification", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    from datetime import datetime
    now = datetime.now()
    pdf.cell(0, 10, f"Généré le: {now.strftime('%d/%m/%Y à %H:%M:%S')}", ln=True, align='C')
    pdf.cell(0, 10, f"Utilisateur: {full_name}", ln=True, align='C')
    pdf.cell(0, 10, f"Identifiant du patient: {user_cin}", ln=True, align='C')
    pdf.ln(5)

    # Image
    if image_bytes:
        import tempfile
        import re
        match = re.match(r'data:image/(png|jpeg|jpg);base64', image_data)
        ext = match.group(1) if match else 'png'
        if ext == 'jpg':
            ext = 'jpeg'
        suffix = f'.{ext}'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(image_bytes)
            tmp.flush()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Image analysée:", ln=True)
            pdf.image(tmp.name, x=pdf.get_x(), y=pdf.get_y(), w=80)
            pdf.ln(75)  # Space after image
        os.unlink(tmp.name)
    elif image_path and os.path.exists(image_path):
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Image analysée:", ln=True)
        pdf.image(image_path, x=pdf.get_x(), y=pdf.get_y(), w=80)
        pdf.ln(75)  # Space after image
    else:
        pdf.cell(0, 10, "Image non disponible", ln=True)
        pdf.ln(10)  # Space if no image

    # Add extra margin before report text
    pdf.ln(16)

    # Rapport détaillé
    filename = data.get('filename')
    if not filename or filename == "Image transmise":
        # Try to get from image_path if available
        filename = os.path.basename(image_path) if image_path else "Image inconnue"
    from app import generate_classification_report, remove_non_latin1
    report_text = generate_classification_report(classification_results, filename, operator_name=full_name, patient_id=user_cin)
    report_text = remove_non_latin1(report_text)
    pdf.set_font("Arial", '', 11)
    for line in report_text.splitlines():
        pdf.multi_cell(0, 8, line)

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name="rapport_classification.pdf",
        mimetype="application/pdf"
    )

# routing for downloading the segmentation pdf report
@app.route('/download-segmentation-pdf', methods=['POST'])
def download_segmentation_pdf():
    data = request.json
    image_data = data.get('original_image')
    result_data = data.get('result_image')
    metrics = data.get('metrics', {})
    user_fname = session.get('first_name', 'Utilisateur inconnu')
    user_lname = session.get('last_name', 'Utilisateur inconnu')
    full_name = user_fname + " " + user_lname
    user_cin = str(session.get('cin', 'Utilisateur inconnu'))

    from fpdf import FPDF
    import base64
    import tempfile
    import re

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Logo
    logo_path = os.path.join('static', 'assets', 'new_logo_black.png')
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)
        pdf.set_xy(45, 10)
    else:
        pdf.set_xy(10, 10)

    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "      Bassar, votre analyse rétinienne", ln=True, align='L')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Rapport d'Analyse - Segmentation", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    now = datetime.now()
    pdf.cell(0, 10, f"Généré le: {now.strftime('%d/%m/%Y à %H:%M:%S')}", ln=True, align='C')
    pdf.cell(0, 10, f"Utilisateur: {full_name}", ln=True, align='C')
    pdf.cell(0, 10, f"Identifiant du patient: {user_cin}", ln=True, align='C')
    pdf.ln(5)

    # Images
    def add_image_from_data(image_data, label):
        if image_data and image_data.startswith('data:image'):
            match = re.match(r'data:image/(png|jpeg|jpg);base64', image_data)
            ext = match.group(1) if match else 'png'
            if ext == 'jpg':
                ext = 'jpeg'
            suffix = f'.{ext}'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(base64.b64decode(image_data.split(',')[1]))
                tmp.flush()
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, label, ln=True)
                pdf.image(tmp.name, x=pdf.get_x(), y=pdf.get_y(), w=80)
                pdf.ln(90)
            os.unlink(tmp.name)
        else:
            pdf.cell(0, 10, f"{label}: Image non disponible", ln=True)
            pdf.ln(10)

    add_image_from_data(image_data, "Image originale")
    add_image_from_data(result_data, "Image segmentée")

    # Metrics
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Métriques de segmentation:", ln=True)
    pdf.set_font("Arial", '', 11)
    metric_explanations = {
        "Dimensions": "      Taille de l'image (pixels)",
        "Taille fichier": "Poids du fichier image",
        "IoU": "Mesure le chevauchement entre la zone prédite et la zone réelle. Une valeur élevée indique que la segmentation correspond bien à la réalité.",
        "Dice": "Le coefficient de Dice évalue la similarité entre l'image prédite et la vérité terrain. Plus il est proche de 100 %, meilleure est la correspondance.",
        "Précision": "Indique la proportion des pixels prédits comme positifs (lésion, vaisseaux, etc.) qui sont réellement corrects.",
        "Rappel": "Mesure la capacité du modèle à détecter tous les pixels réellement positifs. Un rappel élevé signifie peu d'éléments manqués.",
        "Exactitude": "Reflète le pourcentage global de pixels correctement classés, qu'ils soient positifs ou négatifs."
    }

    for key, value in metrics.items():
        explanation = metric_explanations.get(key, "")
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(50, 10, f"{key.capitalize()}: {value}", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 10, explanation)
        pdf.ln(2)

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name="rapport_segmentation.pdf",
        mimetype="application/pdf"
    )

#route for contact form
@app.route('/contact', methods=['POST'])
def contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    
    # Construction du message
    full_message = f"Nom: {name}\nEmail: {email}\n\nMessage:\n{message}"
    msg = MIMEText(full_message)
    msg['Subject'] = f"Nouveau message de {name} via BassarCare"
    msg['From'] = 'aababou19@gmail.com'  # doit correspondre au compte qui envoie
    msg['To'] = 'aababou19@gmail.com'    # ou une autre adresse de réception

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('aababou19@gmail.com', 'jann uxxu ivwl evxv')
            smtp.send_message(msg)
        flash('Message envoyé avec succès !', 'success')
    except Exception as e:
        print(e)
        flash('Une erreur est survenue. Essayez plus tard.', 'error')
    
    return render_template('home/home.html')   # ou une page de remerciement
# Resultat
@app.route('/user/telecharger_resultat/<result_type>/<int:result_id>', methods=['GET'])
def telecharger_resultat(result_type, result_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Non autorisé'}), 403
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            f"SELECT * FROM {table} WHERE id = %s AND statut = 'approuve' AND user_id = %s",
            (result_id, session['user_id'])
        )
        r = cursor.fetchone()
        if not r:
            return jsonify({'error': 'Résultat non trouvé ou non autorisé'}), 404
        return jsonify({'pdf_url': url_for('rapport_pdf', result_type=result_type, result_id=result_id)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/user/check_approbations')
def check_approbations():
    """Retourne les résultats passés à 'approuve' pour l'utilisateur courant (polling JS)."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Non autorisé'}), 403
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, image_id, 'classification' AS result_type, predicted_class, created_at
            FROM results_classification WHERE statut = 'approuve' AND soumis_admin = 1 AND user_id = %s
            UNION ALL
            SELECT id, image_id, 'segmentation' AS result_type, NULL AS predicted_class, created_at
            FROM results_segmentation WHERE statut = 'approuve' AND soumis_admin = 1 AND user_id = %s
            ORDER BY created_at DESC
        """, (session['user_id'], session['user_id']))
        approuves = cursor.fetchall()
        # Convertir les dates en string pour JSON
        for r in approuves:
            if r.get('created_at'):
                r['created_at'] = r['created_at'].strftime('%d/%m/%Y %H:%M')
        return jsonify({'approuves': approuves})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()




@app.route('/user/marquer_telecharge/<result_type>/<int:result_id>', methods=['POST'])
def marquer_telecharge(result_type, result_id):
    """Marque un resultat comme telecharge pour qu il ne reapparaisse plus apres actualisation."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Non autorise'}), 403
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute(
            f"UPDATE {table} SET statut = 'telecharge' WHERE id = %s AND user_id = %s AND statut = 'approuve'",
            (result_id, session['user_id'])
        )
        connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/user/rapport_texte/<result_type>/<int:result_id>')
def rapport_texte(result_type, result_id):
    """Retourne le rapport en texte JSON pour l'affichage dans la modal (bouton Voir rapport)."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Non autorisé'}), 403
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            f"SELECT * FROM {table} WHERE id = %s AND statut = 'approuve' AND user_id = %s",
            (result_id, session['user_id'])
        )
        r = cursor.fetchone()
        if not r:
            return jsonify({'error': 'Résultat non trouvé'}), 404

        user_fname = session.get('first_name', '')
        user_lname = session.get('last_name', '')
        full_name = f"{user_fname} {user_lname}".strip() or 'Utilisateur inconnu'
        user_cin = str(session.get('cin', 'Inconnu'))

        if result_type == 'classification':
            classification_results = {
                'predicted_class_name': r.get('predicted_class', 'N/A'),
                'confidence': float(r.get('confidence', 0)),
                'prob_normal': float(r.get('prob_normal', 0)),
                'prob_glaucoma': float(r.get('prob_glaucoma', 0)),
            }
            rapport = generate_classification_report(
                classification_results,
                r.get('image_id', 'Inconnu'),
                operator_name=full_name,
                patient_id=user_cin
            )
            rapport = remove_non_latin1(rapport)
        else:
            lines = [
                f"Rapport d'Analyse - Segmentation",
                f"Utilisateur : {full_name}",
                f"Identifiant patient : {user_cin}",
                f"Image : {r.get('image_id', 'Inconnu')}",
                "",
                "Métriques de segmentation :",
            ]
            metrics_map = {
                'iou': 'IoU',
                'dice': 'Dice',
                'precision_val': 'Précision',
                'recall_val': 'Rappel',
                'accuracy': 'Exactitude'
            }
            for col, label in metrics_map.items():
                val = r.get(col)
                if val is not None:
                    lines.append(f"  {label} : {float(val)*100:.2f}%")
            rapport = "\n".join(lines)

        return jsonify({'rapport': rapport})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@app.route('/user/rapport_pdf/<result_type>/<int:result_id>')
def rapport_pdf(result_type, result_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    table = 'results_classification' if result_type == 'classification' else 'results_segmentation'
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            f"SELECT * FROM {table} WHERE id = %s AND statut = 'approuve' AND user_id = %s",
            (result_id, session['user_id'])
        )
        r = cursor.fetchone()
        if not r:
            flash('Résultat non trouvé ou non autorisé.', 'danger')
            return redirect(url_for('user_dashboard'))

        user_fname = session.get('first_name', '')
        user_lname = session.get('last_name', '')
        full_name = f"{user_fname} {user_lname}".strip() or 'Utilisateur inconnu'
        user_cin = str(session.get('cin', 'Inconnu'))

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Logo — identique au rapport original
        logo_path = os.path.join('static', 'assets', 'new_logo_black.png')
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=30)
            pdf.set_xy(45, 10)
        else:
            pdf.set_xy(10, 10)

        pdf.set_font("Arial", 'B', 18)
        titre_type = "Classification" if result_type == 'classification' else "Segmentation"
        pdf.cell(0, 10, "       Bassar, votre analyse retinienne", ln=True, align='L')
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Rapport d'Analyse - {titre_type}", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        now = datetime.now()
        pdf.cell(0, 10, f"Genere le: {now.strftime('%d/%m/%Y a %H:%M:%S')}", ln=True, align='C')
        pdf.cell(0, 10, f"Utilisateur: {full_name}", ln=True, align='C')
        pdf.cell(0, 10, f"Identifiant du patient: {user_cin}", ln=True, align='C')
        pdf.ln(5)

        # Image analysée
        image_path = r.get('image_path', '')
        if image_path and os.path.exists(image_path):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Image analysee:", ln=True)
            pdf.image(image_path, x=pdf.get_x(), y=pdf.get_y(), w=80)
            pdf.ln(75)

        pdf.ln(16)

        if result_type == 'classification':
            # Reconstruction du dict classification_results exactement comme lors de l'analyse
            classification_results = {
                'predicted_class_name': r.get('predicted_class', 'N/A'),
                'confidence': float(r.get('confidence', 0)),
                'prob_normal': float(r.get('prob_normal', 0)),
                'prob_glaucoma': float(r.get('prob_glaucoma', 0)),
            }
            # Génération du rapport avec la même fonction que lors de l'analyse initiale
            report_text = generate_classification_report(
                classification_results,
                r.get('image_id', 'Inconnu'),
                operator_name=full_name,
                patient_id=user_cin
            )
            report_text = remove_non_latin1(report_text)
            pdf.set_font("Arial", '', 11)
            for line in report_text.splitlines():
                pdf.multi_cell(0, 8, line)
        else:
            # Segmentation — même structure que download_segmentation_pdf
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Metriques de segmentation:", ln=True)
            pdf.set_font("Arial", '', 11)
            metric_explanations = {
                'IoU': "Mesure le chevauchement entre la zone predite et la zone reelle.",
                'Dice': "Evalue la similarite entre l'image predite et la verite terrain.",
                'Precision': "Proportion des pixels predits positifs qui sont corrects.",
                'Rappel': "Capacite du modele a detecter tous les pixels reellement positifs.",
                'Exactitude': "Pourcentage global de pixels correctement classes."
            }
            metrics_map = {
                'iou': 'IoU',
                'dice': 'Dice',
                'precision_val': 'Precision',
                'recall_val': 'Rappel',
                'accuracy': 'Exactitude'
            }
            for col, label in metrics_map.items():
                val = r.get(col)
                if val is not None:
                    explanation = metric_explanations.get(label, "")
                    pdf.set_font("Arial", 'B', 11)
                    pdf.cell(50, 10, f"{label}: {float(val)*100:.2f}%", ln=0)
                    pdf.set_font("Arial", '', 10)
                    pdf.multi_cell(0, 10, explanation)
                    pdf.ln(2)
            # Image segmentée
            result_path = r.get('result_path', '')
            if result_path and os.path.exists(result_path):
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, "Image segmentee:", ln=True)
                pdf.image(result_path, x=pdf.get_x(), y=pdf.get_y(), w=80)
                pdf.ln(90)

        pdf_bytes = pdf.output(dest='S').encode('latin1')
        download_name = f"rapport_{result_type}_{result_id}.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=download_name,
            mimetype="application/pdf"
        )
    except Exception as e:
        flash(f'Erreur génération PDF: {str(e)}', 'danger')
        return redirect(url_for('user_dashboard'))
    finally:
        cursor.close()
        connection.close()
# ---------------------------------------------------------------
# ROUTE : Page HTML des statistiques descriptives (Admin)
# ---------------------------------------------------------------

@app.route('/admin/statistiques_page')
def admin_statistiques_page():
    """Affiche la page HTML des statistiques descriptives (Gestion des statistiques)."""
    if not session.get('is_admin'):
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('login'))
    return render_template('admin/admin_statistiques.html')

# ---------------------------------------------------------------
# ROUTE : Statistiques personnelles de l'utilisateur (pour diagramme)
# ---------------------------------------------------------------

@app.route('/user/mes_stats')
def user_mes_stats():
    """Retourne les statistiques de résultats de l'utilisateur courant."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        # Tous les résultats soumis à l'admin (soumis_admin = 1)
        # En attente
        cursor.execute("""
            SELECT COUNT(*) AS n FROM results_classification
            WHERE user_id = %s AND soumis_admin = 1 AND statut = 'en_attente'
        """, (uid,))
        en_attente_cls = cursor.fetchone()['n']
        cursor.execute("""
            SELECT COUNT(*) AS n FROM results_segmentation
            WHERE user_id = %s AND soumis_admin = 1 AND statut = 'en_attente'
        """, (uid,))
        en_attente_seg = cursor.fetchone()['n']

        # Approuvés (soumis_admin = 1)
        cursor.execute("""
            SELECT COUNT(*) AS n FROM results_classification
            WHERE user_id = %s AND soumis_admin = 1 AND statut IN ('approuve', 'telecharge')
        """, (uid,))
        approuves_cls = cursor.fetchone()['n']
        cursor.execute("""
            SELECT COUNT(*) AS n FROM results_segmentation
            WHERE user_id = %s AND soumis_admin = 1 AND statut IN ('approuve', 'telecharge')
        """, (uid,))
        approuves_seg = cursor.fetchone()['n']

        # Refusés (soumis_admin = 1)
        cursor.execute("""
            SELECT COUNT(*) AS n FROM results_classification
            WHERE user_id = %s AND soumis_admin = 1 AND statut = 'refuse'
        """, (uid,))
        refuses_cls = cursor.fetchone()['n']
        cursor.execute("""
            SELECT COUNT(*) AS n FROM results_segmentation
            WHERE user_id = %s AND soumis_admin = 1 AND statut = 'refuse'
        """, (uid,))
        refuses_seg = cursor.fetchone()['n']

        en_attente = en_attente_cls + en_attente_seg
        approuves  = approuves_cls  + approuves_seg
        refuses    = refuses_cls    + refuses_seg
        total      = en_attente + approuves + refuses

        def pct(n): return round(n / total * 100, 1) if total else 0

        return jsonify({
            'en_attente': en_attente,
            'approuves':  approuves,
            'refuses':    refuses,
            'total':      total,
            'pct_attente':  pct(en_attente),
            'pct_approuves': pct(approuves),
            'pct_refuses':  pct(refuses),
        })
    finally:
        cursor.close()
        connection.close()



# ---------------------------------------------------------------
# EXÉCUTION DE L'APPLICATION
# ---------------------------------------------------------------
if __name__ == '__main__':
    # Création du dossier d'upload s'il n'existe pas
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    #  On ajoute host="0.0.0.0" pour le réseau
    app.run(host="0.0.0.0", port=5000, debug=True)