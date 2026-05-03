"""
hotspot.py
──────────
Crea un hotspot WiFi con contraseña para que los dispositivos cercanos
puedan conectarse y ver el dashboard sin necesidad de router externo.

Requisitos (ejecutar una sola vez como root):
    sudo apt install -y network-manager qrencode

Uso
───
    import hotspot
    info = hotspot.start()   # devuelve {"ssid": ..., "password": ..., "ip": ..., "url": ...}
    hotspot.stop()           # cierra el hotspot al salir

Estrategia
──────────
  1. nmcli / NetworkManager — Raspberry Pi OS, Ubuntu, etc.
  2. hostapd + dnsmasq como fallback si nmcli no está disponible.
  3. Imprime instrucciones de conexión + QR ASCII en la terminal.
"""

import os
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional


# ── Configuración (sobreescribible con variables de entorno) ──────────────────
SSID       = os.environ.get("HOTSPOT_SSID",     "SFGoal")
PASSWORD   = os.environ.get("HOTSPOT_PASSWORD", "football1")
INTERFACE  = os.environ.get("HOTSPOT_IFACE",    "wlan0")
HOTSPOT_IP = os.environ.get("HOTSPOT_IP",       "192.168.4.1")

_backend: Optional[str] = None
_con_name = "sfgoal-hotspot"


# ── API pública ───────────────────────────────────────────────────────────────

def start() -> dict:
    """Levanta el hotspot. Devuelve {"ssid", "password", "ip", "url"}."""
    global _backend

    if shutil.which("nmcli"):
        _start_nmcli()
        _backend = "nmcli"
    elif shutil.which("hostapd"):
        _start_hostapd()
        _backend = "hostapd"
    else:
        print(
            "[HOTSPOT] AVISO: nmcli ni hostapd encontrados.\n"
            "          Instala con:  sudo apt install -y network-manager\n"
            "          El servidor seguirá accesible en la LAN local."
        )
        _backend = None

    ip  = HOTSPOT_IP if _backend else _get_local_ip()
    url = f"http://{ip}:5000"

    info = {"ssid": SSID, "password": PASSWORD, "ip": ip, "url": url}
    _print_connection_info(info)
    return info


def stop() -> None:
    """Cierra el hotspot limpiamente."""
    if _backend == "nmcli":
        _stop_nmcli()
    elif _backend == "hostapd":
        _stop_hostapd()


# ── Backend nmcli ─────────────────────────────────────────────────────────────

def _start_nmcli() -> None:
    subprocess.run(["nmcli", "connection", "delete", _con_name], capture_output=True)

    result = subprocess.run([
        "nmcli", "device", "wifi", "hotspot",
        "ifname",   INTERFACE,
        "con-name", _con_name,
        "ssid",     SSID,
        "password", PASSWORD,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[HOTSPOT] nmcli error: {result.stderr.strip()}")
        raise RuntimeError("No se pudo crear el hotspot con nmcli")

    time.sleep(2)

    subprocess.run([
        "nmcli", "connection", "modify", _con_name,
        "ipv4.addresses", f"{HOTSPOT_IP}/24",
        "ipv4.method",    "shared",
    ], capture_output=True)

    subprocess.run(["nmcli", "connection", "up", _con_name], capture_output=True)
    time.sleep(1)
    print(f"[HOTSPOT] nmcli: hotspot '{SSID}' activo en {INTERFACE}")


def _stop_nmcli() -> None:
    subprocess.run(["nmcli", "connection", "delete", _con_name], capture_output=True)
    print("[HOTSPOT] nmcli: hotspot cerrado.")


# ── Backend hostapd + dnsmasq ─────────────────────────────────────────────────

_HOSTAPD_CONF = "/tmp/sfgoal_hostapd.conf"
_DNSMASQ_CONF = "/tmp/sfgoal_dnsmasq.conf"
_hostapd_proc = None
_dnsmasq_proc = None


def _start_hostapd() -> None:
    global _hostapd_proc, _dnsmasq_proc

    Path(_HOSTAPD_CONF).write_text(
        f"interface={INTERFACE}\n"
        f"driver=nl80211\n"
        f"ssid={SSID}\n"
        f"hw_mode=g\n"
        f"channel=6\n"
        f"auth_algs=1\n"
        f"ignore_broadcast_ssid=0\n"
        f"wpa=2\n"
        f"wpa_passphrase={PASSWORD}\n"
        f"wpa_key_mgmt=WPA-PSK\n"
        f"wpa_pairwise=TKIP\n"
        f"rsn_pairwise=CCMP\n"
    )

    subprocess.run(["ip", "addr", "add", f"{HOTSPOT_IP}/24", "dev", INTERFACE], capture_output=True)
    subprocess.run(["ip", "link", "set", INTERFACE, "up"], capture_output=True)

    dhcp_start = HOTSPOT_IP.rsplit(".", 1)[0] + ".10"
    dhcp_end   = HOTSPOT_IP.rsplit(".", 1)[0] + ".50"
    Path(_DNSMASQ_CONF).write_text(
        f"interface={INTERFACE}\n"
        f"dhcp-range={dhcp_start},{dhcp_end},255.255.255.0,24h\n"
        f"address=/#/{HOTSPOT_IP}\n"
    )

    _hostapd_proc = subprocess.Popen(
        ["hostapd", _HOSTAPD_CONF], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    _dnsmasq_proc = subprocess.Popen(
        ["dnsmasq", "--no-daemon", f"--conf-file={_DNSMASQ_CONF}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    print(f"[HOTSPOT] hostapd: hotspot '{SSID}' activo en {INTERFACE}")


def _stop_hostapd() -> None:
    for proc in (_hostapd_proc, _dnsmasq_proc):
        if proc:
            proc.send_signal(signal.SIGTERM)
    subprocess.run(["ip", "addr", "del", f"{HOTSPOT_IP}/24", "dev", INTERFACE], capture_output=True)
    print("[HOTSPOT] hostapd: hotspot cerrado.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _print_connection_info(info: dict) -> None:
    url = info["url"]
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║       📶  SMART GOAL  –  WiFi Hotspot        ║")
    print("╠══════════════════════════════════════════════╣")
    print(f"║  Red        :  {info['ssid']:<30}║")
    print(f"║  Contraseña :  {info['password']:<30}║")
    print(f"║  URL        :  {url:<30}║")
    print("╠══════════════════════════════════════════════╣")
    print("║  1. Conéctate al WiFi de arriba              ║")
    print("║  2. Abre la URL en cualquier navegador       ║")
    print("╚══════════════════════════════════════════════╝")

    if shutil.which("qrencode"):
        qr = f"WIFI:T:WPA;S:{info['ssid']};P:{info['password']};;"
        print("\n  Escanea para conectarte al WiFi directamente:\n")
        subprocess.run(["qrencode", "-t", "UTF8", "-m", "2", qr])
    else:
        print("\n  (sudo apt install qrencode para el QR)")

    print()
