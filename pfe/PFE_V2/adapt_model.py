# adapt_model.py
import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import datasets, transforms
import zipfile
import shutil
import uuid
from model import build_unet

MODELS_DIR = os.path.join('static', 'models')
UPLOAD_TMP = os.path.join('tmp', 'adapt')

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def _is_image_file(p: str) -> bool:
    return str(p).lower().endswith(tuple(IMG_EXTS))


def _list_files_with_stem(images_dir: str, masks_dir: str):
    """
    Associe image <-> mask par 'stem' (nom sans extension).
    """
    import pathlib

    images_path = pathlib.Path(images_dir)
    masks_path = pathlib.Path(masks_dir)

    if not images_path.is_dir():
        raise ValueError(f"Images dir introuvable: {images_dir}")
    if not masks_path.is_dir():
        raise ValueError(f"Masks dir introuvable: {masks_dir}")

    masks_index = {}
    for m in masks_path.rglob("*"):
        if m.is_file() and _is_image_file(m.name):
            masks_index[m.stem] = str(m)

    pairs = []
    for img in images_path.rglob("*"):
        if not img.is_file() or not _is_image_file(img.name):
            continue
        ms = masks_index.get(img.stem)
        if ms is not None:
            pairs.append((str(img), ms))

    if not pairs:
        raise ValueError(
            "Aucune paire image/mask trouvée. Vérifie le pairing par stem "
            "(ex: image_12.jpg <-> image_12.png) dans train/images et train/masks."
        )
    return pairs


