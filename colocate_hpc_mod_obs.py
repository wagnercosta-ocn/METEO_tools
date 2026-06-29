import json
import os
import sys
from multiprocessing import Pool, cpu_count

import numpy as np
import pandas as pd
import xarray as xr
'''
The code below colocates the model outputs with the observed data (e.g., altimeter and buoy data)
It was designed for large ammount of data, global model + swot swath altimeter data.

# =========================================================
# SOMMAIRE DU SCRIPT
# =========================================================
#
# A) ARGUMENTS DE LA LIGNE DE COMMANDE
#    - Lecture des chemins passés par le shell : modèle, obs, sortie, config.
#
# B) LECTURE DE LA CONFIGURATION JSON
#    - Chargement des paramètres définis dans le shell.
#
# C) FONCTIONS UTILITAIRES
#    - Vérification/conversion des longitudes.
#    - Construction de l'index spatial.
#    - Recherche du temps modèle le plus proche.
#    - Traitement d'un bloc d'observations.
#
# D) CONTRÔLES DE CONFIGURATION
#    - Vérification des paramètres, colonnes obs, variables modèle, sorties.
#
# E) LECTURE DU NETCDF MODÈLE
#    - Chargement des coordonnées, temps et variables modèle.
#
# F) INDEX SPATIAL DU MODÈLE
#    - Rangement des points modèle dans des cases spatiales.
#
# G) LECTURE DES OBSERVATIONS
#    - Lecture du fichier obs avec ou sans en-tête.
#
# H) CONVERSION DE LA DATE OBSERVATION
#    - Conversion de la colonne date en vrai datetime.
#
# I) CONTRÔLE ET CONVERSION DES LONGITUDES OBS
#    - Harmonisation des longitudes obs avec le système cible.
#
# J) PRÉPARATION DES COLONNES UTILES AU CALCUL
#    - Sélection des colonnes nécessaires à la colocalisation.
#
# K) MULTIPROCESSING
#    - Découpage des observations et traitement parallèle.
#
# L) CONSTRUCTION DE LA SORTIE
#    - Assemblage des résultats et réorganisation des colonnes.
#
# M) ÉCRITURE DU FICHIER WORKER
#    - Écriture du fichier texte avec séparateur, header et format numérique.
#
# =========================================================
'''

# =========================================================
# A) ARGUMENTS DE LA LIGNE DE COMMANDE
# =========================================================

if len(sys.argv) != 5:
    raise ValueError(
        "Usage : python colocate_hpc.py model.nc observations.txt output.txt config.json"
    )

nc_file = sys.argv[1]
alt_file = sys.argv[2]
out_file = sys.argv[3]
config_file = sys.argv[4]

print(f"Fichier modèle       : {nc_file}")
print(f"Fichier observations : {alt_file}")
print(f"Fichier sortie       : {out_file}")
print(f"Fichier config       : {config_file}")


# =========================================================
# B) LECTURE DE LA CONFIGURATION JSON
# =========================================================

