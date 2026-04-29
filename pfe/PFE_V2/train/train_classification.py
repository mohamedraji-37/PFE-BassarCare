# ============================================================
#  train_classification.py
#  Entraînement FROM SCRATCH — Classification Glaucome/Normal
#  Structure : étape par étape, indépendant de app.py
# ============================================================

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models

# ==============================================================
# ÉTAPE 1 — DATASET SYNTHÉTIQUE (pas besoin de vraies images)
# On simule des images rétiniennes pour tester tout le pipeline.
# Quand les vraies images arrivent → on remplace juste cette classe
# ==============================================================

class FakeRetinalDataset(Dataset):
    """
    Génère de fausses images rétiniennes aléatoires.

    Paramètres :
    - num_samples : nombre d'images à générer
    - img_size    : taille de chaque image (224x224 pixels)

    Chaque image est un tenseur de forme [3, 224, 224]
    (3 canaux RGB, largeur 224, hauteur 224)

    Labels :
    - 0 = Normal
    - 1 = Glaucome
    """
    def __init__(self, num_samples=200, img_size=224):
        self.num_samples = num_samples
        self.img_size    = img_size

        # Générer toutes les images aléatoirement en mémoire
        # torch.randn → valeurs entre -1 et 1 (distribution normale)
        self.images = torch.randn(num_samples, 3, img_size, img_size)

        # Labels aléatoires : 0 ou 1
        self.labels = torch.randint(0, 2, (num_samples,))

    def __len__(self):
        # PyTorch appelle cette méthode pour savoir combien d'images il y a
        return self.num_samples

    def __getitem__(self, idx):
        # PyTorch appelle cette méthode pour récupérer UNE image par son index
        return self.images[idx], self.labels[idx]


# ── Créer les datasets ──
# 200 images pour entraîner, 50 pour valider
train_dataset = FakeRetinalDataset(num_samples=200, img_size=224)
val_dataset   = FakeRetinalDataset(num_samples=50,  img_size=224)

# ── Créer les DataLoaders ──
# Le DataLoader découpe le dataset en "batchs" (paquets d'images)
# batch_size=16 → le modèle voit 16 images à la fois
# shuffle=True  → mélange les images à chaque epoch (important pour le train)
train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
val_loader   = DataLoader(val_dataset,   batch_size=16, shuffle=False)

# ── Vérification Étape 1 ──
print("=" * 50)
print("ÉTAPE 1 — Dataset synthétique")
print("=" * 50)
images, labels = next(iter(train_loader))
print(f"✅ Taille d'un batch images : {images.shape}")
#    → torch.Size([16, 3, 224, 224])
#      16 images, 3 canaux RGB, 224x224 pixels
print(f"✅ Taille d'un batch labels : {labels.shape}")
#    → torch.Size([16])
print(f"✅ Exemple de labels        : {labels}")
#    → tensor([0, 1, 0, 1, 1, 0, ...])
print(f"✅ Nombre de batchs train   : {len(train_loader)}")
#    → 200 images / 16 par batch = 13 batchs
print()


# ==============================================================
# ÉTAPE 2 — ARCHITECTURE DU MODÈLE FROM SCRATCH
# On utilise EfficientNet-B4 SANS poids pré-entraînés (weights=None)
# "From scratch" = le modèle ne connaît RIEN au départ
# Il va tout apprendre uniquement depuis nos images rétiniennes
# ==============================================================