class SegmentationPairsDataset(Dataset):
    def __init__(self, images_dir: str, masks_dir: str, img_size: int = 512, augment: bool = False):
        self.pairs = _list_files_with_stem(images_dir, masks_dir)
        self.img_size = int(img_size)
        self.augment = bool(augment)

    def __len__(self):
        return len(self.pairs)

    def _maybe_augment(self, img: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        # Augmentations simples et appliquées aussi au masque.
        # Note: on évite les augmentations photométriques pour garder la sémantique du masque binaire.
        if np.random.rand() < 0.5:
            img = cv2.flip(img, 1)
            mask = cv2.flip(mask, 1)
        if np.random.rand() < 0.5:
            img = cv2.flip(img, 0)
            mask = cv2.flip(mask, 0)

        # Petite rotation pour robustesse; masque via INTER_NEAREST.
        if np.random.rand() < 0.5:
            angle = float(np.random.uniform(-15, 15))
            h, w = mask.shape[:2]
            M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
            mask = cv2.warpAffine(mask, M, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

        return img, mask

    def __getitem__(self, idx: int):
        img_path, mask_path = self.pairs[idx]

        img = cv2.imread(img_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not read image: {img_path}")

        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise ValueError(f"Could not read mask: {mask_path}")

        img = cv2.resize(img, (self.img_size, self.img_size), interpolation=cv2.INTER_LINEAR)
        mask = cv2.resize(mask, (self.img_size, self.img_size), interpolation=cv2.INTER_NEAREST)

        if self.augment:
            img, mask = self._maybe_augment(img, mask)

        # Binarisation (le code d'inférence traite 'foreground' via > 127)
        mask = (mask > 127).astype(np.float32)

        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC -> CHW

        mask = np.expand_dims(mask, axis=0)  # 1xHxW

        return torch.from_numpy(img), torch.from_numpy(mask)


def _compute_dice_iou(pred_bin: torch.Tensor, target_bin: torch.Tensor, eps: float = 1e-7) -> tuple[float, float]:
    """
    pred_bin/target_bin: shape [B, 1, H, W] with values in {0,1}.
    Retourne (dice, iou) en degrés/100? Non: valeur 0..1.
    """
    # Intersection & unions par sample
    dims = (1, 2, 3)
    intersection = torch.sum(pred_bin * target_bin, dim=dims)
    pred_sum = torch.sum(pred_bin, dim=dims)
    target_sum = torch.sum(target_bin, dim=dims)

    dice = (2.0 * intersection + eps) / (pred_sum + target_sum + eps)
    union = pred_sum + target_sum - intersection
    iou = (intersection + eps) / (union + eps)

    return float(dice.mean().item()), float(iou.mean().item())


def run_adaptation(zip_path, task, model_name, base_model_id,
                   epochs, lr, batch_size, db=None, Model=None,
                   base_model_file=None, job_id=None, jobs=None):
    """
    Entraînement FROM SCRATCH (pas fine-tuning).
    Retourne (success: bool, message: str, model_path: str, history: dict)
    """

    def update_progress(pct, msg=''):
        if jobs is not None and job_id is not None:
            jobs[job_id]['progress'] = pct
            jobs[job_id]['message']  = msg

    def is_cancel_requested() -> bool:
        if jobs is None or job_id is None:
            return False
        return bool(jobs.get(job_id, {}).get('cancel_requested'))

    def stop_if_cancelled(stage=''):
        if not is_cancel_requested():
            return False
        msg = "Adaptation arretee par l'utilisateur."
        if stage:
            msg = f"{msg} ({stage})"
        update_progress(100, msg)
        if jobs is not None and job_id is not None and job_id in jobs:
            jobs[job_id]['canceled'] = True
        print(f"[adapt_model] job={job_id} cancelled {stage}".strip(), flush=True)
        return True

    work_dir = os.path.join(UPLOAD_TMP, job_id or str(uuid.uuid4())[:8])
    os.makedirs(work_dir, exist_ok=True)

    history = {
        'train_loss': [],
        'train_acc':  [],
        'val_loss':   [],
        'val_acc':    [],
        # Pour segmentation on ajoute aussi dice/iou (les charts front n'affichent pas encore ces champs,
        # mais on les sauvegarde dans l'historique pour les métriques/logs).
        'train_dice': [],
        'train_iou':  [],
        'val_dice':   [],
        'val_iou':    [],
    }

    try:
        # ── 1. Extraire le ZIP ───────────────────────────────
        update_progress(5, 'Extraction du dataset...')
        if stop_if_cancelled('avant extraction'):
            return False, "Adaptation arretee par l'utilisateur.", '', history
        extract_dir = os.path.join(work_dir, 'data')

        # zip_path peut être un chemin fichier (str) ou un objet FileStorage
        if isinstance(zip_path, str):
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)
        else:
            # FileStorage Flask
            saved_zip = os.path.join(work_dir, 'dataset.zip')
            zip_path.save(saved_zip)
            with zipfile.ZipFile(saved_zip, 'r') as z:
                z.extractall(extract_dir)

        # ── 2. Trouver train/ et test/ ───────────────────────
        update_progress(10, 'Analyse de la structure...')
        if stop_if_cancelled('analyse dataset'):
            return False, "Adaptation arretee par l'utilisateur.", '', history
        train_dir, test_dir = _find_splits(extract_dir)

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # ── 3. Dataset / Loaders ──────────────────────────────
        update_progress(15, 'Chargement du dataset...')
        if stop_if_cancelled('chargement dataset'):
            return False, "Adaptation arretee par l'utilisateur.", '', history
        if task == 'segmentation':
            img_size = 512

            train_images_dir = os.path.join(train_dir, 'images')
            train_masks_dir  = os.path.join(train_dir, 'masks')
            test_images_dir  = os.path.join(test_dir, 'images')
            test_masks_dir   = os.path.join(test_dir, 'masks')

            train_ds = SegmentationPairsDataset(
                train_images_dir, train_masks_dir, img_size=img_size, augment=True
            )
            test_ds = SegmentationPairsDataset(
                test_images_dir, test_masks_dir, img_size=img_size, augment=False
            )

            train_loader = DataLoader(train_ds, batch_size=int(batch_size), shuffle=True, num_workers=0)
            test_loader = DataLoader(test_ds, batch_size=int(batch_size), shuffle=False, num_workers=0)

            num_classes = 1  # binaire: un seul canal masque
        else:
            IMG_SIZE = 224
            train_tf = transforms.Compose([
                transforms.Resize((IMG_SIZE, IMG_SIZE)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
                transforms.RandomRotation(15),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406],
                                     [0.229, 0.224, 0.225]),
            ])
            test_tf = transforms.Compose([
                transforms.Resize((IMG_SIZE, IMG_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406],
                                     [0.229, 0.224, 0.225]),
            ])

            train_ds = datasets.ImageFolder(train_dir, transform=train_tf)
            test_ds = datasets.ImageFolder(test_dir, transform=test_tf)

            train_loader = DataLoader(train_ds, batch_size=int(batch_size), shuffle=True, num_workers=0)
            test_loader = DataLoader(test_ds, batch_size=int(batch_size), shuffle=False, num_workers=0)

            num_classes = len(train_ds.classes)

        # ── 4. Modèle FROM SCRATCH ───────────────────────────
        update_progress(20, 'Construction du modele...')
        if stop_if_cancelled('construction modele'):
            return False, "Adaptation arretee par l'utilisateur.", '', history
        model = _build_model_from_scratch(num_classes, task).to(device)
        _load_base_weights_if_provided(model, base_model_file, work_dir, device)

        # ── 5. Optimizer + Loss ──────────────────────────────
        if task == 'segmentation':
            criterion = nn.BCEWithLogitsLoss()
        else:
            criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=float(lr))
        scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

        # ── 6. Boucle d'entraînement ─────────────────────────
        best_acc   = 0.0
        best_state = None
        nb_epochs  = int(epochs)

        for epoch in range(nb_epochs):
            if stop_if_cancelled(f'avant epoch {epoch + 1}/{nb_epochs}'):
                return False, "Adaptation arretee par l'utilisateur.", '', history
            if task == 'segmentation':
                # ── TRAIN ──
                model.train()
                train_loss = 0.0
                train_dice = 0.0
                train_iou = 0.0
                n_train = 0

                for images, masks in train_loader:
                    if stop_if_cancelled(f'entrainement epoch {epoch + 1}/{nb_epochs}'):
                        return False, "Adaptation arretee par l'utilisateur.", '', history
                    images = images.to(device)
                    masks = masks.to(device)

                    optimizer.zero_grad()
                    logits = model(images)  # [B,1,H,W]
                    loss = criterion(logits, masks)
                    loss.backward()
                    optimizer.step()

                    bs = images.size(0)
                    train_loss += loss.item() * bs

                    probs = torch.sigmoid(logits)
                    pred_bin = (probs > 0.5).float()
                    dice, iou = _compute_dice_iou(pred_bin, masks)
                    train_dice += dice * bs
                    train_iou += iou * bs
                    n_train += bs

                scheduler.step()

                epoch_train_loss = train_loss / n_train if n_train > 0 else 0.0
                epoch_train_dice = train_dice / n_train if n_train > 0 else 0.0
                epoch_train_iou = train_iou / n_train if n_train > 0 else 0.0

                # ── VALIDATION ──
                model.eval()
                val_loss = 0.0
                val_dice = 0.0
                val_iou = 0.0
                n_val = 0

                with torch.no_grad():
                    for images, masks in test_loader:
                        if stop_if_cancelled(f'validation epoch {epoch + 1}/{nb_epochs}'):
                            return False, "Adaptation arretee par l'utilisateur.", '', history
                        images = images.to(device)
                        masks = masks.to(device)

                        logits = model(images)
                        loss = criterion(logits, masks)

                        bs = images.size(0)
                        val_loss += loss.item() * bs

                        probs = torch.sigmoid(logits)
                        pred_bin = (probs > 0.5).float()
                        dice, iou = _compute_dice_iou(pred_bin, masks)
                        val_dice += dice * bs
                        val_iou += iou * bs
                        n_val += bs

                epoch_val_loss = val_loss / n_val if n_val > 0 else 0.0
                epoch_val_dice = val_dice / n_val if n_val > 0 else 0.0
                epoch_val_iou = val_iou / n_val if n_val > 0 else 0.0

                # Front s'attend à train_acc/val_acc: on met Dice en %
                epoch_train_acc = epoch_train_dice * 100.0
                epoch_val_acc = epoch_val_dice * 100.0

                history['train_loss'].append(round(epoch_train_loss, 4))
                history['train_acc'].append(round(epoch_train_acc, 2))
                history['val_loss'].append(round(epoch_val_loss, 4))
                history['val_acc'].append(round(epoch_val_acc, 2))
                history['train_dice'].append(round(epoch_train_dice, 4))
                history['train_iou'].append(round(epoch_train_iou, 4))
                history['val_dice'].append(round(epoch_val_dice, 4))
                history['val_iou'].append(round(epoch_val_iou, 4))

                print(
                    f"[adapt_model][epoch {epoch + 1}/{nb_epochs}] "
                    f"train_loss={epoch_train_loss:.4f} dice={epoch_train_dice*100:.2f}% iou={epoch_train_iou*100:.2f}% "
                    f"val_loss={epoch_val_loss:.4f} dice={epoch_val_dice*100:.2f}% iou={epoch_val_iou*100:.2f}%",
                    flush=True
                )

                if epoch_val_acc > best_acc:
                    best_acc = epoch_val_acc
                    best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

                pct = 25 + int((epoch + 1) / nb_epochs * 65)
                update_progress(
                    pct,
                    f'Epoque {epoch + 1}/{nb_epochs} — '
                    f'loss: {epoch_train_loss:.4f} — '
                    f'val_dice: {epoch_val_acc:.1f}%%'
                )
            else:
                # ── TRAIN ──
                model.train()
                train_loss = 0.0
                train_correct = 0
                train_total = 0

                for images, labels in train_loader:
                    if stop_if_cancelled(f'entrainement epoch {epoch + 1}/{nb_epochs}'):
                        return False, "Adaptation arretee par l'utilisateur.", '', history
                    images, labels = images.to(device), labels.to(device)
                    optimizer.zero_grad()
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()

                    train_loss += loss.item() * images.size(0)
                    preds = outputs.argmax(dim=1)
                    train_correct += (preds == labels).sum().item()
                    train_total += labels.size(0)

                scheduler.step()

                epoch_train_loss = train_loss / train_total if train_total > 0 else 0.0
                epoch_train_acc = 100.0 * train_correct / train_total if train_total > 0 else 0.0

                # ── VALIDATION ──
                model.eval()
                val_loss = 0.0
                val_correct = 0
                val_total = 0

                with torch.no_grad():
                    for images, labels in test_loader:
                        if stop_if_cancelled(f'validation epoch {epoch + 1}/{nb_epochs}'):
                            return False, "Adaptation arretee par l'utilisateur.", '', history
                        images, labels = images.to(device), labels.to(device)
                        outputs = model(images)
                        loss = criterion(outputs, labels)

                        val_loss += loss.item() * images.size(0)
                        preds = outputs.argmax(dim=1)
                        val_correct += (preds == labels).sum().item()
                        val_total += labels.size(0)

                epoch_val_loss = val_loss / val_total if val_total > 0 else 0.0
                epoch_val_acc = 100.0 * val_correct / val_total if val_total > 0 else 0.0

                history['train_loss'].append(round(epoch_train_loss, 4))
                history['train_acc'].append(round(epoch_train_acc, 2))
                history['val_loss'].append(round(epoch_val_loss, 4))
                history['val_acc'].append(round(epoch_val_acc, 2))

                print(
                    f"[adapt_model][epoch {epoch + 1}/{nb_epochs}] "
                    f"train_loss={epoch_train_loss:.4f} train_acc={epoch_train_acc:.2f}% "
                    f"val_loss={epoch_val_loss:.4f} val_acc={epoch_val_acc:.2f}%",
                    flush=True
                )

                if epoch_val_acc > best_acc:
                    best_acc = epoch_val_acc
                    best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

                pct = 25 + int((epoch + 1) / nb_epochs * 65)
                update_progress(
                    pct,
                    f'Epoque {epoch + 1}/{nb_epochs} — '
                    f'loss: {epoch_train_loss:.4f} — '
                    f'val_acc: {epoch_val_acc:.1f}%%'
                )

        # ── 7. Sauvegarder le meilleur modèle ────────────────
        if stop_if_cancelled('avant sauvegarde'):
            return False, "Adaptation arretee par l'utilisateur.", '', history
        update_progress(95, 'Sauvegarde du modele...')
        os.makedirs(MODELS_DIR, exist_ok=True)
        safe_name  = model_name.replace(' ', '_')
        model_path = os.path.join(MODELS_DIR, f'{safe_name}.pth')

        torch.save({
            'state_dict':  best_state,
            'num_classes': num_classes,
            'classes':     getattr(train_ds, "classes", ['background', 'glaucoma']),
            'task':        task,
            'accuracy':    best_acc,
            'model_name':  model_name,
            'history':     history,     # ← courbes Loss & Accuracy
        }, model_path)

        # ── 8. Enregistrer en base ────────────────────────────
        if db is not None and Model is not None and hasattr(db, 'session'):
            new_model = Model(
                model_name=model_name,
                model_type=task,
                file_path=model_path,
            )
            db.session.add(new_model)
            db.session.commit()

        update_progress(100, f'Termine ! Precision: {best_acc:.1f}%%')
        if task == 'segmentation':
            return True, f'Dice validation : {best_acc:.1f}%', model_path, history
        return True, f'Précision test : {best_acc:.1f}%', model_path, history

    except Exception as e:
        return False, str(e), '', history

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════

