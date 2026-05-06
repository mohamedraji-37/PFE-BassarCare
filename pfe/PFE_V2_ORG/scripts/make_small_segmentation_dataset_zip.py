import argparse
import os
import random
import shutil
import tempfile
import zipfile
from pathlib import Path


IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def is_image_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in IMG_EXTS


def list_images(folder: Path):
    return [p for p in folder.iterdir() if is_image_file(p)]


def pair_by_stem(images_dir: Path, masks_dir: Path):
    """
    Associe image <-> mask par stem (nom sans extension).
    Exemple: image_12.jpg <-> image_12.png (ou autre extension).
    """
    images = list_images(images_dir)
    masks_index = {}
    for m in masks_dir.rglob("*"):
        if is_image_file(m):
            masks_index[m.stem] = m

    pairs = []
    for img in images:
        if img.stem in masks_index:
            pairs.append((img, masks_index[img.stem]))
    return pairs


def pair_by_suffix_last3(images_dir: Path, masks_dir: Path):
    """
    Pairing adapté au dataset actuel:
    - masques: Glaucoma_###.png (### = 001..)
    - images:  <ID>_(left|right).jpg
    On associe un masque ### à toute image dont ID%1000 == ###.
    Ensuite, on renomme le masque en <image_stem>.<mask_ext> pour que
    le pairing du dataset final (par stem) fonctionne.
    """
    masks_index = {}
    for m in masks_dir.rglob("*"):
        if m.is_file() and m.suffix.lower() in IMG_EXTS:
            # Exemple: Glaucoma_001
            if m.stem.lower().startswith("glaucoma_"):
                suf = m.stem.split("_", 1)[1]
                if suf.isdigit():
                    masks_index[suf.zfill(3)] = m

    pairs = []
    for img in images_dir.rglob("*"):
        if not img.is_file() or img.suffix.lower() not in IMG_EXTS:
            continue
        # Exemple: 1020_left
        name = img.stem
        if "_" not in name:
            continue
        left_right = name.split("_", 1)[1]
        if left_right not in ("left", "right"):
            continue
        id_part = name.split("_", 1)[0]
        if not id_part.isdigit():
            continue
        suffix = f"{int(id_part) % 1000:03d}"
        m = masks_index.get(suffix)
        if m is None:
            continue
        pairs.append((img, m))

    return pairs


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def zip_folder(folder: Path, output_zip: Path):
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob("*"):
            if p.is_file():
                rel = p.relative_to(folder.parent)
                z.write(p, rel.as_posix())


def sample_pairs(pairs, n, rng: random.Random):
    if not pairs:
        return []
    if n <= 0:
        return []
    n = min(n, len(pairs))
    rng.shuffle(pairs)
    return pairs[:n]


def main():
    parser = argparse.ArgumentParser(description="Créer un petit dataset ZIP pour segmentation (images + masks).")
    parser.add_argument("--input", required=True, help="Dossier du dataset segmentation (doit contenir train/images train/masks etc).")
    parser.add_argument("--output", required=True, help="Chemin zip de sortie (ex: dataset_small_seg.zip).")
    parser.add_argument("--train-n", type=int, default=20, help="Nombre max de paires image/mask pour train.")
    parser.add_argument("--test-n", type=int, default=10, help="Nombre max de paires image/mask pour test.")
    parser.add_argument("--seed", type=int, default=42, help="Seed pour l'aléatoire.")
    parser.add_argument("--pair-mode", default="stem", choices=["stem", "suffix_last3"],
                        help="Mode de pairing image<->mask: 'stem' (nom identique) ou 'suffix_last3' (mask Glaucoma_### avec images dont ID%%1000==###).")
    args = parser.parse_args()

    inp = Path(args.input)
    out_zip = Path(args.output)

    # Deux modes possibles:
    # (1) Dataset déjà structuré:
    #   train/images, train/masks, test/images, test/masks
    #
    # (2) Dataset brut (celui de ton ZIP):
    #   glaucoma/*.jpg  (images)
    #   glaucoma/*.png  (masks)
    #   (donc pas de train/test séparés)
    glaucoma_raw_dir = inp / "glaucoma"
    raw_mode = glaucoma_raw_dir.is_dir()

    if not raw_mode:
        required = [
            inp / "train" / "images",
            inp / "train" / "masks",
            inp / "test" / "images",
            inp / "test" / "masks",
        ]
        for r in required:
            if not r.is_dir():
                raise SystemExit(
                    f"Structure manquante: {r}\n"
                    "Attendu: soit train/images+masks+test/images+masks, soit un dossier brut 'glaucoma/' contenant jpg+png."
                )

    rng = random.Random(args.seed)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        work_dir = td / "seg_small"
        train_out_images = work_dir / "train" / "images"
        train_out_masks = work_dir / "train" / "masks"
        test_out_images = work_dir / "test" / "images"
        test_out_masks = work_dir / "test" / "masks"

        ensure_dir(train_out_images)
        ensure_dir(train_out_masks)
        ensure_dir(test_out_images)
        ensure_dir(test_out_masks)

        if raw_mode:
            # Dataset brut: on construit une seule liste de paires et on split dedans.
            if args.pair_mode == "stem":
                all_pairs = pair_by_stem(glaucoma_raw_dir, glaucoma_raw_dir)
                # fallback: si rien ne matche, tenter suffix_last3
                if not all_pairs:
                    all_pairs = pair_by_suffix_last3(glaucoma_raw_dir, glaucoma_raw_dir)
            else:
                all_pairs = pair_by_suffix_last3(glaucoma_raw_dir, glaucoma_raw_dir)

            # Shuffle stable puis split simple sans overlap.
            rng.shuffle(all_pairs)
            train_pairs = sample_pairs(all_pairs, args.train_n, rng)
            remaining = [p for p in all_pairs if p not in train_pairs]
            test_pairs = sample_pairs(remaining, args.test_n, rng)
        else:
            # Dataset déjà structuré train/test séparés.
            if args.pair_mode == "stem":
                train_pairs = pair_by_stem(inp / "train" / "images", inp / "train" / "masks")
                test_pairs = pair_by_stem(inp / "test" / "images", inp / "test" / "masks")
            else:
                train_pairs = pair_by_suffix_last3(inp / "train" / "images", inp / "train" / "masks")
                test_pairs = pair_by_suffix_last3(inp / "test" / "images", inp / "test" / "masks")

        train_pairs = sample_pairs(train_pairs, args.train_n, rng)
        test_pairs = sample_pairs(test_pairs, args.test_n, rng)

        for img_path, mask_path in train_pairs:
            shutil.copy2(img_path, train_out_images / img_path.name)
            # Assure que le stem du masque correspond au stem de l'image
            out_mask = train_out_masks / f"{img_path.stem}{mask_path.suffix}"
            shutil.copy2(mask_path, out_mask)

        for img_path, mask_path in test_pairs:
            shutil.copy2(img_path, test_out_images / img_path.name)
            out_mask = test_out_masks / f"{img_path.stem}{mask_path.suffix}"
            shutil.copy2(mask_path, out_mask)

        zip_folder(work_dir, out_zip)

    print(f"OK: dataset segmentation créé: {out_zip}")


if __name__ == "__main__":
    main()