class GlaucomaClassifier(nn.Module):
    """
    Modèle de classification Glaucome/Normal basé sur EfficientNet-B4.

    Architecture :
    ┌─────────────────────────────────────────┐
    │  EfficientNet-B4 (backbone)             │
    │  → extrait les caractéristiques visuelles│
    │                                         │
    │  Classifier personnalisé :              │
    │  Linear(1792 → 256) + ReLU             │
    │  Dropout(0.3)                           │
    │  Linear(256 → 2)  ← 2 classes          │
    └─────────────────────────────────────────┘

    Paramètre num_classes = 2 :
    - Sortie 0 → Normal
    - Sortie 1 → Glaucome
    """
    def __init__(self, num_classes=2):
        super(GlaucomaClassifier, self).__init__()

        # weights=None → FROM SCRATCH, aucune connaissance préalable
        # (si on mettait weights=EfficientNet_B4_Weights.IMAGENET1K_V1
        #  ce serait du Transfer Learning — pas ce qu'on veut ici)
        self.backbone = models.efficientnet_b4(weights=None)

        # Récupérer la taille de la dernière couche du backbone
        # Pour EfficientNet-B4 c'est 1792 neurones
        num_features = self.backbone.classifier[1].in_features

        # Remplacer le classifier original par le nôtre
        # adapté à 2 classes (Normal / Glaucome)
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.4),                        # Évite l'overfitting
            nn.Linear(num_features, 256),             # 1792 → 256
            nn.ReLU(),                                # Activation non-linéaire
            nn.Dropout(p=0.3),                        # 2ème couche de régularisation
            nn.Linear(256, num_classes)               # 256 → 2 (sortie finale)
        )

    def forward(self, x):
        # x = batch d'images [batch_size, 3, 224, 224]
        # retourne les logits [batch_size, 2]
        # (pas encore de softmax ici → géré par la loss CrossEntropy)
        return self.backbone(x)


# ── Initialiser le modèle ──
# Choisir automatiquement GPU si disponible, sinon CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = GlaucomaClassifier(num_classes=2).to(device)

# ── Vérification Étape 2 ──
print("=" * 50)
print("ÉTAPE 2 — Architecture du modèle")
print("=" * 50)
print(f"✅ Device utilisé : {device}")

# Compter le nombre total de paramètres du modèle
total_params     = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"✅ Paramètres totaux     : {total_params:,}")
print(f"✅ Paramètres à entraîner: {trainable_params:,}")

# Tester un passage d'un batch dans le modèle (forward pass)
with torch.no_grad():
    test_input  = torch.randn(4, 3, 224, 224).to(device)  # 4 fausses images
    test_output = model(test_input)
print(f"✅ Forme de la sortie    : {test_output.shape}")
#    → torch.Size([4, 2])
#      4 images, 2 scores (un par classe)
print(f"✅ Exemple de sortie     : {test_output[0]}")
#    → tensor([ 0.12, -0.34]) ← scores bruts (logits)
#      La classe avec le score le plus haut = prédiction du modèle
print()
print("✅ Étapes 1 et 2 terminées — prêt pour l'Étape 3 (Loss + Optimiseur) !")


# ==============================================================
# ÉTAPE 3 — LOSS FUNCTION + OPTIMISEUR + SCHEDULER
#
# Loss Function (CrossEntropyLoss) :
#   → Mesure l'erreur entre la prédiction du modèle et la vraie réponse
#   → Doit descendre vers 0 pendant l'entraînement
#
# Optimiseur (AdamW) :
#   → C'est lui qui corrige les poids du modèle après chaque batch
#   → Il utilise le gradient (dérivée de la loss) pour savoir
#      dans quel sens corriger chaque poids
#   → lr (learning rate) = taille du pas de correction
#      trop grand → le modèle oscille et n'apprend pas
#      trop petit → le modèle apprend trop lentement
#
# Scheduler (CosineAnnealingLR) :
#   → Réduit automatiquement le learning rate au fil des epochs
#   → Au début : grands pas pour apprendre vite
#   → Vers la fin : petits pas pour affiner précisément
# ==============================================================

import torch.optim as optim

# ── Loss Function ──
# CrossEntropyLoss = la plus adaptée pour la classification multi-classes
# Elle combine en interne un Softmax + un calcul d'erreur logarithmique
#
# Exemple concret :
#   Vrai label       : Glaucome (1)
#   Sortie modèle    : [0.2, 0.8]  → 80% Glaucome = BONNE prédiction → Loss faible
#   Sortie modèle    : [0.9, 0.1]  → 10% Glaucome = MAUVAISE prédiction → Loss élevée
criterion = nn.CrossEntropyLoss()