def _build_model_from_scratch(num_classes, task):
    """CNN simple entraîné FROM SCRATCH (pas de poids pré-entraînés)."""
    if task == 'segmentation':
        # Architecture utilisée côté inference dans `app.py` (build_unet dans `model.py`)
        # Elle sort directement un masque binaire (1 canal).
        return build_unet()
    else:
        return _SimpleCNN(num_classes=num_classes)


def _load_base_weights_if_provided(model, base_model_file, work_dir, device):
    """Charge des poids initiaux si un fichier de modèle est fourni."""
    if base_model_file is None:
        return

    if isinstance(base_model_file, str):
        filename = os.path.basename(base_model_file).lower()
    else:
        filename = (base_model_file.filename or '').lower()

    if not filename.endswith(('.pth', '.pt')):
        raise ValueError("Le modèle de base doit être un fichier .pth ou .pt")

    if isinstance(base_model_file, str):
        base_model_path = base_model_file
    else:
        base_model_path = os.path.join(work_dir, 'base_model.pth')
        base_model_file.save(base_model_path)

    checkpoint = torch.load(base_model_path, map_location=device)
    if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    elif isinstance(checkpoint, dict):
        state_dict = checkpoint
    else:
        raise ValueError("Format du modèle de base non supporté")

    model.load_state_dict(state_dict, strict=False)


