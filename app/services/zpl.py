def generate_zpl(pallet):
    return f"""
^XA
^FO50,50^A0N,35,35^FD{pallet.barcode}^FS
^FO50,100^A0N,30,30^FDCustomer: {pallet.customer_name}^FS
^FO50,150^A0N,30,30^FD{pallet.material_type}^FS
^FO50,200^B3N,N,80,Y,N^FD{pallet.barcode}^FS
^XZ
"""