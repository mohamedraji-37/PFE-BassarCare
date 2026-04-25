import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
import os
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import numpy as np

# Configuration
DATA_DIR = r"C:\Users\Electro Ragragui\Desktop\data"
MODEL_PATH = "efficientnet_b4.pth"  # Chemin vers votre modèle pré-entraîné
BATCH_SIZE = 8  # Réduit pour CPU
LEARNING_RATE = 0.0001
NUM_EPOCHS = 30  # Réduit pour CPU
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
NUM_CLASSES = 2

print(f"Utilisation du device: {DEVICE}")

# Transforms pour l'augmentation des données
train_transforms = transforms.Compose([
    transforms.Resize((380, 380)),  # EfficientNet-B4 input size
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomVerticalFlip(p=0.3),
    transforms.RandomRotation(degrees=15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

val_transforms = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Chargement des datasets
train_dataset = datasets.ImageFolder(
    root=os.path.join(DATA_DIR, 'train'),
    transform=train_transforms
)

val_dataset = datasets.ImageFolder(
    root=os.path.join(DATA_DIR, 'validation'),
    transform=val_transforms
)

# DataLoaders (optimisé pour CPU)
train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,  # 0 pour CPU
    pin_memory=False  # False pour CPU
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,  # 0 pour CPU
    pin_memory=False  # False pour CPU
)

print(f"Classes: {train_dataset.classes}")
print(f"Nombre d'images d'entraînement: {len(train_dataset)}")
print(f"Nombre d'images de validation: {len(val_dataset)}")

# Fonction pour charger le modèle EfficientNet-B4
def load_efficientnet_b4():
    # Charger EfficientNet-B4 pré-entraîné (syntaxe mise à jour)
    model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.IMAGENET1K_V1)
    
    # Modifier la dernière couche pour 2 classes (glaucome/normal)
    num_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(0.4),
        nn.Linear(num_features, NUM_CLASSES)
    )
    
    return model

# Charger le modèle
model = load_efficientnet_b4()

# Si vous avez un modèle pré-entraîné spécifique, décommentez les lignes suivantes:
# if os.path.exists(MODEL_PATH):
#     model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
#     print(f"Modèle chargé depuis {MODEL_PATH}")

model = model.to(DEVICE)

# Critère de perte et optimiseur
criterion = nn.CrossEntropyLoss()
optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)

# Scheduler pour ajuster le learning rate
scheduler = optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, mode='min', factor=0.5, patience=5
)

# Early stopping
class EarlyStopping:
    def __init__(self, patience=10, min_delta=0):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = float('inf')
        
    def __call__(self, val_loss):
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
            return False
        else:
            self.counter += 1
            return self.counter >= self.patience

early_stopping = EarlyStopping(patience=10)

# Fonction d'entraînement
def train_epoch(model, train_loader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    progress_bar = tqdm(train_loader, desc="Training")
    
    for batch_idx, (data, target) in enumerate(progress_bar):
        data, target = data.to(device), target.to(device)
        
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item()
        _, predicted = torch.max(output.data, 1)
        total += target.size(0)
        correct += (predicted == target).sum().item()
        
        # Mise à jour de la barre de progression
        progress_bar.set_postfix({
            'Loss': f'{loss.item():.4f}',
            'Acc': f'{100.*correct/total:.2f}%'
        })
    
    epoch_loss = running_loss / len(train_loader)
    epoch_acc = 100. * correct / total
    
    return epoch_loss, epoch_acc

# Fonction de validation
def validate_epoch(model, val_loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        progress_bar = tqdm(val_loader, desc="Validation")
        
        for data, target in progress_bar:
            data, target = data.to(device), target.to(device)
            output = model(data)
            loss = criterion(output, target)
            
            running_loss += loss.item()
            _, predicted = torch.max(output.data, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()
            
            all_preds.extend(predicted.cpu().numpy())
            all_targets.extend(target.cpu().numpy())
            
            progress_bar.set_postfix({
                'Loss': f'{loss.item():.4f}',
                'Acc': f'{100.*correct/total:.2f}%'
            })
    
    epoch_loss = running_loss / len(val_loader)
    epoch_acc = 100. * correct / total
    
    # Calcul des métriques détaillées
    precision = precision_score(all_targets, all_preds, average='weighted')
    recall = recall_score(all_targets, all_preds, average='weighted')
    f1 = f1_score(all_targets, all_preds, average='weighted')
    
    return epoch_loss, epoch_acc, precision, recall, f1, all_preds, all_targets

# Boucle d'entraînement principale
train_losses = []
val_losses = []
train_accs = []
val_accs = []
best_val_acc = 0.0

print("Début de l'entraînement...")

for epoch in range(NUM_EPOCHS):
    print(f'\nEpoch {epoch+1}/{NUM_EPOCHS}')
    print('-' * 60)
    
    # Entraînement
    train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, DEVICE)
    
    # Validation
    val_loss, val_acc, precision, recall, f1, val_preds, val_targets = validate_epoch(
        model, val_loader, criterion, DEVICE
    )
    
    # Enregistrement des métriques
    train_losses.append(train_loss)
    val_losses.append(val_loss)
    train_accs.append(train_acc)
    val_accs.append(val_acc)
    
    # Ajustement du learning rate
    scheduler.step(val_loss)
    
    print(f'Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%')
    print(f'Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')
    print(f'Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}')
    
    # Sauvegarde du meilleur modèle
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), 'best_glaucoma_model.pth')
        print(f'Nouveau meilleur modèle sauvegardé avec une précision de {val_acc:.2f}%')
    
    # Early stopping
    if early_stopping(val_loss):
        print(f'Early stopping à l\'epoch {epoch+1}')
        break

print(f'\nEntraînement terminé. Meilleure précision de validation: {best_val_acc:.2f}%')

# Chargement du meilleur modèle pour l'évaluation finale
model.load_state_dict(torch.load('best_glaucoma_model.pth'))

# Évaluation finale
print('\nÉvaluation finale...')
final_val_loss, final_val_acc, final_precision, final_recall, final_f1, final_preds, final_targets = validate_epoch(
    model, val_loader, criterion, DEVICE
)

print(f'Précision finale: {final_val_acc:.2f}%')
print(f'Précision (Precision): {final_precision:.4f}')
print(f'Rappel (Recall): {final_recall:.4f}')
print(f'F1-Score: {final_f1:.4f}')

# Matrice de confusion
cm = confusion_matrix(final_targets, final_preds)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=train_dataset.classes, 
            yticklabels=train_dataset.classes)
plt.title('Matrice de Confusion')
plt.ylabel('Vraie classe')
plt.xlabel('Classe prédite')
plt.tight_layout()
plt.savefig('confusion_matrix.png')
plt.show()

# Graphiques des métriques d'entraînement
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

# Graphique des pertes
ax1.plot(train_losses, label='Train Loss')
ax1.plot(val_losses, label='Validation Loss')
ax1.set_title('Évolution des pertes')
ax1.set_xlabel('Epoch')
ax1.set_ylabel('Loss')
ax1.legend()
ax1.grid(True)

# Graphique des précisions
ax2.plot(train_accs, label='Train Accuracy')
ax2.plot(val_accs, label='Validation Accuracy')
ax2.set_title('Évolution de la précision')
ax2.set_xlabel('Epoch')
ax2.set_ylabel('Accuracy (%)')
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.savefig('training_metrics.png')
plt.show()

print("\nEntraînement terminé avec succès!")
print(f"Modèle sauvegardé sous: best_glaucoma_model.pth")
print(f"Graphiques sauvegardés: confusion_matrix.png, training_metrics.png")