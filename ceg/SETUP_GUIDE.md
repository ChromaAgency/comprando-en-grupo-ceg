# Configuración de la API de Documentos Mexicanos

## Configuración inicial

### 1. Instalación de dependencias

Asegúrate de que los siguientes módulos estén instalados:
- `auth_api_key`
- `l10n_mx_edi` 
- `sale_purchase`

### 2. Configuración de API Key

1. Ve a **Configuración > Usuarios y Compañías > API Keys**
2. Crea una nueva API Key:
   - **Nombre**: API_DocumentosMexicanos_CEG
   - **Usuario**: Selecciona un usuario con permisos para ver facturas, pagos y entregas
   - **Clave**: Genera una clave segura (ej: `ceg_mx_docs_2024_secure_key_123`)

### 3. Configuración de permisos del usuario

El usuario asociado a la API Key debe tener los siguientes permisos:
- **Contabilidad**: Acceso de facturación/lectura
- **Ventas**: Acceso de lectura
- **Inventario**: Acceso de lectura
- **Localización Mexicana**: Acceso de lectura

### 4. Prueba de configuración

Prueba la configuración con este comando curl:

```bash
curl -X GET \
  "https://tu-dominio.com/api/mexican-documents/TEST-ORDER-001" \
  -H "X-API-Key: ceg_mx_docs_2024_secure_key_123" \
  -H "Content-Type: application/json"
```

## Casos de uso comunes

### Caso 1: Obtener todos los documentos de una orden
```python
import requests

def get_mexican_documents(magento_order_ref, api_key, base_url):
    headers = {"X-API-Key": api_key}
    response = requests.get(
        f"{base_url}/api/mexican-documents/{magento_order_ref}", 
        headers=headers
    )
    return response.json()

# Uso
docs = get_mexican_documents("MGT-2024-001", "tu_api_key", "https://tu-dominio.com")
print(docs)
```

### Caso 2: Descargar todos los PDFs de una orden
```python
import requests
import os

def download_all_pdfs(magento_order_ref, api_key, base_url, output_dir="downloads"):
    # Crear directorio si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener URLs de documentos
    headers = {"X-API-Key": api_key}
    response = requests.get(f"{base_url}/api/mexican-documents/{magento_order_ref}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            # Descargar facturas
            for invoice in data['data']['invoices']:
                pdf_response = requests.get(invoice['pdf_url'], headers=headers)
                filename = f"{output_dir}/factura_{invoice['name']}.pdf"
                with open(filename, "wb") as f:
                    f.write(pdf_response.content)
                print(f"Descargado: {filename}")
            
            # Descargar complementos de pago
            for payment in data['data']['payments']:
                pdf_response = requests.get(payment['pdf_url'], headers=headers)
                filename = f"{output_dir}/pago_{payment['name']}.pdf"
                with open(filename, "wb") as f:
                    f.write(pdf_response.content)
                print(f"Descargado: {filename}")
            
            # Descargar documentos de traslado
            for transfer in data['data']['transfer_documents']:
                pdf_response = requests.get(transfer['pdf_url'], headers=headers)
                filename = f"{output_dir}/traslado_{transfer['name']}.pdf"
                with open(filename, "wb") as f:
                    f.write(pdf_response.content)
                print(f"Descargado: {filename}")

# Uso
download_all_pdfs("MGT-2024-001", "tu_api_key", "https://tu-dominio.com")
```

### Caso 3: Integración con webhook de Magento
```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/webhook/magento/order_complete', methods=['POST'])
def handle_magento_order_complete():
    data = request.json
    magento_order_ref = data.get('order_ref')
    
    if magento_order_ref:
        # Obtener documentos mexicanos
        docs = get_mexican_documents(
            magento_order_ref, 
            "tu_api_key", 
            "https://tu-odoo-domain.com"
        )
        
        if docs['success']:
            # Procesar documentos (enviar por email, guardar en sistema, etc.)
            process_documents(docs['data'])
            return jsonify({"status": "success"})
    
    return jsonify({"status": "error"}), 400

def process_documents(documents):
    # Tu lógica de procesamiento aquí
    print(f"Procesando documentos para orden: {documents['sale_order']['name']}")
    for invoice in documents['invoices']:
        print(f"  - Factura: {invoice['name']} (UUID: {invoice['cfdi_uuid']})")
```

## Resolución de problemas

### Error 401 - No autorizado
- Verificar que la API Key sea correcta
- Verificar que la API Key esté activa
- Verificar que el usuario asociado tenga permisos

### Error 404 - Orden no encontrada
- Verificar que la referencia de Magento sea correcta
- Verificar que la orden exista en Odoo
- Verificar el mapeo de referencias (client_order_ref, name, origin)

### Error 404 - Documento CFDI no encontrado
- Verificar que los documentos CFDI hayan sido generados
- Verificar el estado de los documentos CFDI
- Verificar que los attachments PDF existan

### Error 500 - Error interno
- Revisar logs de Odoo
- Verificar que los módulos mexicanos estén instalados correctamente
- Verificar permisos de acceso a archivos
