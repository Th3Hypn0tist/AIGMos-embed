"""Network configuration; no implicit network traffic beyond reading neighbor cache."""
from getpass import getpass
from .network import neighbors,connectivity

def run(manager,mac,show):
    while True:
        print("\nNetwork Manager")
        show(manager.network_view(mac))
        print("1 IP mode  2 Wi-Fi  3 OSC destination  4 Neighbor inventory  5 Ping  0 Back")
        try:
            action=input("> ").strip()
            if action=="0": return
            if action=="1":
                mode=input("Mode (auto/static/dhcp): ")
                address=input("IPv4: ") if mode=="static" else None
                show(manager.network(mac,mode,address,neighbors()))
            elif action=="2":
                show(manager.set_wifi(mac,input("SSID: "),getpass("Wi-Fi password: ")))
            elif action=="3":
                show(manager.set_endpoint(mac,input("Master IPv4: "),int(input("UDP port: "))))
            elif action=="4": show(manager.network_view(mac,neighbors()))
            elif action=="5": show(connectivity(input("IPv4: ")))
            else: print("Unknown action")
        except (ValueError,KeyError,OSError,TypeError) as exc: print("ERROR:",exc)
        except __import__("subprocess").SubprocessError as exc: print("ERROR:",exc)