# ── Optimiseur AdamW ──
# AdamW = Adam + Weight Decay (régularisation des poids)
# lr=1e-3       → learning rate de départ = 0.001
# weight_decay  → pénalise les poids trop grands → évite l'overfitting
optimizer = optim.AdamW(
    model.parameters(),
    lr=1e-3,
    weight_decay=1e-4
)

# ── Scheduler CosineAnnealingLR ──
# T_max = nombre total d'epochs
# Le learning rate suit une courbe en cosinus :
#   Epoch 1   → lr = 0.001   (départ)
#   Epoch 50  → lr = 0.0005  (milieu)
#   Epoch 100 → lr = 0.00001 (fin, très petit)
NUM_EPOCHS = 100
scheduler = optim.lr_scheduler.CosineAnnealingLR(
    optimizer,
    T_max=NUM_EPOCHS,
    eta_min=1e-6     # learning rate minimum à ne pas dépasser vers le bas
)

# ── Vérification Étape 3 ──
print("=" * 50)
print("ÉTAPE 3 — Loss + Optimiseur + Scheduler")
print("=" * 50)

# Simuler un calcul de loss sur un batch
images_test = torch.randn(4, 3, 224, 224).to(device)
labels_test = torch.tensor([0, 1, 0, 1]).to(device)   # 4 vrais labels

with torch.no_grad():
    outputs_test = model(images_test)                  # prédictions du modèle
    loss_test    = criterion(outputs_test, labels_test) # calcul de l'erreur

print(f"✅ Loss Function   : CrossEntropyLoss")
print(f"✅ Optimiseur      : AdamW  (lr=0.001, weight_decay=1e-4)")
print(f"✅ Scheduler       : CosineAnnealingLR (T_max={NUM_EPOCHS})")
print(f"✅ Exemple de Loss : {loss_test.item():.4f}")
#    → valeur élevée au départ (ex: 0.7432) car le modèle ne sait rien encore
#    → descendra progressivement vers 0 pendant l'entraînement
print(f"✅ Learning rate initial : {optimizer.param_groups[0]['lr']}")
print()


# ==============================================================
# ÉTAPE 4 — BOUCLES TRAIN ET VALIDATION
#
# train_one_epoch :
#   → Le modèle voit TOUTES les images d'entraînement une fois
#   → Pour chaque batch :
#       1. Forward pass  : le modèle fait une prédiction
#       2. Calcul loss   : on mesure l'erreur
#       3. Backward pass : on calcule les gradients (torch.backward)
#       4. optimizer.step: on corrige les poids du modèle
#   → Retourne : loss moyenne + accuracy sur tout le train
#
# validate :
#   → Le modèle voit les images de validation SANS se corriger
#   → torch.no_grad() → pas de calcul de gradient (plus rapide)
#   → Sert à mesurer si le modèle généralise bien sur des images inconnues
# ==============================================================

def train_one_epoch(model, loader, criterion, optimizer, device):
    """
    Entraîne le modèle sur toutes les images du loader (1 epoch).
    Retourne : (loss_moyenne, accuracy)
    """
    model.train()   # mode entraînement → active Dropout, BatchNorm en mode train

    total_loss = 0.0
    correct    = 0
    total      = 0

    for batch_idx, (images, labels) in enumerate(loader):
        # Envoyer les données sur GPU ou CPU
        images = images.to(device)
        labels = labels.to(device)

        # ── 1. Remettre les gradients à zéro ──
        # OBLIGATOIRE à chaque batch sinon les gradients s'accumulent
        optimizer.zero_grad()

        # ── 2. Forward pass ──
        # Le modèle calcule ses prédictions
        outputs = model(images)                    # [batch_size, 2]

        # ── 3. Calcul de la Loss ──
        # Compare les prédictions avec les vrais labels
        loss = criterion(outputs, labels)

        # ── 4. Backward pass ──
        # Calcule les gradients de chaque poids par rapport à la loss
        # C'est la "rétropropagation" — le cœur de l'apprentissage
        loss.backward()

        # ── 5. Gradient Clipping ──
        # Évite que les gradients deviennent trop grands (explosion)
        # max_norm=1.0 → limite la norme maximale des gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        # ── 6. Mise à jour des poids ──
        # L'optimiseur corrige les poids dans la direction du gradient
        optimizer.step()

        # ── Statistiques ──
        total_loss += loss.item()

        # La prédiction finale = classe avec le score le plus élevé
        predictions = outputs.argmax(dim=1)              # [batch_size]
        correct    += (predictions == labels).sum().item()
        total      += labels.size(0)

    avg_loss = total_loss / len(loader)   # loss moyenne sur tous les batchs
    accuracy = correct / total            # % de bonnes prédictions

    return avg_loss, accuracy


