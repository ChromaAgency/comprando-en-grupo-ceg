# API de Documentos Mexicanos - CEG

## Descripción

Esta API permite obtener documentos fiscales mexicanos (CFDI) asociados a órdenes de venta de Magento, incluyendo:
- Facturas CFDI
- Complementos de pago CFDI
- Documentos de traslado CFDI

## Autenticación

Todos los endpoints requieren autenticación mediante API Key del módulo `auth_api_key`.

### Métodos de autenticación:
1. **Header HTTP**: `X-API-Key: tu_api_key`
2. **Query parameter**: `?api_key=tu_api_key`

## Endpoints

### 1. Obtener URLs de documentos mexicanos

**Endpoint**: `GET /api/mexican-documents/{magento_order_ref}`

**Descripción**: Obtiene las URLs de todos los documentos CFDI asociados a una orden de venta de Magento.

**Parámetros**:
- `magento_order_ref` (string): Referencia de la orden en Magento. Se busca por `client_order_ref`, y si no se encuentra, por `name`, `origin` o coincidencia parcial.

**Headers**:
```
X-API-Key: tu_api_key
Content-Type: application/json
```

**Respuesta exitosa (200)**:
```json
{
  "success": true,
  "data": {
    "sale_order": {
      "id": 123,
      "name": "SO001",
      "magento_ref": "MGT-2024-001",
      "amount_total": 1500.00
    },
    "invoices": [
      {
        "name": "Factura anticipo INV/2024/001",
        "url": "https://tu-dominio.com/api/mexican-documents/pdf/invoice/456.pdf"
      }
    ],
    "payments": [
      {
        "name": "Complemento de pago PAY/2024/001",
        "url": "https://tu-dominio.com/api/mexican-documents/pdf/payment/789.pdf"
      }
    ],
    "transfer_documents": [
      {
        "name": "Factura de traslado PICK/2024/001",
        "url": "https://tu-dominio.com/api/mexican-documents/pdf/transfer/101112.pdf"
      }
    ]
  }
}
```

**Respuesta de error**:
```json
{
  "success": false,
  "error": "Mensaje de error",
  "code": 400
}
```

### 2. Descargar PDF de factura

**Endpoint**: `GET /api/mexican-documents/pdf/invoice/{invoice_id}.pdf`

**Descripción**: Descarga el PDF del CFDI de una factura específica.

**Parámetros**:
- `invoice_id` (int): ID de la factura en Odoo

**Autenticación**:
- Header: `X-API-Key: tu_api_key`
- Query param: `?api_key=tu_api_key`

**Respuesta exitosa (200)**:
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="NOMBRE_DEL_PDF.pdf"`
- Contenido: Datos binarios del PDF

**Errores**:
- 404 si la factura no existe o no tiene CFDI
- 401 si la API key es inválida

### 3. Descargar PDF de complemento de pago

**Endpoint**: `GET /api/mexican-documents/pdf/payment/{payment_id}.pdf`

**Descripción**: Descarga el PDF del CFDI de un complemento de pago específico.

**Parámetros**:
- `payment_id` (int): ID del pago en Odoo

**Autenticación**:
- Header: `X-API-Key: tu_api_key`
- Query param: `?api_key=tu_api_key`

**Respuesta exitosa (200)**:
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="NOMBRE_DEL_PDF.pdf"`
**Autenticación**:
- Header: `X-API-Key: tu_api_key`
- Query param: `?api_key=tu_api_key`

**Respuesta exitosa (200)**:
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="complemento_pago.pdf"`
- Contenido: Datos binarios del PDF

### 4. Descargar PDF de documento de traslado

**Endpoint**: `GET /api/mexican-documents/pdf/transfer/{picking_id}`

**Descripción**: Descarga el PDF del CFDI de un documento de traslado específico.

**Parámetros**:
- `picking_id` (int): ID del documento de traslado en Odoo

**Autenticación**:
- Header: `X-API-Key: tu_api_key`
- Query param: `?api_key=tu_api_key`

**Respuesta exitosa (200)**:
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="traslado.pdf"`
- Contenido: Datos binarios del PDF

## Códigos de estado

- **200**: Éxito
- **400**: Error en la solicitud (parámetros incorrectos)
- **401**: No autorizado (API key inválida o faltante)
- **404**: Recurso no encontrado
- **500**: Error interno del servidor

## Ejemplos de uso

### Ejemplo con cURL - Obtener URLs de documentos:

```bash
curl -X GET \
  "https://tu-dominio.com/api/mexican-documents/MGT-2024-001" \
  -H "X-API-Key: tu_api_key" \
  -H "Content-Type: application/json"
```

### Ejemplo con cURL - Descargar PDF de factura:

```bash
curl -X GET \
  "https://tu-dominio.com/api/mexican-documents/pdf/invoice/456?api_key=tu_api_key" \
  -o factura.pdf
```

### Ejemplo con Python:

```python
import requests

# Configuración
base_url = "https://tu-dominio.com"
api_key = "tu_api_key"
magento_ref = "MGT-2024-001"

# Obtener URLs de documentos
headers = {"X-API-Key": api_key}
response = requests.get(f"{base_url}/api/mexican-documents/{magento_ref}", headers=headers)

if response.status_code == 200:
    data = response.json()
    if data['success']:
        # Descargar PDFs
        for invoice in data['data']['invoices']:
            pdf_response = requests.get(invoice['pdf_url'], headers=headers)
            with open(f"factura_{invoice['id']}.pdf", "wb") as f:
                f.write(pdf_response.content)
```

## Notas importantes

1. **Configuración de API Keys**: Las API keys deben configurarse en el módulo `auth_api_key` de Odoo
2. **Permisos**: El usuario asociado a la API key debe tener permisos para acceder a los documentos
3. **Localización mexicana**: Requiere que los módulos de localización mexicana (`l10n_mx_edi`) estén instalados
4. **Documentos CFDI**: Solo retorna documentos que tengan CFDI válidos generados
5. **Referencias de Magento**: El sistema busca órdenes por `client_order_ref`, `name` u `origin`
