"""
Demo 2 - Simulasi PBFT (Practical Byzantine Fault Tolerance)
Cara pakai:
    python demo2_pbft.py --n 4 --f 1                 -> semua replica jujur
    python demo2_pbft.py --n 4 --f 1 --byzantine 3   -> replica-3 berkhianat (AMAN)
    python demo2_pbft.py --n 3 --f 1 --byzantine 2   -> n < 3f+1 (GAGAL)
"""
import argparse
import hashlib

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=4, help="jumlah replica")
ap.add_argument("--f", type=int, default=1, help="jumlah node Byzantine yg ditoleransi")
ap.add_argument("--byzantine", type=int, nargs="*", default=[],
                help="id replica yang berkhianat")
args = ap.parse_args()

N, F = args.n, args.f
PRIMARY = 0
REQUEST = "TRANSFER 100 dari A ke B"


def digest(teks):
    return hashlib.sha256(teks.encode()).hexdigest()[:8]


class Replica:
    def __init__(self, rid):
        self.id = rid
        self.byz = rid in args.byzantine
        self.prepares = {}      # id pengirim -> digest
        self.commits = {}
        self.digest = None
        self.prepared = False
        self.committed = False

    def tag(self):
        return f"R{self.id}{'*' if self.byz else ' '}"


replicas = [Replica(i) for i in range(N)]
d = digest(REQUEST)

print(f"=== SIMULASI PBFT: n={N}, f={F}, Byzantine={args.byzantine or 'tidak ada'} ===")
syarat = "TERPENUHI" if N >= 3 * F + 1 else "TIDAK TERPENUHI"
print(f"Syarat teorema: n >= 3f+1 = {3*F+1} -> {syarat}")
print(f"Request client : '{REQUEST}'  (digest={d})\n")

# --- Fase 1: PRE-PREPARE ---------------------------------------------------
print("[1] PRE-PREPARE: primary R0 broadcast (view=0, seq=1, digest) ke semua backup")
for r in replicas:
    r.digest = d

# --- Fase 2: PREPARE -------------------------------------------------------
print("[2] PREPARE: setiap backup broadcast PREPARE. "
      "Replica 'prepared' bila punya >= 2f PREPARE cocok")
for pengirim in replicas:
    if pengirim.id == PRIMARY:
        continue                                      # primary tidak mengirim PREPARE
    isi = digest("PALSU") if pengirim.byz else d     # replica Byzantine mengirim digest palsu
    for penerima in replicas:
        penerima.prepares[pengirim.id] = isi
for r in replicas:
    valid = sum(1 for v in r.prepares.values() if v == r.digest)
    r.prepared = valid >= 2 * F
    status = "PREPARED" if r.prepared else "belum prepared"
    if r.byz:
        status = "(Byzantine: perilaku sembarang)"
    print(f"    {r.tag()} PREPARE valid = {valid} (butuh {2*F}) -> {status}")

# --- Fase 3: COMMIT --------------------------------------------------------
print("[3] COMMIT: replica yang prepared broadcast COMMIT. "
      "'committed' bila punya >= 2f+1 COMMIT cocok")
for pengirim in replicas:
    if pengirim.prepared or pengirim.byz:
        isi = digest("PALSU") if pengirim.byz else d
        for penerima in replicas:
            penerima.commits[pengirim.id] = isi
for r in replicas:
    valid = sum(1 for v in r.commits.values() if v == r.digest)
    r.committed = r.prepared and valid >= 2 * F + 1
    status = "COMMITTED" if r.committed else "belum committed"
    if r.byz:
        status = "(Byzantine: perilaku sembarang)"
    print(f"    {r.tag()} COMMIT valid  = {valid} (butuh {2*F+1}) -> {status}")

# --- Fase 4: EXECUTE & REPLY ----------------------------------------------
print("[4] EXECUTE & REPLY: replica yang committed mengeksekusi request dan membalas client")
balasan = []
for r in replicas:
    if r.byz:
        balasan.append((r.id, "HASIL-PALSU"))
        print(f"    {r.tag()} -> reply 'HASIL-PALSU'  (Byzantine)")
    elif r.committed:
        balasan.append((r.id, "OK: transfer berhasil"))
        print(f"    {r.tag()} -> reply 'OK: transfer berhasil'")
    else:
        print(f"    {r.tag()} -> tidak membalas")

# --- Client menunggu f+1 balasan identik ---------------------------------
print(f"\n[CLIENT] Menunggu f+1 = {F+1} balasan yang identik")
hitung = {}
for _, h in balasan:
    hitung[h] = hitung.get(h, 0) + 1
diterima = [h for h, c in hitung.items() if c >= F + 1]
if diterima:
    jawaban = diterima[0]
    print(f"HASIL: KONSENSUS TERCAPAI -> '{jawaban}' ({hitung[jawaban]} balasan identik)")
else:
    print("HASIL: KONSENSUS GAGAL -> tidak ada jawaban yang didukung f+1 replica")
