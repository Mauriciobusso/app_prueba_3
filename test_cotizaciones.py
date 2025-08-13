from pprint import pprint
from app_prueba_3.api.cotizacion_extractor import get_cotizacion_full_data_from_drive

ids = [
    '1hmwwh-Dgal7CT5xUfzZTwj2UnKdtDgrj',
    '1i2Cwc40LdcxIUsmy29O1Sd8FpwL77deU',
    '1BRT7bjFH4S6HPP51ocJ-GdLD43R4K1jc'
]

for file_id in ids:
    print(f'\n--- Resultados para file_id: {file_id} ---')
    data = get_cotizacion_full_data_from_drive(file_id)
    pprint(data)
