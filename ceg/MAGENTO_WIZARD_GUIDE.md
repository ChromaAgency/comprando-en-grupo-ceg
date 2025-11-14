# Estados de Magento y Wizard - Guía de Usuario

## Resumen de Funcionalidades

Se han agregado campos de estado de Magento y un wizard para gestionar el envío de estados a los siguientes modelos:

- **Sale Order** (`sale.order`)
- **Purchase Order** (`purchase.order`) 
- **Stock Picking** (`stock.picking`)
- **Account Move** (`account.move`)

## Estados de Magento por Modelo

### Sale Order (Órdenes de Venta)
- `impo_local_shipping`: Entrega Local
- `delivered`: Entregado
- `impo_anticipo_complete`: Anticipo Completado
- `processing`: En Proceso
- `complete`: Completado
- `canceled`: Cancelado

### Purchase Order (Órdenes de Compra)
- `impo_in_prod`: En Producción
- `impo_shipped`: Enviado
- `impo_ua_clearence`: En Aduanas
- `in_prod`: En Producción
- `in_transit`: En Tránsito
- `in_customs`: En Aduanas

### Stock Picking (Transferencias)
- `impo_local_shipping`: Entrega Local
- `shipped`: Enviado
- `delivered`: Entregado
- `in_transit`: En Tránsito
- `complete`: Completado

### Account Move (Facturas/Asientos)
- `impo_anticipo_complete`: Anticipo Completado
- `paid`: Pagado
- `processing`: En Proceso
- `complete`: Completado

## Visualización en Vistas

### Status Bar
En las vistas de formulario, el campo `magento_state` aparece como una barra de estado clickeable en el header:

```xml
<field name="magento_state" widget="statusbar" clickable="True"/>
```

### Listas/Tree Views
En las vistas de lista, el campo aparece como una columna opcional después del campo `state`:

```xml
<field name="magento_state" optional="show"/>
```

## Wizard de Estados de Magento

### Acceso al Wizard
El wizard se puede acceder desde:

1. **Menú contextual**: Seleccionar registros → Acción → "Actualizar Estado de Magento"
2. **Botón en formulario**: (si se agrega en futuras versiones)

### Uso del Wizard

1. **Seleccionar registros**: Marcar uno o varios registros en la vista de lista
2. **Abrir wizard**: Acciones → "Actualizar Estado de Magento"
3. **Seleccionar estado**: Elegir el estado deseado de la lista (específica por modelo)
4. **Enviar**: Click en "Enviar Estado"

El wizard:
- ✅ Valida que los registros tengan instancia de Magento configurada
- ✅ Envía el estado a Magento vía API
- ✅ Actualiza el campo `magento_state` en los registros
- ✅ Muestra resultado del envío (exitosos/fallidos)

## Envío Automático

### Sale Order
- **Al confirmar**: Se envía automáticamente estado `impo_local_shipping`

### Purchase Order  
- **Al cambiar `magento_state`**: Se envía automáticamente el nuevo estado

### Stock Picking
- **Al marcar como hecho**: 
  - Salidas → `delivered`
  - Transferencias internas → `in_transit`

### Account Move
- **Al cambiar estado de pago**:
  - `paid` → `impo_anticipo_complete`
  - `in_payment` → `processing`
  - `partial` → `processing`

## Métodos de Programación

### Envío Manual
```python
# Envío individual
record.send_status_to_magento('delivered')

# Envío en lote
records.batch_send_status_to_magento('processing')

# Método específico del modelo
record.action_send_magento_status()
```

### Personalización de Estados
```python
# Agregar nuevos estados en el wizard
def _get_magento_state_selection(self):
    if self.env.context.get('active_model') == 'mi.modelo':
        return [
            ('nuevo_estado', 'Nuevo Estado'),
            # ... más estados
        ]
```

## Configuración Requerida

Para que funcione correctamente:

1. **Instancia de Magento**: Los registros deben tener acceso a `magento.instance`
2. **Token de acceso**: La instancia debe tener `access_token` configurado
3. **URL de Magento**: La instancia debe tener `magento_url` configurado
4. **ID de orden**: Los registros deben tener `magento_order_id`

## Permisos de Seguridad

El wizard requiere:
- `base.group_user`: Usuarios básicos
- `base.group_system`: Administradores del sistema

## Troubleshooting

### El wizard no aparece
- Verificar que se hayan seleccionado registros
- Verificar permisos de usuario

### Error "No se encontró instancia de Magento"
- Verificar configuración de `magento_instance_id` en el registro
- Verificar relación con orden de venta (para picking/invoice)

### Error de envío HTTP
- Verificar `access_token` en instancia de Magento
- Verificar `magento_url` en instancia de Magento
- Verificar conectividad de red

### Estado no se actualiza
- Verificar que el registro tenga el campo `magento_state`
- Verificar que el método `write` no esté siendo bloqueado

## Logs y Debugging

Los errores se registran en:
```python
_logger.error("Error al enviar estado a Magento: %s", error)
```

Para debugging, revisar logs de Odoo con nivel DEBUG o ERROR.
