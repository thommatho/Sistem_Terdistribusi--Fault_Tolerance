"""
Demo 4 - Replikasi dengan Quorum (gaya Amazon Dynamo): N=3, W=2, R=2
Menunjukkan bagaimana sistem industri tetap melayani request saat ada node mati,
serta bagaimana data basi diperbaiki lewat read repair (anti-entropy).
Cara pakai:
    python demo4_quorum.py
"""
N, W, R = 3, 2, 2


class Node:
    def __init__(self, nama):
        self.nama = nama
        self.hidup = True
        self.data = {}                      # key -> (versi, nilai)

    def tulis(self, key, versi, nilai):
        if not self.hidup:
            return False
        self.data[key] = (versi, nilai)
        return True

    def baca(self, key):
        return self.data.get(key) if self.hidup else None


cluster = [Node("Node-A"), Node("Node-B"), Node("Node-C")]
versi_global = 0


def put(key, nilai):
    global versi_global
    hidup = [n for n in cluster if n.hidup]
    if len(hidup) < W:                      # koordinator menolak sebelum menulis apa pun
        print(f"  PUT {key}='{nilai}' -> hanya {len(hidup)}/{N} replica hidup (butuh W={W}) "
              f"=> DITOLAK (quorum tulis tidak tercapai)")
        return False
    versi_global += 1
    ack = [n.nama for n in hidup if n.tulis(key, versi_global, nilai)]
    print(f"  PUT {key}='{nilai}' (v{versi_global}) -> ACK dari {ack} "
          f"({len(ack)}/{N}, butuh W={W}) => BERHASIL")
    return True


def get(key, dari):
    """Koordinator membaca dari R replica, ambil versi terbaru, lalu read repair."""
    jawaban = [(n, n.baca(key)) for n in dari if n.hidup][:R]
    print(f"  GET {key} dari {[n.nama for n, _ in jawaban]}:")
    for n, v in jawaban:
        print(f"     {n.nama} -> {v}")
    if len(jawaban) < R:
        print(f"  => GAGAL (hanya {len(jawaban)} replica merespons, butuh R={R})")
        return None
    terbaru = max((v for _, v in jawaban if v), key=lambda x: x[0])
    for n, v in jawaban:
        if v != terbaru:
            n.tulis(key, *terbaru)
            print(f"     [READ REPAIR] {n.nama} diperbarui ke v{terbaru[0]}")
    print(f"  => NILAI TERBARU: '{terbaru[1]}' (v{terbaru[0]})")
    return terbaru


def status():
    teks = [f"{n.nama}={'UP' if n.hidup else 'DOWN'}" for n in cluster]
    print("  Status: " + " | ".join(teks))


print("=== REPLIKASI QUORUM (N=3, W=2, R=2) ===")
print("\n[1] Kondisi normal")
put("stok:laptop", "50")

print("\n[2] Node-C CRASH, tulis tetap berhasil (2 dari 3 replica cukup)")
cluster[2].hidup = False
status()
put("stok:laptop", "49")

print("\n[3] Node-C pulih tetapi datanya basi; baca dari Node-C & Node-B "
      "memicu read repair")
cluster[2].hidup = True
status()
get("stok:laptop", [cluster[2], cluster[1]])
print(f"  Isi Node-C sekarang: {cluster[2].data['stok:laptop']}")

print("\n[4] Dua node CRASH sekaligus (Node-B & Node-C): quorum tidak tercapai")
cluster[1].hidup = False
cluster[2].hidup = False
status()
put("stok:laptop", "48")
get("stok:laptop", cluster)
print("\nKesimpulan: sistem memilih konsistensi (menolak) "
      "daripada menerima data yang bisa hilang.")
