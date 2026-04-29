# 📱 BassarCare – Application Mobile

## Description

Cette application est la version mobile de l'application web **BassarCare**.  
Elle permet d'accéder à l'application depuis un téléphone Android.

La version mobile a été développée en utilisant :
- **Ionic Framework** : Framework pour créer l'interface mobile.
- **Capacitor** : Le pont qui permet d'utiliser les fonctions natives Android.

L'application mobile charge l'application web via une **adresse IP locale du serveur Flask**.

---

## Prérequis

Avant d'exécuter le projet, il faut installer les outils suivants :
- Node.js  
- Ionic Framework  
- Capacitor  
- Android Studio  

---

## 🛠 Configuration du Serveur (Backend Flask)

Avant de lancer l'application mobile, il faut modifier le fichier `app.py` du serveur Flask pour autoriser les connexions sur le réseau local.

Modifier la fin du fichier `app.py` comme ceci(ici, c'est déjà fait) :

```python
if __name__ == '__main__':
    # Création du dossier d'upload s'il n'existe pas
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # On ajoute host="0.0.0.0" pour permettre l'accès via le réseau local
    app.run(host="0.0.0.0", port=5000, debug=True)
Explication : host="0.0.0.0" permet au  téléphone de "voir" le serveur qui tourne sur ordinateur.
```

###  Lancer le serveur
Dans le terminal de projet principal (Web), lancez la commande :


```bash
python app.py
```
Gardez ce terminal ouvert. Le serveur doit tourner pour que l'application mobile fonctionne

---
### 0️⃣ Se déplacer dans le dossier contenant l'application mobile

```bash
cd mobileApp
```
Toutes les commandes suivantes doivent être exécutées dans ce dossier.
---
## 1️⃣ Installer Ionic et Capacitor
Installer Ionic globalement :
```bash
npm install -g @ionic/cli
```
Installer les dépendances du projet :
```bash
npm install
```
Cette commande installe toutes les dépendances nécessaires au projet.

---
## 2️⃣ Construire l'application
```bash
ionic build
```

Cette commande génère le dossier www/ qui contient la version web utilisée par l'application mobile.

---
## 3️⃣ Configuration de l'adresse IP du serveur
L'application mobile se connecte au serveur Flask via une adresse IP locale.

Ouvrir le fichier : capacitor.config.ts

 Modifier l'adresse IP dans la configuration :
```
TypeScript
server: {
  url: 'http://192.168.X.X:5000',
  cleartext: true
}
```
Remplacer 192.168.X.X par l'adresse IP du PC qui exécute le serveur Flask.

---
## 4️⃣ Synchroniser le projet avec Android
```bash
npx cap sync android
```
---
## 5️⃣ Ouvrir le projet dans Android Studio
```bash
npx cap open android
```
```plaintext
⚙️ Activer le Débogage USB (Sur votre téléphone)
Avant de brancher votre téléphone, vous devez activer le mode développeur :

Allez dans les Paramètres de votre téléphone.

Allez dans À propos du téléphone.

Appuyez 7 fois rapidement sur Numéro de version (Build Number). Un message dira "Vous êtes maintenant développeur".

Revenez aux paramètres, allez dans Système ou Paramètres supplémentaires.

Ouvrez Options pour les développeurs.

Activez l'interrupteur Débogage USB.

Connectez le téléphone au PC par câble. Un message apparaîtra sur le téléphone : cochez "Toujours autoriser" et validez.

-Optionnel : Personnaliser l'icône de l'application
Pour changer l'icône par défaut (Ionic) par l'icône de BassarCare :

Dans Android Studio, faites un clic droit sur le dossier app (dans la vue Project).

Allez dans New -> Image Asset.

Dans Icon Type, laissez "Launcher Icons (Adaptive and Legacy)".

Dans Path, sélectionnez le fichier d'icône (logo de BassarCare).

Ajustez la taille avec le curseur Resize.

Cliquez sur Next, puis Finish.
```
---
## 6️⃣ Lancer l'application sur téléphone
Connecter un téléphone Android avec USB Debugging activé.

Cliquer sur Run ▶ dans Android Studio.

L'application sera installée sur le téléphone.

---
## 7️⃣ Générer le fichier APK


Dans Android Studio, allez dans : Build -> Build Bundle(s) / APK(s) -> Build APK(s).

Une fois terminé, une notification apparaît. Cliquez sur locate.

Le fichier APK se trouve dans : android/app/build/outputs/apk/debug/.

Installation : Copiez ce fichier sur votre téléphone et ouvrez-le pour installer l'application 
```plaintext
📂 Structure du projet

mobileApp/
│
├── android/            → Projet Android
├── src/                → Code source Ionic
├── www/                → Application compilée
├── capacitor.config.ts → Configuration (IP serveur)
├── package.json
└── README.md
🔗 Fonctionnement de l'application
L'utilisateur ouvre l'application mobile.

L'application charge l'application web via l'adresse IP du serveur Flask.

L'utilisateur peut utiliser les fonctionnalités depuis le téléphone.
Remarque!:

Pour que l’application mobile fonctionne correctement, le téléphone et l’ordinateur doivent être connectés au même réseau Wi-Fi.
```
