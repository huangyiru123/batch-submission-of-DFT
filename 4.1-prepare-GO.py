import os
import shutil
import subprocess
from pymatgen.core import Structure

MATERIAL_IDS = [
    "ZrSc2O5_mp-753401",
]
START_N = 22

BASE_DIR = "/public/home/huangyiru/My-Work/2602-multimode/3.4-Experiment/8.3-DFPT"
CIF_SRC = "/public/home/huangyiru/My-Work/2602-multimode/3.4-Experiment/8.1-pipeline/0-1000/cif"
INCAR_GO = os.path.join(BASE_DIR, "0.1-INCAR-geometry-opti")
VASP_SH = os.path.join(BASE_DIR, "0.1-vasp.sh")
VASPKIT = "/public/software/vaspkit.1.3.4/bin/vaspkit"

for i, mat_id in enumerate(MATERIAL_IDS):
    n = START_N + i
    mat_dir = os.path.join(BASE_DIR, f"{n}-{mat_id}")
    go_dir = os.path.join(mat_dir, "1-GO")

    for sub in ["1-GO", "2.1-scf", "3.1-dfpt", "3.2-bandgap"]:
        os.makedirs(os.path.join(mat_dir, sub), exist_ok=True)

    cif_src = os.path.join(CIF_SRC, f"{mat_id}.cif")
    cif_dst = os.path.join(mat_dir, f"{mat_id}.cif")
    shutil.copy(cif_src, cif_dst)

    structure = Structure.from_file(cif_dst)
    poscar_str = structure.to(fmt="poscar")
    with open(os.path.join(go_dir, "POSCAR"), "w") as f:
        f.write(poscar_str)
    print(f"[{n}-{mat_id}] POSCAR written: {structure.formula}")

    ret = subprocess.run(
        f"printf '1\\n102\\n2\\n0.03\\n' | {VASPKIT}",
        shell=True, capture_output=True, text=True, cwd=go_dir
    )
    if ret.returncode != 0 or not os.path.exists(os.path.join(go_dir, "KPOINTS")):
        print(f"[{n}-{mat_id}] KPOINTS failed\n{ret.stdout}\n{ret.stderr}")
        continue
    print(f"[{n}-{mat_id}] KPOINTS ok")

    ret = subprocess.run(
        f"printf '1\\n103\\n' | {VASPKIT}",
        shell=True, capture_output=True, text=True, cwd=go_dir
    )
    if ret.returncode != 0 or not os.path.exists(os.path.join(go_dir, "POTCAR")):
        print(f"[{n}-{mat_id}] POTCAR failed\n{ret.stdout}\n{ret.stderr}")
        continue
    print(f"[{n}-{mat_id}] POTCAR ok")

    shutil.copy(INCAR_GO, os.path.join(go_dir, "INCAR"))

    sh_dst = os.path.join(go_dir, "0.1-vasp.sh")
    shutil.copy(VASP_SH, sh_dst)
    with open(sh_dst, "r") as f:
        content = f.read()
    content = __import__("re").sub(r"#SBATCH --job-name=\S+", f"#SBATCH --job-name=GO-{n}", content)
    with open(sh_dst, "w") as f:
        f.write(content)
    print(f"[{n}-{mat_id}] INCAR + vasp.sh ok")

print("\n--- submitting jobs ---")
for i, mat_id in enumerate(MATERIAL_IDS):
    n = START_N + i
    go_dir = os.path.join(BASE_DIR, f"{n}-{mat_id}", "1-GO")
    sh_path = os.path.join(go_dir, "0.1-vasp.sh")
    if not os.path.exists(sh_path):
        print(f"[{n}-{mat_id}] skip: vasp.sh not found")
        continue
    ret = subprocess.run("sbatch 0.1-vasp.sh", shell=True, cwd=go_dir, capture_output=True, text=True)
    print(f"[{n}-{mat_id}] sbatch: {ret.stdout.strip()} {ret.stderr.strip()}")
