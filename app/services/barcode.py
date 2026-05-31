from datetime import datetime

def generate_pallet_code(pallet_id: int) -> str:
    year = datetime.now().year
    return f"PAL-{year}-{pallet_id:06d}"