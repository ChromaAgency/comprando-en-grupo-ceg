# Magento Status Sender Mixin

Este mixin (`magento.status.sender.mixin`) permite enviar estados a Magento desde diferentes modelos de Odoo de forma estandarizada.

## Modelos que implementan el mixin

- `sale.order`
- `purchase.order` 
- `stock.picking`
- `account.move`

## Uso básico

### Enviar estado individual

```python
# Desde una orden de venta
sale_order = self.env['sale.order'].browse(order_id)
success = sale_order.send_status_to_magento('processing')

# Desde una factura
invoice = self.env['account.move'].browse(invoice_id)
success = invoice.send_status_to_magento('paid')

# Desde una entrega
picking = self.env['stock.picking'].browse(picking_id)
success = picking.send_status_to_magento('shipped')
```

### Enviar estado en lote

```python
# Para múltiples registros
orders = self.env['sale.order'].search([('state', '=', 'sale')])
result = orders.batch_send_status_to_magento('processing')

print(f"Exitosos: {result['success_count']}")
print(f"Fallidos: {result['failed_count']}")
```

## Métodos principales del mixin

### `send_status_to_magento(status)`
Envía un estado a Magento para el registro actual.

**Parámetros:**
- `status` (str): Estado a enviar a Magento

**Retorna:**
- `bool`: True si se envió correctamente, False en caso contrario

### `batch_send_status_to_magento(status)`
Envía estado a Magento para múltiples registros.

**Parámetros:**
- `status` (str): Estado a enviar a Magento

**Retorna:**
- `dict`: Diccionario con resultados:
  - `successful`: Registros enviados exitosamente
  - `failed`: Registros que fallaron
  - `success_count`: Número de envíos exitosos
  - `failed_count`: Número de envíos fallidos

## Métodos que pueden sobrescribirse

### `_get_magento_instance()`
Obtiene la instancia de Magento relacionada al registro.

### `_get_magento_order_id()` 
Obtiene el ID de orden de Magento para el registro.

### `_get_status_comment(status)`
Obtiene el comentario a enviar con el estado.

### `_get_headers(token)`
Obtiene los headers para la petición HTTP.

## Ejemplo de personalización

```python
class SaleOrder(models.Model):
    _inherit = ['sale.order', 'magento.status.sender.mixin']
    _name = 'sale.order'

    def _get_status_comment(self, status):
        """Personalizar comentario para órdenes de venta"""
        return f"Orden {self.name} actualizada a estado: {status}"
    
    def custom_send_status(self):
        """Método personalizado para enviar estado"""
        if self.state == 'sale':
            return self.send_status_to_magento('confirmed')
        return False
```

## Estados comunes de Magento

- `pending`: Pendiente
- `processing`: En proceso
- `shipped`: Enviado
- `complete`: Completado
- `canceled`: Cancelado
- `closed`: Cerrado
- `refunded`: Reembolsado

## Configuración requerida

Para que el mixin funcione correctamente, los registros deben tener:

1. **Instancia de Magento configurada**: El modelo debe tener acceso a un registro de `magento.instance` con:
   - `access_token`: Token de acceso válido
   - `magento_url`: URL base de Magento

2. **ID de orden de Magento**: El registro debe tener acceso al `magento_order_id` correspondiente

## Manejo de errores

El mixin incluye manejo de errores robusto:

- **Logging**: Se registran todos los errores en el log de Odoo
- **Excepciones controladas**: Se capturan y manejan las excepciones HTTP y de validación
- **Códigos de estado**: Se verifican los códigos de respuesta HTTP

## Integración automática

Algunos modelos pueden enviar estados automáticamente:

```python
class StockPicking(models.Model):
    _inherit = ['stock.picking', 'magento.status.sender.mixin']
    
    def action_done(self):
        """Enviar estado automáticamente al completar entrega"""
        result = super().action_done()
        
        for picking in self:
            if picking._get_magento_instance():
                picking.send_status_to_magento('complete')
        
        return result
```

## Troubleshooting

### Error: "No se encontró instancia de Magento"
- Verificar que el registro tenga configurada una instancia de Magento
- Revisar el método `_get_magento_instance()` del modelo

### Error: "Token de acceso no configurado"
- Verificar que la instancia de Magento tenga el campo `access_token` configurado
- Revisar permisos de API en Magento

### Error: "ID de orden de Magento no encontrado"
- Verificar que el registro tenga el `magento_order_id` configurado
- Revisar el método `_get_magento_order_id()` del modelo

### Error HTTP 401 (Unauthorized)
- Verificar que el token de acceso sea válido
- Verificar permisos de API en Magento

### Error HTTP 404 (Not Found)
- Verificar que la URL de Magento sea correcta
- Verificar que el endpoint `/rest/V1/orders/{order_id}/comments` esté disponible
