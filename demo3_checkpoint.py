"""
Demo 3 - Checkpointing & Rollback Recovery pada sistem e-commerce (5 service)
Cara pakai:
    python demo3_checkpoint.py koordinasi   -> coordinated checkpointing (rollback SEMUA)
    python demo3_checkpoint.py naif         -> hanya service yang crash yang di-restore
"""
import json
import os
import shutil
import sys

strategi = sys.argv[1] if len(sys.argv) > 1 else "koordinasi"
TOTAL_ORDER = 10
CKPT_SETIAP = 3          # checkpoint setelah order ke-3, 6, 9
ORDER_CRASH = 8          # service payment crash saat memproses order ke-8
FOLDER = "checkpoints"

shutil.rmtree(FOLDER, ignore_errors=True)
os.makedirs(FOLDER)

state = {
    "user_auth":    {"login": 0},
    "inventory":    {"stok": 100, "terjual": 0},
    "payment":      {"transaksi": 0},
    "shipping":     {"paket": 0},
    "notification": {"email": 0},
}


class ServiceCrash(Exception):
    pass


def proses_order(no, crash=False):
    state["user_auth"]["login"] += 1
    state["inventory"]["stok"] -= 1
    state["inventory"]["terjual"] += 1
    if crash:
        raise ServiceCrash("payment")   # crash setelah stok berkurang, sebelum bayar dicatat
    state["payment"]["transaksi"] += 1
    state["shipping"]["paket"] += 1
    state["notification"]["email"] += 1


def simpan_checkpoint(no):
    """Checkpoint dilakukan di antara dua order (tidak ada pesan 'dalam perjalanan')."""
    path = f"{FOLDER}/ckpt_{no}.json"
    with open(path, "w") as f:
        json.dump(state, f)
    print(f"  [CHECKPOINT] {path} disimpan untuk {len(state)} service")


def muat_checkpoint(no):
    with open(f"{FOLDER}/ckpt_{no}.json") as f:
        return json.load(f)


def cetak_state():
    for svc, isi in state.items():
        print(f"  {svc:<13}: {isi}")


print(f"=== CHECKPOINTING E-COMMERCE (strategi: {strategi}) ===")
order, ckpt_terakhir, sudah_crash = 1, 0, False
while order <= TOTAL_ORDER:
    try:
        proses_order(order, crash=(order == ORDER_CRASH and not sudah_crash))
        print(f"Order {order:>2}: auth > inventory > payment > shipping > notification  [OK]")
        if order % CKPT_SETIAP == 0:
            simpan_checkpoint(order)
            ckpt_terakhir = order
        order += 1
    except ServiceCrash as e:
        sudah_crash = True
        print(f"Order {order:>2}: !!! SERVICE '{e}' CRASH "
              "(stok sudah berkurang, pembayaran belum dicatat)")
        if strategi == "koordinasi":
            print(f"  [RECOVERY] Rollback SEMUA service ke ckpt_{ckpt_terakhir}.json")
            state = muat_checkpoint(ckpt_terakhir)
            order = ckpt_terakhir + 1
            print(f"  [RECOVERY] Replay order {order} s.d. {TOTAL_ORDER}")
        else:
            print(f"  [RECOVERY] Hanya 'payment' di-restore dari ckpt_{ckpt_terakhir}.json")
            state["payment"] = muat_checkpoint(ckpt_terakhir)["payment"]
            order += 1                      # service lain lanjut tanpa rollback

print("\n=== STATE AKHIR ===")
cetak_state()

nilai = {
    "login": state["user_auth"]["login"],
    "terjual": state["inventory"]["terjual"],
    "transaksi": state["payment"]["transaksi"],
    "paket": state["shipping"]["paket"],
    "email": state["notification"]["email"],
}
print("\n=== VALIDASI KONSISTENSI (semua nilai harus sama) ===")
print("  " + " | ".join(f"{k}={v}" for k, v in nilai.items()))
if len(set(nilai.values())) == 1:
    print("  HASIL: KONSISTEN - global state valid, tidak ada order yang hilang/yatim")
else:
    print("  HASIL: TIDAK KONSISTEN - ada barang terjual tanpa "
          "pembayaran/pengiriman (orphan state)")
