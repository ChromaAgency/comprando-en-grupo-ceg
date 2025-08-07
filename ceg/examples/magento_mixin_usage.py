# -*- coding: utf-8 -*-

from odoo import models, api


class ExampleUsageMixin(models.TransientModel):
    """
    Ejemplo de cómo usar el mixin de envío de estados a Magento
    """
    _name = 'example.magento.usage'
    _description = 'Ejemplo de uso del mixin de Magento'

    @api.model
    def example_original_implementation(self):
        """
        Implementación original que se puede reemplazar con el mixin
        """
        # ANTES (código original que proporcionaste):
        # for rec in self:
        #     url, headers, data = rec._build_request_data(status)
        #     response = requests.post(url, headers=headers, data=data)
        #     if response.status_code != 200:
        #         _logger.error("Error al enviar el estado de la entrega a Magento")
        #         return
        pass

    @api.model 
    def example_new_implementation_single(self, record, status):
        """
        NUEVA implementación usando el mixin para un registro individual
        """
        # Ahora simplemente:
        success = record.send_status_to_magento(status)
        if not success:
            # El error ya se registra automáticamente en el log
            return False
        return True

    @api.model
    def example_new_implementation_batch(self, records, status):
        """
        NUEVA implementación usando el mixin para múltiples registros
        """
        # Para múltiples registros:
        result = records.batch_send_status_to_magento(status)
        
        if result['failed_count'] > 0:
            # Manejar registros fallidos si es necesario
            failed_records = result['failed']
            # Hacer algo con los registros que fallaron...
        
        return result

    @api.model
    def example_usage_in_real_method(self):
        """
        Ejemplos de uso real en diferentes contextos
        """
        # Ejemplo 1: Enviar estado desde una orden de venta
        sale_order = self.env['sale.order'].browse(1)
        if sale_order.exists():
            sale_order.send_status_to_magento('processing')

        # Ejemplo 2: Enviar estado cuando se confirma una entrega
        picking = self.env['stock.picking'].browse(1) 
        if picking.exists() and picking.state == 'done':
            picking.send_status_to_magento('shipped')

        # Ejemplo 3: Enviar estado en lote para múltiples facturas
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted')
        ])
        result = invoices.batch_send_status_to_magento('invoiced')
        
        # Ejemplo 4: Uso con manejo de errores personalizado
        try:
            success = sale_order.send_status_to_magento('complete')
            if success:
                # Hacer algo adicional si el envío fue exitoso
                pass
        except Exception as e:
            # Manejar errores específicos de la aplicación
            pass

    @api.model
    def example_custom_model_implementation(self):
        """
        Ejemplo de cómo implementar el mixin en un modelo personalizado
        """
        # Si tienes un modelo personalizado que necesita enviar estados a Magento:
        
        class CustomModel(models.Model):
            _inherit = ['custom.model', 'magento.status.sender.mixin']
            _name = 'custom.model'
            
            # Sobrescribir métodos según la estructura de tu modelo
            def _get_magento_instance(self):
                # Implementar lógica específica para obtener la instancia
                return self.related_sale_order.magento_instance_id
                
            def _get_magento_order_id(self):
                # Implementar lógica específica para obtener el order_id
                return self.related_sale_order.magento_order_id
                
            def _get_status_comment(self, status):
                # Personalizar el comentario
                return f"Custom model {self.name} updated to: {status}"