def validate(model, loader, criterion, device):
    """
    Évalue le modèle sur les images de validation (sans apprentissage).
    Retourne : (loss_moyenne, accuracy)
    """
    model.eval()   # mode évaluation → désactive Dropout, BatchNorm en mode eval

    total_loss = 0.0
    correct    = 0
    total      = 0

    with torch.no_grad():   # pas de calcul de gradient → plus rapide + économe
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss    = criterion(outputs, labels)

            total_loss += loss.item()
            predictions = outputs.argmax(dim=1)
            correct    += (predictions == labels).sum().item()
            total      += labels.size(0)

    avg_loss = total_loss / len(loader)
    accuracy = correct / total

    return avg_loss, accuracy


# ── Vérification Étape 4 ──
print("=" * 50)
print("ÉTAPE 4 — Boucles Train et Validation")
print("=" * 50)

# Tester une seule epoch pour vérifier que tout fonctionne
train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
val_loss,   val_acc   = validate(model, val_loader, criterion, device)

print(f"✅ Train  → Loss: {train_loss:.4f}  |  Accuracy: {train_acc*100:.1f}%")
print(f"✅ Val    → Loss: {val_loss:.4f}  |  Accuracy: {val_acc*100:.1f}%")
# → Accuracy ~50% normal au départ (données aléatoires = pile ou face)
# → Avec de vraies images elle montera progressivement
print()


# ==============================================================
# ÉTAPE 5 — BOUCLE COMPLÈTE : EARLY STOPPING + SAUVEGARDE
#
# Early Stopping :
#   → Si la val_loss ne s'améliore pas pendant N epochs consécutives
#     on arrête l'entraînement automatiquement
#   → Évite de gaspiller du temps et d'overfitter
#   → patience = 10 → on attend 10 epochs avant d'arrêter
#
# Sauvegarde du meilleur modèle :
#   → À chaque fois que la val_loss est meilleure qu'avant
#     on sauvegarde les poids dans best_glaucoma_model.pth
#   → À la fin on recharge automatiquement le meilleur modèle
# ==============================================================

import os

# Dossier de sauvegarde des modèles (même structure que app.py)
SAVE_DIR = os.path.join("stored_models", "classification")
os.makedirs(SAVE_DIR, exist_ok=True)
SAVE_PATH = os.path.join(SAVE_DIR, "best_glaucoma_model.pth")

# Paramètres Early Stopping
PATIENCE    = 10              # epochs sans amélioration avant arrêt
best_val_loss = float('inf')  # meilleure loss vue jusqu'ici (commence à l'infini)
no_improve    = 0             # compteur d'epochs sans amélioration

# Historique pour tracer les courbes Loss / Accuracy
history = {
    'train_loss': [],
    'val_loss':   [],
    'train_acc':  [],
    'val_acc':    []
}

print("=" * 50)
print("ÉTAPE 5 — Entraînement complet")
print("=" * 50)
print(f"Epochs max : {NUM_EPOCHS}  |  Patience : {PATIENCE}")
print(f"Modèle sauvegardé dans : {SAVE_PATH}")
print("-" * 50)