with open(config_file, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


# =========================================================
# C) FONCTIONS UTILITAIRES
# =========================================================

def check_lon_system(name: str, value: str) -> None:
    """Vérifie qu'un système de longitude déclaré est autorisé."""
    if value not in {"180", "360"}:
        raise ValueError(f"{name} doit valoir '180' ou '360', pas '{value}'.")


def convert_lon_values(values, source_system: str, target_system: str):
    """
    Convertit des longitudes d'un système vers un autre.

    Systèmes possibles :
    - "180" : longitudes dans [-180, 180]
    - "360" : longitudes dans [0, 360]
    """
    arr = np.asarray(values, dtype=float).copy()

    if source_system == target_system:
        return arr

    if source_system == "180" and target_system == "360":
        return np.where(arr < 0.0, arr + 360.0, arr)

    if source_system == "360" and target_system == "180":
        return np.where(arr > 180.0, arr - 360.0, arr)

    raise ValueError(
        f"Conversion non gérée : source_system='{source_system}', "
        f"target_system='{target_system}'."
    )


def validate_lon_range(values, expected_system: str, label: str) -> None:
    """
    Vérifie que les longitudes sont cohérentes avec le système déclaré.
    """
    arr = np.asarray(values, dtype=float)

    if expected_system == "360":
        if np.any(arr < 0.0) or np.any(arr > 360.0):
            raise ValueError(
                f"{label} contient des longitudes hors de [0, 360], "
                "alors que le système déclaré est '360'."
            )

    elif expected_system == "180":
        if np.any(arr < -180.0) or np.any(arr > 180.0):
            raise ValueError(
                f"{label} contient des longitudes hors de [-180, 180], "
                "alors que le système déclaré est '180'."
            )

    else:
        raise ValueError(
            f"Système de longitude non reconnu pour {label} : {expected_system}"
        )


def grid_key(lat_value: float, lon_value: float):
    """
    Associe une position géographique à une case d'index spatial.

    RES_DEG ne modifie pas la résolution du modèle.
    Il sert seulement à accélérer la recherche du plus proche voisin.
    """
    r = CONFIG["RES_DEG"]
    return (
        int(np.floor(lat_value / r)),
        int(np.floor(lon_value / r)),
    )


def nearest_time_index(t_obs):
    """
    Retourne l'indice du temps modèle le plus proche du temps d'observation.
    """
    t_obs = np.datetime64(t_obs)
    i = np.searchsorted(time_np, t_obs)

    if i <= 0:
        return 0

    if i >= len(time_np):
        return len(time_np) - 1

    before = time_np[i - 1]
    after = time_np[i]

    if abs(t_obs - before) < abs(after - t_obs):
        return i - 1

    return i


def process_block(block_df):
    """
    Traite un bloc d'observations.

    Pour chaque observation :
    1) lit lat/lon/time par nom de colonne ;
    2) cherche le temps modèle le plus proche ;
    3) rejette si l'écart temporel dépasse TIME_WINDOW_SEC ;
    4) cherche les points modèle candidats dans les cases spatiales voisines ;
    5) sélectionne le point modèle spatialement le plus proche ;
    6) calcule mod_xxx, obs_xxx et diff_xxx ;
    7) recopie les colonnes obs auxiliaires demandées.
    """
    results = []

    for _, row in block_df.iterrows():

        lat_obs = float(row["lat"])
        lon_obs = float(row["lon"])
        t_obs = row["time"]

        # Recherche du temps modèle le plus proche.
        tidx = nearest_time_index(t_obs)

        dt = abs(
            (time_np[tidx] - np.datetime64(t_obs))
            .astype("timedelta64[s]")
            .astype(int)
        )

        if dt > CONFIG["TIME_WINDOW_SEC"]:
            continue

        # Recherche des points modèle dans la case de l'obs + 8 voisines.
        k = grid_key(lat_obs, lon_obs)
        candidates = []

        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                kk = (k[0] + di, k[1] + dj)
                if kk in grid_index:
                    candidates.extend(grid_index[kk])

        if not candidates:
            continue

        # Sélection du point modèle le plus proche.
        best_idx = None
        best_d = 1e99

        for i in candidates:
            dlat = lat_f[i] - lat_obs
            dlon = lon_f[i] - lon_obs
            d = dlat * dlat + dlon * dlon

            if d < best_d:
                best_d = d
                best_idx = i

        if best_d > CONFIG["MAX_DIST_DEG"] ** 2:
            continue

        # Ligne de sortie interne sous forme de dictionnaire.
        # L'ordre final sera choisi uniquement par OUTPUT_COLUMNS.
        out = {
            "date": t_obs,
            "lat": lat_obs,
            "lon": lon_obs,
        }

        keep_row = True

        for var_cfg in CONFIG["VARIABLES"]:
            var_name = var_cfg["name"]
            obs_col = var_cfg["obs_col"]

            model_flat = model_data[var_name][tidx].ravel()

            model_value = model_flat[best_idx]
            obs_value = float(row[obs_col])

            if not np.isfinite(model_value) or not np.isfinite(obs_value):
                keep_row = False
                break

            out[f"mod_{var_name}"] = float(model_value)
            out[f"obs_{var_name}"] = float(obs_value)
            out[f"diff_{var_name}"] = float(model_value - obs_value)

        if not keep_row:
            continue

        # Recopie des colonnes obs auxiliaires : vent, flag, sat, etc.
        for col in CONFIG["KEEP_OBS_COLUMNS"]:
            out[col] = row[col]

        results.append(out)

    return results


# =========================================================
# D) CONTRÔLES DE CONFIGURATION
# =========================================================

check_lon_system("MODEL_LON_SYSTEM", CONFIG["MODEL_LON_SYSTEM"])
check_lon_system("OBS_LON_SYSTEM", CONFIG["OBS_LON_SYSTEM"])
check_lon_system("TARGET_LON_SYSTEM", CONFIG["TARGET_LON_SYSTEM"])

CONFIG["KEEP_OBS_COLUMNS"] = CONFIG.get("KEEP_OBS_COLUMNS", [])
CONFIG["OBS_WITH_HEADER"] = CONFIG.get("OBS_WITH_HEADER", False)
CONFIG["OUTPUT_FLOAT_FORMAT"] = CONFIG.get("OUTPUT_FLOAT_FORMAT", "%.3f")

if not CONFIG["VARIABLES"]:
    raise ValueError("CONFIG['VARIABLES'] ne peut pas être vide.")

if len(CONFIG["ALT_COLUMNS"]) != len(set(CONFIG["ALT_COLUMNS"])):
    raise ValueError(
        "ALT_COLUMNS contient des doublons. "
        "Chaque colonne d'observation doit avoir un nom unique."
    )

if len(CONFIG["KEEP_OBS_COLUMNS"]) != len(set(CONFIG["KEEP_OBS_COLUMNS"])):
    raise ValueError("KEEP_OBS_COLUMNS contient des doublons.")

required_obs_columns = {"date", "lat", "lon"}

for var_cfg in CONFIG["VARIABLES"]:
    required_obs_columns.add(var_cfg["obs_col"])

for col in CONFIG["KEEP_OBS_COLUMNS"]:
    required_obs_columns.add(col)

missing_declared_columns = required_obs_columns.difference(CONFIG["ALT_COLUMNS"])

if missing_declared_columns:
    raise ValueError(
        f"Colonnes nécessaires absentes de ALT_COLUMNS : "
        f"{sorted(missing_declared_columns)}"
    )

print("Configuration lue correctement.")
print(f"ALT_COLUMNS          : {CONFIG['ALT_COLUMNS']}")
print(f"VARIABLES            : {CONFIG['VARIABLES']}")
print(f"KEEP_OBS_COLUMNS     : {CONFIG['KEEP_OBS_COLUMNS']}")
print(f"OUTPUT_COLUMNS       : {CONFIG['OUTPUT_COLUMNS']}")
print(f"OBS_WITH_HEADER      : {CONFIG['OBS_WITH_HEADER']}")
print(f"OUTPUT_FLOAT_FORMAT  : {CONFIG['OUTPUT_FLOAT_FORMAT']}")


# =========================================================
# E) LECTURE DU NETCDF MODÈLE
# =========================================================

print("Lecture du NetCDF...")

ds = xr.open_dataset(nc_file, decode_times=True)

time_np = ds[CONFIG["TIME_NAME"]].values
lat = ds[CONFIG["LAT_NAME"]].values
lon = ds[CONFIG["LON_NAME"]].values

validate_lon_range(lon, CONFIG["MODEL_LON_SYSTEM"], "Les longitudes du modèle")

lon = convert_lon_values(
    lon,
    CONFIG["MODEL_LON_SYSTEM"],
    CONFIG["TARGET_LON_SYSTEM"],
)

validate_lon_range(
    lon,
    CONFIG["TARGET_LON_SYSTEM"],
    "Les longitudes converties du modèle",
)

model_data = {}

for var_cfg in CONFIG["VARIABLES"]:
    var_name = var_cfg["name"]
    model_var = var_cfg["model_var"]

    if model_var not in ds.variables:
        raise ValueError(
            f"La variable NetCDF '{model_var}' est introuvable dans le fichier modèle."
        )

    # Chargement en mémoire NumPy pour accélérer les accès dans la boucle.
    model_data[var_name] = ds[model_var].values

print(f"Plage latitude modèle  : {lat.min()} -> {lat.max()}")
print(f"Plage longitude modèle : {lon.min()} -> {lon.max()}")
print(f"Nombre de temps modèle : {len(time_np)}")


# =========================================================
# F) INDEX SPATIAL DU MODÈLE
# =========================================================

lon2d, lat2d = np.meshgrid(lon, lat)

lat_f = lat2d.ravel()
lon_f = lon2d.ravel()

grid_index = {}

for i, (la, lo) in enumerate(zip(lat_f, lon_f)):
    k = grid_key(la, lo)
    grid_index.setdefault(k, []).append(i)

print(f"Nombre de points modèle  : {len(lat_f)}")
print(f"Nombre de cases indexées : {len(grid_index)}")


# =========================================================
# G) LECTURE DES OBSERVATIONS
# =========================================================

print("Lecture du fichier d'observations...")

if CONFIG["OBS_WITH_HEADER"]:
    alt = pd.read_csv(
        alt_file,
        sep=r"\s+",
        header=0,
    )

    missing_input_header_cols = set(CONFIG["ALT_COLUMNS"]).difference(alt.columns)

    if missing_input_header_cols:
        raise ValueError(
            "Le fichier obs possède un header, mais certaines colonnes déclarées "
            f"dans ALT_COLUMNS sont absentes du fichier : "
            f"{sorted(missing_input_header_cols)}"
        )

    # On réordonne selon ALT_COLUMNS pour rester cohérent avec la config.
    alt = alt[CONFIG["ALT_COLUMNS"]]

else:
    alt = pd.read_csv(
        alt_file,
        sep=r"\s+",
        names=CONFIG["ALT_COLUMNS"],
        header=None,
    )

print(f"Nombre de lignes obs lues : {len(alt)}")


# =========================================================
# H) CONVERSION DE LA DATE OBSERVATION
# =========================================================

alt["time"] = pd.to_datetime(
    alt["date"],
    format="%Y%m%d%H%M%S",
    errors="raise",
)


# =========================================================
# I) CONTRÔLE ET CONVERSION DES LONGITUDES OBS
# =========================================================

validate_lon_range(
    alt["lon"].values,
    CONFIG["OBS_LON_SYSTEM"],
    "Les longitudes des observations",
)

alt["lon"] = convert_lon_values(
    alt["lon"].values,
    CONFIG["OBS_LON_SYSTEM"],
    CONFIG["TARGET_LON_SYSTEM"],
)

validate_lon_range(
    alt["lon"].values,
    CONFIG["TARGET_LON_SYSTEM"],
    "Les longitudes converties des observations",
)


# =========================================================
# J) PRÉPARATION DES COLONNES UTILES AU CALCUL
# =========================================================

obs_value_cols = (
    ["lat", "lon", "time"]
    + [var_cfg["obs_col"] for var_cfg in CONFIG["VARIABLES"]]
    + CONFIG["KEEP_OBS_COLUMNS"]
)

# Suppression des doublons éventuels en conservant l'ordre.
obs_value_cols = list(dict.fromkeys(obs_value_cols))

missing_runtime_cols = set(obs_value_cols).difference(alt.columns)
if missing_runtime_cols:
    raise ValueError(
        f"Colonnes nécessaires absentes au moment du calcul : "
        f"{sorted(missing_runtime_cols)}"
    )

alt_work = alt[obs_value_cols].copy()

print(f"Colonnes utilisées pour le calcul : {obs_value_cols}")
print(f"Nombre de points d'observation   : {len(alt_work)}")


# =========================================================
# K) MULTIPROCESSING
# =========================================================

nproc = int(os.environ.get("SLURM_CPUS_PER_TASK", cpu_count()))

print(f"Nombre de CPU utilisés : {nproc}")

blocks = np.array_split(alt_work, nproc * 4)

with Pool(nproc) as pool:
    results = pool.map(process_block, blocks)

results = [item for sublist in results for item in sublist]


# =========================================================
# L) CONSTRUCTION DE LA SORTIE
# =========================================================

print(f"Nombre total de colocalisations : {len(results)}")

internal_columns = ["date", "lat", "lon"]

for var_cfg in CONFIG["VARIABLES"]:
    var_name = var_cfg["name"]
    internal_columns.extend([
        f"mod_{var_name}",
        f"obs_{var_name}",
        f"diff_{var_name}",
    ])

internal_columns.extend(CONFIG["KEEP_OBS_COLUMNS"])

df = pd.DataFrame(results, columns=internal_columns)

if len(df) > 0:
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.strftime(
        CONFIG["OUTPUT_DATE_FORMAT"]
    )

missing_output_columns = set(CONFIG["OUTPUT_COLUMNS"]).difference(df.columns)

if missing_output_columns:
    raise ValueError(
        f"Colonnes demandées dans OUTPUT_COLUMNS introuvables : "
        f"{sorted(missing_output_columns)}"
    )

df_out = df[CONFIG["OUTPUT_COLUMNS"]]


# =========================================================
# M) ÉCRITURE DU FICHIER WORKER
# =========================================================

df_out.to_csv(
    out_file,
    sep=CONFIG["OUTPUT_SEPARATOR"],
    index=False,
    header=CONFIG["OUTPUT_WITH_HEADER"],
    float_format=CONFIG["OUTPUT_FLOAT_FORMAT"],
)

print(f"Fichier écrit : {out_file}")

                                                                                                                                            
