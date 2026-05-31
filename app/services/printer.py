import socket

def print_zpl(zpl: str, printer_ip: str):
    print("SIMULATED PRINT:")
    print("PRINTER:", printer_ip)
    print("ZPL:")
    print(zpl)
    return True