for epoch in range(1, NUM_EPOCHS + 1):

    # ── Entraînement ──
    train_loss, train_acc = train_one_epoch(
        model, train_loader, criterion, optimizer, device
    )

    # ── Validation ──
    val_loss, val_acc = validate(
        model, val_loader, criterion, device
    )

    # ── Mise à jour du scheduler ──
    # Réduit le learning rate selon la courbe cosinus
    scheduler.step()

    # ── Sauvegarder l'historique ──
    history['train_loss'].append(train_loss)
    history['val_loss'].append(val_loss)
    history['train_acc'].append(train_acc)
    history['val_acc'].append(val_acc)

    # ── Affichage ──
    lr_actuel = optimizer.param_groups[0]['lr']
    print(f"Epoch [{epoch:3d}/{NUM_EPOCHS}] "
          f"| Train Loss: {train_loss:.4f}  Acc: {train_acc*100:5.1f}% "
          f"| Val Loss: {val_loss:.4f}  Acc: {val_acc*100:5.1f}% "
          f"| LR: {lr_actuel:.6f}")

    # ── Meilleur modèle → sauvegarder ──
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        no_improve    = 0
        torch.save(model.state_dict(), SAVE_PATH)
        print(f"           ✅ Meilleur modèle sauvegardé ! (val_loss={best_val_loss:.4f})")
    else:
        no_improve += 1
        # Afficher un avertissement si ça stagne
        if no_improve >= 5:
            print(f"           ⚠️  Pas d'amélioration depuis {no_improve} epochs...")

    # ── Early Stopping ──
    if no_improve >= PATIENCE:
        print(f"\n⛔ Early Stopping déclenché à l'epoch {epoch}")
        print(f"   Meilleure val_loss obtenue : {best_val_loss:.4f}")
        break

# ── Fin de l'entraînement ──
print()
print("=" * 50)
print("✅ ENTRAÎNEMENT TERMINÉ !")
print("=" * 50)
print(f"Meilleure Val Loss  : {best_val_loss:.4f}")
print(f"Meilleure Val Acc   : {max(history['val_acc'])*100:.1f}%")
print(f"Modèle sauvegardé   : {SAVE_PATH}")
print()
print("✅ Prêt pour l'Étape 6 — Affichage des courbes Loss / Accuracy !")


# ==============================================================
# ÉTAPE 6 — COURBES LOSS ET ACCURACY
#
# On trace 4 courbes sur 2 graphiques côte à côte :
#   Graphique gauche  → Loss    (train en bleu, val en orange)
#   Graphique droite  → Accuracy (train en bleu, val en orange)
#
# Ce qu'on veut voir :
#   - Loss      : descendre vers 0
#   - Accuracy  : monter vers 100%
#   - Les 2 courbes (train/val) proches = pas d'overfitting
#
# Signes d'overfitting à surveiller :
#   - Train Loss continue de descendre MAIS Val Loss remonte
#   - Train Acc monte MAIS Val Acc stagne ou descend
# ==============================================================

import matplotlib
matplotlib.use('Agg')          # pas besoin d'écran pour sauvegarder en fichier
import matplotlib.pyplot as plt

