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


def list_images(root: Path):
    return [p for p in root.rglob("*") if is_image_file(p)]


def ensure_train_test_split(src_root: Path, work_dir: Path, train_per_class: int, test_per_class: int, seed: int):
    """
    Crée `train/` et `test/` sous `work_dir` depuis `src_root`.

    - Si `src_root/train` et `src_root/test` existent: on sous-échantillonne chaque classe.
    - Sinon: on suppose que `src_root/<class_name>/...` contient les images et on split 70/30 (ou via n_*).
    """
    train_src = src_root / "train"
    test_src = src_root / "test"

    out_train = work_dir / "train"
    out_test = work_dir / "test"
    out_train.mkdir(parents=True, exist_ok=True)
    out_test.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)

    if train_src.is_dir() and test_src.is_dir():
        classes = sorted({p.name for p in train_src.iterdir() if p.is_dir()} | {p.name for p in test_src.iterdir() if p.is_dir()})
        for cls in classes:
            cls_train_dir = train_src / cls
            cls_test_dir = test_src / cls
            imgs_train = list_images(cls_train_dir) if cls_train_dir.is_dir() else []
            imgs_test = list_images(cls_test_dir) if cls_test_dir.is_dir() else []

            if imgs_train:
                chosen_train = rng.sample(imgs_train, k=min(len(imgs_train), train_per_class))
            else:
                chosen_train = []

            if imgs_test:
                chosen_test = rng.sample(imgs_test, k=min(len(imgs_test), test_per_class))
            else:
                chosen_test = []

            dst_train_cls = out_train / cls
            dst_test_cls = out_test / cls
            dst_train_cls.mkdir(parents=True, exist_ok=True)
            dst_test_cls.mkdir(parents=True, exist_ok=True)

            for src_img in chosen_train:
                shutil.copy2(src_img, dst_train_cls / src_img.name)
            for src_img in chosen_test:
                shutil.copy2(src_img, dst_test_cls / src_img.name)
        return

    # Split automatique depuis dossiers de classes à la racine
    classes = [p.name for p in src_root.iterdir() if p.is_dir()]
    for cls in classes:
        cls_dir = src_root / cls
        imgs = list_images(cls_dir)
        if not imgs:
            continue

        rng.shuffle(imgs)
        # Priorité: respecter train_per_class / test_per_class si possible
        chosen_train = imgs[: min(len(imgs), train_per_class)]
        chosen_test = imgs[min(len(imgs), train_per_class): min(len(imgs), train_per_class + test_per_class)]

        dst_train_cls = out_train / cls
        dst_test_cls = out_test / cls
        dst_train_cls.mkdir(parents=True, exist_ok=True)
        dst_test_cls.mkdir(parents=True, exist_ok=True)

        for src_img in chosen_train:
            shutil.copy2(src_img, dst_train_cls / src_img.name)
        for src_img in chosen_test:
            shutil.copy2(src_img, dst_test_cls / src_img.name)


def zip_folder(folder: Path, output_zip: Path):
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob("*"):
            if p.is_file():
                rel = p.relative_to(folder)
                z.write(p, rel.as_posix())


def main():
    parser = argparse.ArgumentParser(description="Créer un dataset ZIP petit (train/test) à partir d'un dataset existant.")
    parser.add_argument("--input", required=True, help="Chemin du dataset (dossier OU zip).")
    parser.add_argument("--output", required=True, help="Chemin du dataset_zip de sortie (ex: dataset_small.zip).")
    parser.add_argument("--train-per-class", type=int, default=10, help="Nombre max d'images d'entraînement par classe.")
    parser.add_argument("--test-per-class", type=int, default=5, help="Nombre max d'images de test par classe.")
    parser.add_argument("--seed", type=int, default=42, help="Seed pour l'échantillonnage aléatoire.")
    args = parser.parse_args()

    inp = Path(args.input)
    out_zip = Path(args.output)

    if not inp.exists():
        raise SystemExit(f"Input introuvable: {inp}")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)

        if inp.is_file() and inp.suffix.lower() == ".zip":
            extract_dir = td_path / "extract"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(inp, "r") as z:
                z.extractall(extract_dir)

            # Si le zip contient un sous-dossier unique, on l'utilise
            subdirs = [p for p in extract_dir.iterdir() if p.is_dir()]
            src_root = subdirs[0] if len(subdirs) == 1 else extract_dir
        else:
            src_root = inp

        work_dir = td_path / "small"
        ensure_train_test_split(
            src_root=src_root,
            work_dir=work_dir,
            train_per_class=args.train_per_class,
            test_per_class=args.test_per_class,
            seed=args.seed,
        )

        # Zip: garde train/... et test/...
        # On zip folder parent pour obtenir train/ et test/ au top-level
        zip_folder(work_dir, out_zip)

    print(f"OK: dataset créé: {out_zip}")


if __name__ == "__main__":
    main()

