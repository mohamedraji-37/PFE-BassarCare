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