def plot_training_curves(history, save_path="courbes_entrainement.png"):
    """
    Trace et sauvegarde les courbes Loss et Accuracy.

    Paramètre history : dictionnaire avec les clés
        'train_loss', 'val_loss', 'train_acc', 'val_acc'
    """
    epochs_range = range(1, len(history['train_loss']) + 1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Courbes d'Entraînement — Classification Glaucome", fontsize=14, fontweight='bold')

    # ── Graphique 1 : Loss ──
    ax1.plot(epochs_range, history['train_loss'], 'b-o', markersize=3, label='Train Loss')
    ax1.plot(epochs_range, history['val_loss'],   'r-o', markersize=3, label='Val Loss')
    ax1.set_title('Loss (Fonction de Coût)', fontsize=12)
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    # Ligne horizontale à 0 pour visualiser l'objectif
    ax1.axhline(y=0, color='green', linestyle='--', alpha=0.5, label='Objectif → 0')

    # Annoter la meilleure val_loss
    best_epoch = history['val_loss'].index(min(history['val_loss'])) + 1
    best_loss  = min(history['val_loss'])
    ax1.annotate(f'Meilleur: {best_loss:.4f}',
                 xy=(best_epoch, best_loss),
                 xytext=(best_epoch + 1, best_loss + 0.05),
                 arrowprops=dict(arrowstyle='->', color='red'),
                 color='red', fontsize=9)

    # ── Graphique 2 : Accuracy ──
    train_acc_pct = [a * 100 for a in history['train_acc']]
    val_acc_pct   = [a * 100 for a in history['val_acc']]

    ax2.plot(epochs_range, train_acc_pct, 'b-o', markersize=3, label='Train Accuracy')
    ax2.plot(epochs_range, val_acc_pct,   'r-o', markersize=3, label='Val Accuracy')
    ax2.set_title('Accuracy (Précision)', fontsize=12)
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_ylim([0, 105])
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    # Ligne horizontale à 100% pour visualiser l'objectif
    ax2.axhline(y=100, color='green', linestyle='--', alpha=0.5, label='Objectif → 100%')

    # Annoter la meilleure val_accuracy
    best_acc_epoch = val_acc_pct.index(max(val_acc_pct)) + 1
    best_acc       = max(val_acc_pct)
    ax2.annotate(f'Meilleur: {best_acc:.1f}%',
                 xy=(best_acc_epoch, best_acc),
                 xytext=(best_acc_epoch + 1, best_acc - 10),
                 arrowprops=dict(arrowstyle='->', color='red'),
                 color='red', fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Courbes sauvegardées → {save_path}")


# ── Tracer les courbes ──
print()
print("=" * 50)
print("ÉTAPE 6 — Courbes Loss / Accuracy")
print("=" * 50)
plot_training_curves(history, save_path="courbes_entrainement.png")
print(f"   Train Loss finale  : {history['train_loss'][-1]:.4f}")
print(f"   Val   Loss finale  : {history['val_loss'][-1]:.4f}")
print(f"   Train Acc  finale  : {history['train_acc'][-1]*100:.1f}%")
print(f"   Val   Acc  finale  : {history['val_acc'][-1]*100:.1f}%")
print()


# ==============================================================
# ÉTAPE 7 — ÉVALUATION FINALE SUR LE JEU DE TEST
#
# Après l'entraînement on recharge le MEILLEUR modèle sauvegardé
# (pas forcément celui de la dernière epoch — celui avec la
#  meilleure val_loss pendant tout l'entraînement)
#
# On calcule les métriques détaillées :
#   - Accuracy globale
#   - Precision : parmi les prédits Glaucome, combien sont vrais ?
#   - Recall    : parmi les vrais Glaucome, combien détectés ?
#   - F1-Score  : équilibre entre Precision et Recall
#   - AUC-ROC   : capacité à distinguer les 2 classes (1.0 = parfait)
#
# Pourquoi ces métriques en plus de l'Accuracy ?
#   Ex: 90% Normal, 10% Glaucome dans le dataset
#   Un modèle qui dit TOUJOURS "Normal" a 90% d'Accuracy
#   mais ne détecte AUCUN glaucome → inutile médicalement !
#   → Recall du Glaucome doit être très élevé (ne pas rater de cas)
# ==============================================================

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve
)
import numpy as np

def evaluate_final(model, loader, device, class_names=['Normal', 'Glaucome']):
    """
    Évaluation complète sur un jeu de données (test ou val).
    Retourne toutes les métriques et les probabilités prédites.
    """
    model.eval()

    all_preds  = []   # prédictions finales (0 ou 1)
    all_labels = []   # vrais labels
    all_probs  = []   # probabilité d'être Glaucome (classe 1)

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)

            outputs = model(images)                          # logits [batch, 2]
            probs   = torch.softmax(outputs, dim=1)          # probabilités [batch, 2]
            preds   = outputs.argmax(dim=1)                  # classe prédite

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs[:, 1].cpu().numpy())      # prob classe Glaucome

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs  = np.array(all_probs)

    # ── Rapport complet ──
    print("\n📊 RAPPORT DE CLASSIFICATION DÉTAILLÉ :")
    print("-" * 50)
    print(classification_report(all_labels, all_preds, target_names=class_names))

    # ── AUC-ROC ──
    # Nécessite au moins les 2 classes présentes dans les labels
    try:
        auc = roc_auc_score(all_labels, all_probs)
        print(f"AUC-ROC  : {auc:.4f}  (1.0 = parfait, 0.5 = aléatoire)")
    except ValueError:
        print("AUC-ROC  : non calculable (une seule classe dans ce batch)")
        auc = None

    # ── Matrice de confusion ──
    cm = confusion_matrix(all_labels, all_preds)
    print(f"\nMatrice de confusion :")
    print(f"              Prédit Normal  Prédit Glaucome")
    print(f"Vrai Normal       {cm[0][0]:5d}           {cm[0][1]:5d}")
    print(f"Vrai Glaucome     {cm[1][0]:5d}           {cm[1][1]:5d}")
    print()
    print(f"  Vrais Négatifs  (TN) = {cm[0][0]}  → Normaux bien détectés")
    print(f"  Faux Positifs   (FP) = {cm[0][1]}  → Normaux classés Glaucome")
    print(f"  Faux Négatifs   (FN) = {cm[1][0]}  → Glaucomes RATÉS ⚠️")
    print(f"  Vrais Positifs  (TP) = {cm[1][1]}  → Glaucomes bien détectés")

    return all_preds, all_labels, all_probs, auc


