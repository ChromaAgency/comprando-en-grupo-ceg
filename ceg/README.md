# Módulo CEG - Wizard de Anticipos de Compra a Venta

## Descripción

Este módulo extiende la funcionalidad de Odoo 18.0 para permitir crear anticipos de órdenes de venta directamente desde las órdenes de compra relacionadas.

## Funcionalidad

### Wizard de Anticipos
- **Ubicación**: Disponible en las órdenes de compra confirmadas (estados 'purchase' y 'done')
- **Función**: Crear anticipos del 100% del total de cada orden de venta relacionada
- **Acceso**: Botón "Create Sale Advance Payment" en la vista de formulario de la orden de compra

### Características principales:
1. **Conexión automática**: El wizard identifica automáticamente las órdenes de venta relacionadas a través de las líneas de compra
2. **Anticipos completos**: Crea anticipos por el 100% del total de cada orden de venta
3. **Trazabilidad**: Registra mensajes en las órdenes de compra indicando los anticipos creados
4. **Seguridad**: Solo disponible para usuarios con permisos de compra

## Dependencias

- `purchase`: Módulo base de compras
- `sale`: Módulo base de ventas  
- `sale_purchase`: Conexión entre ventas y compras
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
└── __manifest__.py
```

## Notas técnicas

- El wizard utiliza el wizard estándar de Odoo `sale.advance.payment.inv` internamente
- Se basa en la relación `sale_line_id` en las líneas de orden de compra (proporcionada por `sale_purchase`)
- Filtra automáticamente solo las órdenes de venta confirmadas
- Maneja múltiples órdenes de venta por orden de compra
