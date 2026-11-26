"""Explicit bootloader identification through an external esptool 4.x CLI.

Identification can reset the selected device, but never writes or erases flash.
"""
import re
import shutil
import subprocess
from .registry import mac_id

def toolchain():
    return {"esptool":shutil.which("esptool.py") or shutil.which("esptool"),
            "host_cc":shutil.which("cc"),
            "esp8266_cc":shutil.which("xtensa-lx106-elf-gcc"),
            "esp32c6_cc":shutil.which("riscv32-esp-elf-gcc")}

def parse_identity(output):
    chip=re.search(r"(?:Chip is|Chip type:)\s*(ESP8266(?:EX)?|ESP8285|ESP32-C6|ESP32-S3)\b",output,re.I)
    mac=re.search(r"^\s*MAC:\s*([0-9a-f:]{17})\s*$",output,re.I|re.M)
    flash=re.search(r"Detected flash size:\s*(\d+)\s*(KB|MB)\b",output,re.I)
    if not (chip and mac and flash):
        raise ValueError("incomplete or unsupported bootloader identity")
    platform=chip[1].upper()
    if platform in ("ESP8266EX","ESP8285"): platform="ESP8266"
    size=int(flash[1])*(1024 if flash[2].upper()=="KB" else 1048576)
    if size<=0: raise ValueError("invalid flash size")
    return {"platform":platform,"mac":mac_id(mac[1]),"flash_bytes":size}

def identify(port,executable=None,runner=subprocess.run):
    executable=executable or toolchain()["esptool"]
    if not executable: raise ValueError("esptool 4.x not found")
    # flash_id prints chip, MAC and detected flash size in one connection.
    args=[executable,"--chip","auto","--port",str(port),"--baud","115200",
          "--no-stub","--after","hard_reset","flash_id"]
    try:
        result=runner(args,capture_output=True,text=True,timeout=30,check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("bootloader identification timed out") from exc
    if result.returncode:
        raise ValueError("bootloader identification failed: "+result.stderr.strip()[-500:])
    identity=parse_identity(result.stdout)
    identity["port"]=str(port)
    return identity