def plot_confusion_matrix(all_labels, all_preds,
                          class_names=['Normal', 'Glaucome'],
                          save_path="matrice_confusion.png"):
    """Sauvegarde la matrice de confusion en image."""
    cm = confusion_matrix(all_labels, all_preds)

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.colorbar(im)

    ax.set(xticks=[0, 1], yticks=[0, 1],
           xticklabels=class_names, yticklabels=class_names,
           xlabel='Classe Prédite', ylabel='Vraie Classe',
           title='Matrice de Confusion')

    # Annoter chaque cellule avec son nombre
    thresh = cm.max() / 2.0
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]),
                    ha='center', va='center',
                    color='white' if cm[i, j] > thresh else 'black',
                    fontsize=16, fontweight='bold')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Matrice de confusion sauvegardée → {save_path}")


# ── Recharger le meilleur modèle et évaluer ──
print("=" * 50)
print("ÉTAPE 7 — Évaluation finale")
print("=" * 50)

# Recharger les poids du meilleur modèle sauvegardé
model.load_state_dict(torch.load(SAVE_PATH, map_location=device))
print(f"✅ Meilleur modèle rechargé depuis : {SAVE_PATH}")

# Évaluer sur le jeu de validation (remplacer par test_loader quand disponible)
all_preds, all_labels, all_probs, auc = evaluate_final(model, val_loader, device)

# Sauvegarder la matrice de confusion
plot_confusion_matrix(all_labels, all_preds, save_path="matrice_confusion.png")
print()


# ==============================================================
# ÉTAPE 8 — COURBE ROC
#
# La courbe ROC montre le compromis entre :
#   - Taux de Vrais Positifs (TPR = Recall) : Glaucomes bien détectés
#   - Taux de Faux Positifs (FPR)           : Normaux classés à tort Glaucome
#
# AUC (Area Under Curve) :
#   - 1.0 → modèle parfait
#   - 0.5 → modèle aléatoire (inutile)
#   - objectif médical : AUC > 0.95
#
# Utile pour choisir le seuil de décision optimal :
#   Par défaut on prédit Glaucome si prob > 0.5
#   Mais en médecine on peut abaisser à 0.3 pour ne rater
#   aucun cas (meilleur Recall, plus de faux positifs)
# ==============================================================

