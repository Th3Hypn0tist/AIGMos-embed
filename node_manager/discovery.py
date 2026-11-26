"""Non-invasive Linux serial inventory. Does not open ports or reset devices."""
from pathlib import Path

def serial_ports(dev=Path("/dev"),sys=Path("/sys/class/tty")):
    result=[]
    for pattern in ("ttyUSB*","ttyACM*"):
        for port in sorted(dev.glob(pattern)):
            item={"port":str(port),"usb":{},"identified":False}
            device=sys/port.name/"device"
            if device.exists():
                resolved=device.resolve()
                for parent in (resolved,*resolved.parents):
                    if (parent/"idVendor").is_file() and (parent/"idProduct").is_file():
                        for key in ("idVendor","idProduct","manufacturer","product","serial"):
                            try: item["usb"][key]=(parent/key).read_text().strip()
                            except OSError: pass
                        break
            result.append(item)
    return result
