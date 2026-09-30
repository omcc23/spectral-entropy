import os
import numpy as np
from Bio import SeqIO
from collections import defaultdict
# SETTINGS
FASTA_FILE = "diverse_long_genomes_voss.fasta"
# Cache stores normalized Shannon entropy, not the old 0-to-2 values.
CACHE_DIR = "shannon_entropy_npz_normalized"
os.makedirs(CACHE_DIR, exist_ok=True)
GROUPS = ["Bacteria", "Plants", "Mammals", "Insects", "Worms", "ColdBlooded"]
# IDENTIFY GROUP

def get_group(record_id):
    for g in GROUPS:
        if record_id.startswith(g):
            return g
    return None
# NORMALIZED SHANNON ENTROPY

def shannon_entropy(seq):
    seq = seq.upper()
    length = len(seq)
    if length == 0:
        return np.nan, None
    counts = np.array([seq.count("A"), seq.count("C"), seq.count("G"), seq.count("T")], dtype=float)
    probabilities = counts / length
    # Remove zero-probability terms for the entropy sum only
    nonzero = probabilities[probabilities > 0]
    # Shannon entropy
    H = -np.sum(nonzero * np.log2(nonzero))
    # Normalize Shannon entropy to 0-1.
    H_normalized = H / np.log2(4)
    return H_normalized, probabilities

def print_base_probabilities(probabilities):
    labels = ["A", "C", "G", "T"]
    parts = [f"p_{base}={prob:.6f}" for base, prob in zip(labels, probabilities)]
    print("    " + "  ".join(parts) + f"  sum={np.sum(probabilities):.6f}")
# CACHE NAME

def cache_name(record_id):
    safe = record_id.replace("/", "_").replace("\\", "_")
    return os.path.join(CACHE_DIR, safe + "_shannon_normalized.npz")
# MAIN

def main():
    kingdom_values = defaultdict(list)
    print("==============================")
    print("NORMALIZED SHANNON ENTROPY CACHE")
    print("==============================")
    records = list(SeqIO.parse(FASTA_FILE, "fasta"))
    total = len(records)
    for i, record in enumerate(records, start=1):
        group = get_group(record.id)
        if group is None:
            continue
        filename = cache_name(record.id)
        # LOAD EXISTING CACHE
        if os.path.exists(filename):
            data = np.load(filename)
            H = float(data["entropy"])
            print(f"[{i}/{total}] " f"Loaded {record.id} " f"Normalized H={H:.5f}")
            if all(key in data for key in ("A", "C", "G", "T", "genome_length")):
                length = float(data["genome_length"])
                if length > 0:
                    print_base_probabilities(
                        np.array(
                            [float(data["A"]), float(data["C"]), float(data["G"]), float(data["T"])]
                        )
                        / length
                    )
        else:
            seq = str(record.seq).upper()
            # Keep only canonical bases
            seq = "".join(b for b in seq if b in "ACGT")
            H, probabilities = shannon_entropy(seq)
            if probabilities is None:
                print(f"[{i}/{total}] " f"Skipped {record.id}: empty sequence")
                continue
            np.savez(
                filename,
                dataset="Normalized_Shannon_entropy",
                record_id=record.id,
                genome_length=len(seq),
                entropy=H,
                A=seq.count("A"),
                C=seq.count("C"),
                G=seq.count("G"),
                T=seq.count("T"),
                p_A=probabilities[0],
                p_C=probabilities[1],
                p_G=probabilities[2],
                p_T=probabilities[3],
            )
            print(f"[{i}/{total}] " f"Calculated {record.id} " f"Normalized H={H:.5f}")
            print_base_probabilities(probabilities)
        kingdom_values[group].append(H)
    # GROUP SUMMARY
    print("\n\n==============================")
    print("NORMALIZED SHANNON SUMMARY")
    print("==============================")
    table = []
    for group in GROUPS:
        values = np.array(kingdom_values[group])
        if len(values) == 0:
            avg = np.nan
        else:
            avg = np.mean(values)
        print(f"{group:15s} " f"{len(values):3d} genomes " f"Average normalized H = {avg:.6f}")
        table.append([group, avg])
    # SAVE SUMMARY
    np.savez(
        "kingdom_normalized_shannon_summary.npz",
        kingdoms=np.array([x[0] for x in table]),
        mean_entropy=np.array([x[1] for x in table]),
    )
    print("\nSaved:")
    print("kingdom_normalized_shannon_summary.npz")
# RUN
if __name__ == "__main__":
    main()