def plot_roc_curve(all_labels, all_probs, auc,
                   save_path="courbe_roc.png"):
    """Trace et sauvegarde la courbe ROC."""
    try:
        fpr, tpr, thresholds = roc_curve(all_labels, all_probs)

        fig, ax = plt.subplots(figsize=(7, 6))

        # Courbe ROC du modèle
        ax.plot(fpr, tpr, 'b-', linewidth=2,
                label=f'Modèle (AUC = {auc:.4f})')

        # Ligne diagonale = modèle aléatoire (référence)
        ax.plot([0, 1], [0, 1], 'r--', linewidth=1,
                label='Aléatoire (AUC = 0.50)')

        # Point optimal (meilleur seuil)
        optimal_idx = np.argmax(tpr - fpr)
        optimal_thr = thresholds[optimal_idx]
        ax.scatter(fpr[optimal_idx], tpr[optimal_idx],
                   color='green', s=100, zorder=5,
                   label=f'Seuil optimal = {optimal_thr:.2f}')

        ax.set(xlabel='Taux Faux Positifs (FPR)',
               ylabel='Taux Vrais Positifs (TPR / Recall)',
               title='Courbe ROC — Classification Glaucome',
               xlim=[0, 1], ylim=[0, 1.02])
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✅ Courbe ROC sauvegardée → {save_path}")
        print(f"   Seuil optimal détecté : {optimal_thr:.2f}")
        print(f"     → Au-dessus de ce seuil = Glaucome prédit")

    except Exception as e:
        print(f"⚠️  Courbe ROC non tracée : {e}")


print("=" * 50)
print("ÉTAPE 8 — Courbe ROC")
print("=" * 50)
if auc is not None:
    plot_roc_curve(all_labels, all_probs, auc, save_path="courbe_roc.png")
else:
    print("⚠️  AUC non disponible — courbe ROC ignorée")
print()


# ==============================================================
# ÉTAPE 9 — RÉSUMÉ FINAL ET FICHIERS PRODUITS
#
# Récapitulatif de tout ce qui a été généré :
#   1. best_glaucoma_model.pth  → modèle prêt à charger dans app.py
#   2. courbes_entrainement.png → Loss et Accuracy par epoch
#   3. matrice_confusion.png    → analyse des erreurs du modèle
#   4. courbe_roc.png           → performance de discrimination
#
# Étape suivante :
#   → Remplacer FakeRetinalDataset par GlaucomaDataset (vraies images)
#   → Relancer ce script complet
#   → Le modèle .pth sera automatiquement chargé par app.py
# ==============================================================

print()
print("=" * 60)
print("  ✅  PIPELINE COMPLET — RÉSUMÉ FINAL")
print("=" * 60)
print()
print("📁 FICHIERS GÉNÉRÉS :")
print(f"   🧠 {SAVE_PATH}")
print(f"      → Modèle entraîné, prêt pour app.py")
print(f"   📈 courbes_entrainement.png")
print(f"      → Courbes Loss et Accuracy par epoch")
print(f"   🔲 matrice_confusion.png")
print(f"      → Analyse des erreurs (TP, FP, TN, FN)")
print(f"   📉 courbe_roc.png")
print(f"      → Courbe ROC avec AUC et seuil optimal")
print()
print("📊 RÉSULTATS :")
print(f"   Meilleure Val Loss     : {best_val_loss:.4f}   (objectif → 0)")
print(f"   Meilleure Val Accuracy : {max(history['val_acc'])*100:.1f}%  (objectif → 100%)")
if auc is not None:
    print(f"   AUC-ROC                : {auc:.4f}   (objectif → 1.0)")
print()
print("🔜 PROCHAINE ÉTAPE :")
print("   Remplacer FakeRetinalDataset par de vraies images rétiniennes")
print("   → dataset REFUGE, DRISHTI ou vos propres images annotées")
print("   → Relancer ce script → le .pth sera utilisé par app.py")
print()
print("=" * 60)