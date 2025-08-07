# Módulo CEG - Extensiones Personalizadas

## Descripción

Este módulo extiende la funcionalidad de Odoo 18.0 con características específicas para CEG, incluyendo:

1. **Wizard de Anticipos de Compra a Venta**
2. **API de Documentos Mexicanos CFDI**

## Funcionalidades

### 1. Wizard de Anticipos
- **Ubicación**: Disponible en las órdenes de compra confirmadas (estados 'purchase' y 'done')
- **Función**: Crear anticipos del 100% del total de cada orden de venta relacionada
- **Acceso**: Botón "Create Sale Advance Payment" en la vista de formulario de la orden de compra

#### Características principales:
- **Conexión automática**: El wizard identifica automáticamente las órdenes de venta relacionadas a través de las líneas de compra
- **Anticipos completos**: Crea anticipos por el 100% del total de cada orden de venta
- **Trazabilidad**: Registra mensajes en las órdenes de compra indicando los anticipos creados
- **Seguridad**: Solo disponible para usuarios con permisos de compra

### 2. API de Documentos Mexicanos
- **Función**: Proporciona acceso a documentos fiscales mexicanos (CFDI) vía API REST
- **Autenticación**: Utiliza API Keys del módulo `auth_api_key`
- **Documentos soportados**: 
  - Facturas CFDI
  - Complementos de pago CFDI
  - Documentos de traslado CFDI

#### Endpoints disponibles:
- `GET /api/mexican-documents/{magento_order_ref}` - Obtener URLs de documentos
- `GET /api/mexican-documents/pdf/invoice/{invoice_id}` - Descargar PDF de factura
- `GET /api/mexican-documents/pdf/payment/{payment_id}` - Descargar PDF de complemento de pago
- `GET /api/mexican-documents/pdf/transfer/{picking_id}` - Descargar PDF de documento de traslado

*Ver [API_DOCS.md](API_DOCS.md) para documentación completa de la API.*

## Dependencias

- `purchase`: Módulo base de compras
- `sale`: Módulo base de ventas  
- `sale_purchase`: Conexión entre ventas y compras
- `auth_api_key`: Autenticación por API Key
- `l10n_mx_edi`: Localización mexicana EDI/CFDI
- `whatsapp`: Dependencia existente del módulo
- `odoo_magento2_ept`: Dependencia existente del módulo

## Instalación

1. Asegurar que todas las dependencias estén instaladas
2. Instalar o actualizar el módulo CEG
3. El wizard estará disponible automáticamente en las órdenes de compra

## Uso

1. Ir a una orden de compra en estado 'Confirmada' o 'Hecho'
2. Hacer clic en el botón "Create Sale Advance Payment"
3. Revisar la información de las órdenes de venta relacionadas
4. Hacer clic en "Create Advance Payments"
5. El sistema creará las facturas de anticipo correspondientes

## Archivos del módulo

```
ceg/
├── controllers/
│   ├── __init__.py
│   └── mexican_documents_controller.py  # API de documentos mexicanos
├── models/
│   ├── __init__.py
│   ├── discuss_channel.py
│   ├── whatsapp_account.py
│   └── purchase_order.py          # Extensión de purchase.order
├── wizard/
│   ├── __init__.py
│   └── purchase_advance_payment_inv.py  # Wizard principal
├── views/
│   ├── purchase_advance_payment_inv_views.xml  # Vista del wizard
│   └── purchase_order_views.xml    # Extensión de la vista de orden de compra
├── security/
│   └── ir.model.access.csv         # Permisos de acceso
├── __init__.py
├── __manifest__.py
├── README.md
└── API_DOCS.md                     # Documentación de la API
```

## Notas técnicas

### Wizard de Anticipos:
- El wizard utiliza el wizard estándar de Odoo `sale.advance.payment.inv` internamente
- Se basa en la relación `sale_line_id` en las líneas de orden de compra (proporcionada por `sale_purchase`)
- Filtra automáticamente solo las órdenes de venta confirmadas
- Maneja múltiples órdenes de venta por orden de compra

### API de Documentos Mexicanos:
- Utiliza autenticación por API Key del módulo `auth_api_key`
- Busca órdenes de venta por referencia de Magento (`client_order_ref`, `name`, `origin`)
- Solo retorna documentos con CFDI válidos
- Soporta documentos de facturas, pagos y traslados
- Maneja errores HTTP estándar (401, 404, 500)