class _SimpleCNN(nn.Module):
    """CNN from scratch pour classification rétinienne."""
    def __init__(self, num_classes):
        super().__init__()
        self.features = nn.Sequential(
            # Bloc 1
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2), nn.Dropout2d(0.1),
            # Bloc 2
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2), nn.Dropout2d(0.1),
            # Bloc 3
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d(128, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.MaxPool2d(2), nn.Dropout2d(0.2),
            # Bloc 4
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(),
            nn.MaxPool2d(2), nn.Dropout2d(0.2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(256 * 4 * 4, 512), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(512, 128),          nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


class _SimpleUNet(nn.Module):
    """UNet simplifié from scratch pour segmentation."""
    def __init__(self, in_channels=3, out_channels=2):
        super().__init__()

        def _block(ic, oc):
            return nn.Sequential(
                nn.Conv2d(ic, oc, 3, padding=1), nn.BatchNorm2d(oc), nn.ReLU(),
                nn.Conv2d(oc, oc, 3, padding=1), nn.BatchNorm2d(oc), nn.ReLU(),
            )

        self.enc1       = _block(in_channels, 32)
        self.enc2       = _block(32, 64)
        self.enc3       = _block(64, 128)
        self.pool       = nn.MaxPool2d(2)
        self.bottleneck = _block(128, 256)
        self.up3        = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.dec3       = _block(256, 128)
        self.up2        = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec2       = _block(128, 64)
        self.up1        = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.dec1       = _block(64, 32)
        self.head       = nn.Conv2d(32, out_channels, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        b  = self.bottleneck(self.pool(e3))
        d3 = self.dec3(torch.cat([self.up3(b),  e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.head(d1)


def _evaluate(model, loader, device):
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            preds   = model(images).argmax(dim=1)
            correct += (preds == labels).sum().item()
            total   += labels.size(0)
    return 100.0 * correct / total if total > 0 else 0.0


def _find_splits(root):
    """
    Cherche train/ et test/ dans le dossier extrait.
    Si absents, fait une répartition 70/30 automatique.
    """
    # Cas 1 : train/ test/ directement à la racine
    train_dir = os.path.join(root, 'train')
    test_dir  = os.path.join(root, 'test')
    if os.path.isdir(train_dir) and os.path.isdir(test_dir):
        return train_dir, test_dir

    # Cas 2 : un sous-dossier contient train/ et test/
    for sub in os.listdir(root):
        sub_path = os.path.join(root, sub)
        if not os.path.isdir(sub_path):
            continue
        t = os.path.join(sub_path, 'train')
        e = os.path.join(sub_path, 'test')
        if os.path.isdir(t) and os.path.isdir(e):
            return t, e
        # Training_Set / Validation_Set (Fundus_Train_Val_Data)
        t2 = os.path.join(sub_path, 'Training_Set')
        e2 = os.path.join(sub_path, 'Validation_Set')
        if os.path.isdir(t2) and os.path.isdir(e2):
            return t2, e2

    # Cas 3 : dossiers de classes directement dans root → split 70/30
    import random
    img_exts  = ('.jpg', '.jpeg', '.png', '.bmp')
    class_dirs = []
    for d in os.listdir(root):
        dp = os.path.join(root, d)
        if os.path.isdir(dp):
            imgs = [f for f in os.listdir(dp) if f.lower().endswith(img_exts)]
            if imgs:
                class_dirs.append((d, dp, imgs))

    if class_dirs:
        train_dir = os.path.join(root, '_train')
        test_dir  = os.path.join(root, '_test')
        for class_name, class_path, images in class_dirs:
            random.shuffle(images)
            split = int(len(images) * 0.7)
            for i, img in enumerate(images):
                dest = os.path.join(
                    train_dir if i < split else test_dir, class_name)
                os.makedirs(dest, exist_ok=True)
                shutil.copy2(os.path.join(class_path, img),
                             os.path.join(dest, img))
        return train_dir, test_dir

    raise ValueError(
        "Structure du dataset non reconnue. "
        "Attendu : train/ + test/, ou dossiers de classes directement."
    )
