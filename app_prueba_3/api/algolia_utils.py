"""
Utilidades para Algolia - conversión de datos
"""
from ..utils import Cot, Certs, Fam, Client, completar_con_ceros
from typing import List, Dict
from datetime import datetime

def timestamp_to_date(timestamp) -> str:
    """Convierte un timestamp a fecha en formato YYYY-MM-DD"""
    if not timestamp:
        return ''
    
    try:
        # Si el timestamp es un string, convertirlo a int/float
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        
        # Si el timestamp está en milisegundos, convertir a segundos
        if timestamp > 1e12:  # Timestamp en milisegundos
            timestamp = timestamp / 1000
            
        # Convertir timestamp a datetime y formatear
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%d-%m-%Y')
    except (ValueError, TypeError, OSError):
        return str(timestamp) if timestamp else ''

def cot_to_algolia(cot: Cot) -> Dict:
    """Convierte un objeto Cot a formato Algolia"""
    return {
        "objectID": f"cot_{cot.num}_{cot.area}",
        "num": cot.num,
        "client": cot.client,
        "description": getattr(cot, 'description', ''),
        "issuedate": cot.issuedate,
        "issuedate_timestamp": getattr(cot, 'issuedate_timestamp', 0),
        "status": getattr(cot, 'status', ''),
        "area": cot.area,
        "type": "cotizacion"
    }

def certs_to_algolia(cert: Certs) -> Dict:
    """Convierte un objeto Certs a formato Algolia"""
    return {
        "objectID": f"cert_{cert.num}_{cert.year}_{cert.area}",
        "num": cert.num,
        "year": cert.year,
        "client": cert.client,
        "issuedate": cert.issuedate,
        "status": getattr(cert, 'status', ''),
        "area": cert.area,
        "type": "certificado"
    }

def fam_to_algolia(fam: Fam) -> Dict:
    """Convierte un objeto Fam a formato Algolia"""
    return {
        "objectID": f"fam_{fam.family}_{fam.area}",
        "family": fam.family,
        "razonsocial": fam.razonsocial,
        "expirationdate": fam.expirationdate,
        "description": getattr(fam, 'description', ''),
        "area": fam.area,
        "type": "familia"
    }

def client_to_algolia(client: Client) -> Dict:
    """Convierte un objeto Client a formato Algolia"""
    return {
        "objectID": f"client_{client.id}",
        "id": client.id,
        "razonsocial": client.razonsocial,
        "cuit": client.cuit,
        "direccion": client.direccion,
        "phone": client.phone,
        "email_cotizacion": client.email_cotizacion,
        "active_fams": client.active_fams,
        "condiciones": client.condiciones,
        "consultora": client.consultora,
        "type": "cliente"
    }

def algolia_to_cot(hit: Dict) -> Cot:
    """Convierte un resultado de Algolia a objeto Cot"""
    return Cot(
        id=hit.get('object_id', ''),
        num=completar_con_ceros(hit.get('number', ''),4),
        year=completar_con_ceros(hit.get('year', ''),2),
        client=hit.get('razonsocial', ''),
        client_id=hit.get('client', ''),
        consultora=hit.get('consultora', ''),
        issuedate=hit.get('issuedate', ''),
        issuedate_timestamp=hit.get('issuedate_timestamp', 0),
        status=hit.get('estado', ''),
        area=hit.get('area', ''),
        drive_file_id=hit.get('drive_file_id', ''),
        drive_file_id_name=hit.get('drive_file_id_name', ''),
        drive_aprobacion_id=hit.get('drive_aprobacion_id', ''),
        drive_aceptacion_id=hit.get('drive_aceptacion_id', ''),
        enviada_fecha=timestamp_to_date(hit.get('enviada_fecha', '')), 
        facturada_fecha=timestamp_to_date(hit.get('facturada_fecha', '')),
        facturar=hit.get('facturar', ''),
        nombre=hit.get('nombre', ''),
        email=hit.get('email', ''),
        ot=hit.get('ot', ''),
        rev=hit.get('rev', ''),
        resolucion=hit.get('resolucion', ''),
        cuenta=hit.get('cuenta', '')
    )

def algolia_to_certs(hit: Dict) -> Certs:
    """Convierte un resultado de Algolia a objeto Certs"""
    return Certs(
        id=hit.get('object_id', ''),
        num=hit.get('num', ''),
        client=hit.get('client', ''),
        description=hit.get('description', ''),
        issuedate=timestamp_to_date(hit.get('issuedate', '')),  # Convertir timestamp si es necesario
        issuedate_timestamp=hit.get('issuedate_timestamp', 0),
        status=hit.get('status', ''),
        area=hit.get('area', '')
    )
    

def algolia_to_fam(hit: Dict) -> Fam:
    """Convierte un resultado de Algolia a objeto Fam"""
    return Fam(
        id=hit.get('object_id', ''),
        family=hit.get('family', ''),
        razonsocial=hit.get('razonsocial', ''),
        expirationdate=timestamp_to_date(hit.get('expirationdate', '')),  # Convertir timestamp si es necesario
        description=hit.get('description', ''),
        area=hit.get('area', '')
    )

def algolia_to_client(hit: Dict) -> Client:
    """Convierte un resultado de Algolia a objeto Client"""
    return Client(
        id=hit.get('id', hit.get('objectID', '')),
        razonsocial=hit.get('razonsocial', ''),
        cuit=hit.get('cuit', ''),
        direccion=hit.get('direccion', ''),
        phone=hit.get('phone', ''),
        email_cotizacion=hit.get('email_cotizacion', ''),
        active_fams=hit.get('active_fams', 0),
        condiciones=hit.get('condiciones', ''),
        consultora=hit.get('consultora', ''),
    )
