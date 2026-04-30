# prepare_acrima.py
# Exécuter : python prepare_acrima.py
# Résultat : crée un dossier dataset_ready/ prêt à zipper

import os, shutil, random

# ── MODIFIE CE CHEMIN ──────────────────────────────────────
ACRIMA_IMAGES = r"C:\Users\YOUSSEF\Downloads\archive\ACRIMA\Images"
OUTPUT_DIR    = r"C:\Users\YOUSSEF\Downloads\dataset_ready"
# ──────────────────────────────────────────────────────────

if not os.path.isdir(ACRIMA_IMAGES):
    raise FileNotFoundError(
        "Le dossier ACRIMA_IMAGES est introuvable.\n"
        f"Chemin actuel: {ACRIMA_IMAGES}\n"
        "Astuce: extrais d'abord archive.zip puis pointe vers ...\\archive\\ACRIMA\\Images."
    )

glaucoma = []
normal   = []

for fname in os.listdir(ACRIMA_IMAGES):
    if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue
    if '_g_' in fname:          # ex: Im686_g_ACRIMA.png
        glaucoma.append(fname)
    else:                       # ex: Im001_ACRIMA.png
        normal.append(fname)

print(f"Glaucoma : {len(glaucoma)} images")
print(f"Normal   : {len(normal)} images")

random.shuffle(glaucoma)
random.shuffle(normal)

def split_and_copy(files, class_name, src_dir, out_dir):
    split = int(len(files) * 0.7)
    train_files = files[:split]
    test_files  = files[split:]

    for phase, flist in [('train', train_files), ('test', test_files)]:
        dest = os.path.join(out_dir, phase, class_name)
        os.makedirs(dest, exist_ok=True)
        for f in flist:
            shutil.copy2(os.path.join(src_dir, f), os.path.join(dest, f))
    print(f"  {class_name}: {split} train / {len(files)-split} test")

split_and_copy(glaucoma, 'glaucoma', ACRIMA_IMAGES, OUTPUT_DIR)
split_and_copy(normal,   'normal',   ACRIMA_IMAGES, OUTPUT_DIR)

print(f"\nDataset prêt dans : {OUTPUT_DIR}")
print("Structure :")
print("  dataset_ready/")
print("  ├── train/")
print("  │   ├── glaucoma/  (~277 images)")
print("  │   └── normal/    (~216 images)")
print("  └── test/")
print("      ├── glaucoma/  (~119 images)")
print("      └── normal/    (~93 images)")
print("\nZippe le dossier dataset_ready/ et uploade le ZIP.")