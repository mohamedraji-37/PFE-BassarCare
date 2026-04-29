# 🧠 Medical Image Processing Web App

This is a Flask-based web application for managing, processing, and analyzing medical images using deep learning models for **segmentation** and **classification**. It supports admin and user roles, model upload, image inference, and report generation.

---

## 🚀 Features

### ✅ For Users
- Upload images for **segmentation** (e.g., optic disc/cup) or **classification** (e.g., glaucoma detection).
- View processing results and overlay visualizations.
- Download a PDF report with segmentation metrics or classification diagnosis.

### 🛠️ For Admins
- Manage (upload/delete) segmentation and classification models (`.pt` or `.pth`).
- View registered users.
- Delete user accounts if needed.

---

## 🗂 Project Structure

```plaintext
.
├── app.py # Main Flask application
├── database.py # MySQL database connection logic
├── create_admin.py # insert an admin profil to the database
├── model.py # U-Net model architecture
├── templates/              # HTML views (login, signup, dashboard)
│   ├── home/
│   │   └── home.html
│   ├── auth/
│   │   ├── sign-in.html
│   │   └── sign-up.html
│   ├── admin/
│   │   └── dashboard.html
│   └── user/
│       └── dashboard.html
├── static/ # styling and anything else
│ ├── CSS/
│ └── JS/
| └── Assets/ #pictures, Illustrations
├── uploads/ # Temporary uploaded and processed files
├── stored_models/ # Segmentation and classification models
│ ├── segmentation/
│ └── classification/
└── README.md
```

---

## ⚙️ Requirements

### 1. Install all dependencies manually using:


```bash
pip install flask mysql-connector-python torch torchvision pillow opencv-python fpdf
```
### 1. download the UNET model for segmentation :

```
https://drive.google.com/file/d/1Wl7-E6Tk3YpeJ7GIYScGvUeW9ou474yy/view
```

---

## 🧪 Usage

### 1. Configure the Database

Make sure your MySQL database :

```bash
create database Segment_db;
```
### Run database.py

To automatically create table structure that includes

- `users`: to handle user accounts and authentication
- `models`: to store metadata for uploaded models (type, name, path)

Edit the `create_connection()` function in `database.py` to include your MySQL credentials.

### 2. Run the Application

```bash
python app.py
```

Then open your browser and navigate to:

```
http://localhost:5000
```

---

## 🔐 User Roles

- **Regular Users** can:
  - Upload images
  - Run segmentation or classification
  - View/download results and reports

- **Admins** can:
  - Upload/delete models
  - Manage users

> After signing up, you can set a user as admin by updating the `is_admin` field in the database manually.

---

## 📄 PDF Reports

- **Segmentation**: includes mask, overlay, and metrics (IoU, Dice, etc.)
- **Classification**: includes glaucoma diagnosis with recommendations

Reports are generated and downloadable as `.pdf` files automatically.

---

## 🧠 Supported Models

### Formats:
- `.pth`: PyTorch `state_dict` (recommended)
- `.pt`: TorchScript

### Types:
- `segmentation`: U-Net based models
- `classification`: ResNet-based binary classifiers

Make sure your models are compatible with the expected architecture.

### For the model architecture used u can navigate:

```
https://github.com/nikhilroxtomar/Retina-Blood-Vessel-Segmentation-in-PyTorch/
```

---

## 📷 Image Requirements

- Accepted formats: JPG, PNG
- Automatically resized and normalized before inference

---

## 📦 API Endpoints (Optional Use)

- `POST /process-image` – for segmentation processing
- `POST /classify-image` – for glaucoma classification
- `GET /get-models` – list available models
- `POST /download-results` – generate a segmentation PDF report

---

## 🛡 Disclaimer

> This application is intended for research and educational purposes only. It is **not a substitute for professional medical advice**.

---

## 📬 Contact

For issues, suggestions, or contributions, feel free to open an issue or a pull request on the repository.
---
## 🌍 BassarCare – Language

Description

The BassarCare application supports multiple languages in order to make the interface accessible to different users.

The available languages are:

🇫🇷 French
EN English
AR Arabic

Translation management is implemented using Flask-Babel, the standard solution for Flask applications.

This feature allows the application to:

translate the entire user interface
change the language dynamically
keep the selected language during navigation
## ⚙️ Technical Implementation
##  Installation of Flask-Babel

Install the required library:
```bash
pip install flask-babel
```
## Configuration in app.py

Import Flask-Babel:
```python
from flask_babel import Babel, gettext as _, get_locale
```
Initialize Babel:
```python
babel = Babel(app)
```
## 🌐 Supported Languages

Define the available languages in the application:
```python
LANGUAGES = {
    'fr': 'Français',
    'en': 'English',
    'ar': 'العربية'
}
```
## Dynamic Language Selection

The selected language is stored in the user session.
```python
def select_locale():
    return session.get('lang', 'fr')

babel = Babel(app, locale_selector=select_locale)
```
How it works:

if no language is selected → French by default
the language remains active during the entire navigation
## Route to Change the Language

A route allows changing the application language.
```python
@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))
babel = Babel(app, locale_selector=select_locale)
```

Function:

saves the language in the session
automatically reloads the page
Injection into Templates

To make translations accessible in HTML templates:
```python
@app.context_processor
def inject_languages():
    return {
        'LANGUAGES': LANGUAGES,
        'CURRENT_LANG': str(get_locale()),
        '_': _
    }
```
In HTML templates, you can write:

{{ _('Connexion') }}
## Modification of HTML Templates

All interface texts have been replaced with translation functions.

Before
```
<h1>Connexion</h1>
```
After
```
<h1>{{ _('Connexion') }}</h1>
```
This modification was applied to the following pages:

Home
Login / Signup
User dashboard
Admin dashboard
Report pages
## Generation of Translation Files

Extraction of texts to translate:
```bash
pybabel extract -F babel.cfg -o messages.pot .
```
Initialization of languages:
```bash
pybabel init -i messages.pot -d translations -l en
pybabel init -i messages.pot -d translations -l ar
```
Generated structure:

translations/
 ├── en/
 │   └── LC_MESSAGES/messages.po
 └── ar/
     └── LC_MESSAGES/messages.po
 Translation of .po Files

Each text appears in the following form:

msgid "Connexion"
msgstr "Login"

The file contains all the text strings that need to be translated.

## Translations were adapted for:

English
Arabic
user experience
## Compilation of Translations

Once the translation is finished, compile the files:
```bash
pybabel compile -d translations
```
This command generates:

messages.mo

 ## Without this step, translations will not be taken into account by Flask.

## Language Change Button

A menu allows the user to choose the language.

Example in home.html:
```
<a href="{{ url_for('set_language', lang='en') }}">English</a>
<a href="{{ url_for('set_language', lang='ar') }}">العربية</a>
```
How it works:

the user clicks on a language
the session is updated
the page reloads with the new language
## 📱 Mobile Compatibility

Language management also works in the BassarCare mobile application, because it directly loads the Flask web application.

Thus:

the selected language is preserved
the mobile interface is automatically translated.