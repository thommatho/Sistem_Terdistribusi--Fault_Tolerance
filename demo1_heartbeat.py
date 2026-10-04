"""
Demo 1 - Failure Detector dengan Heartbeat
Cara pakai:
    python demo1_heartbeat.py normal   -> semua node sehat
    python demo1_heartbeat.py gagal    -> Node-2 crash, Node-3 gangguan jaringan
"""
import sys
import time
import threading

TIMEOUT = 3.0     # detik: batas waktu tanpa heartbeat sebelum node dicurigai gagal
INTERVAL = 1.0    # setiap node mengirim heartbeat tiap 1 detik
DURASI = 10       # lama simulasi (detik)

skenario = sys.argv[1] if len(sys.argv) > 1 else "normal"
mulai = time.time()
last_seen = {n: mulai for n in ("Node-1", "Node-2", "Node-3")}
lock = threading.Lock()


def sekarang():
    return time.time() - mulai


def node_worker(nama, crash_at=None, macet=None):
    """Thread yang mensimulasikan satu node.
    crash_at : detik ketika node mati (berhenti mengirim heartbeat selamanya)
    macet    : (awal, akhir) rentang detik ketika jaringan node terganggu
    """
    while sekarang() < DURASI:
        t = sekarang()
        if crash_at is not None and t >= crash_at:
            return                                   # node crash
        terganggu = macet is not None and macet[0] <= t < macet[1]
        if not terganggu:
            with lock:
                last_seen[nama] = time.time()        # kirim heartbeat
        time.sleep(INTERVAL)


def failure_detector():
    status_lama = {n: "ACTIVE" for n in last_seen}
    print(f"=== FAILURE DETECTOR DENGAN HEARTBEAT (skenario: {skenario}) ===")
    print(f"Interval heartbeat: {INTERVAL}s | Timeout: {TIMEOUT}s\n")
    time.sleep(0.5)          # offset agar tidak bentrok dengan waktu kirim heartbeat
    while sekarang() < DURASI:
        baris, kejadian = [], []
        with lock:
            snapshot = dict(last_seen)
        for node, terakhir in snapshot.items():
            umur = time.time() - terakhir
            status = "ACTIVE" if umur <= TIMEOUT else "FAILED"
            baris.append(f"{node}: {status:<6} ({umur:3.1f}s)")
            if status != status_lama[node]:
                if status == "FAILED":
                    pesan = (f"{node} DICURIGAI GAGAL "
                             f"(tanpa heartbeat {umur:.1f}s > {TIMEOUT}s)")
                else:
                    pesan = f"{node} AKTIF KEMBALI -> sebelumnya FALSE POSITIVE"
                kejadian.append("  >> " + pesan)
                status_lama[node] = status
        print(f"t={sekarang():4.1f}s | " + " | ".join(baris))
        for k in kejadian:
            print(k)
        time.sleep(1.0)
    print("\nSimulasi selesai.")


if skenario == "gagal":
    konfigurasi = {"Node-1": {},
                   "Node-2": {"crash_at": 4.0},
                   "Node-3": {"macet": (1.5, 5.5)}}
else:
    konfigurasi = {"Node-1": {}, "Node-2": {}, "Node-3": {}}

for nama, opsi in konfigurasi.items():
    threading.Thread(target=node_worker, args=(nama,), kwargs=opsi, daemon=True).start()

failure_detector()
