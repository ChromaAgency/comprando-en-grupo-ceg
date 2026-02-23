from ast import literal_eval
from odoo.http import Controller, route, Response, request
from datetime import datetime
import logging
import urllib.parse
import tempfile
from odoo.tools import html2plaintext
import pandas as pd
import io
import json

_logger = logging.getLogger(__name__)
SEPARATOR = ';'

def _get_temp_file():
        return tempfile.TemporaryFile('w+', encoding='iso-8859-1')
def bool_to_empty_string(value):
    return f"{value}" if value else  ''

class ReportSaleOperationsTradeUnity(Controller):

    def _add_row_data_to_csv(self, file_content, row): 
        sale_line = row.move_id.sale_line_id
        sale_order = sale_line.order_id
        picking = row.move_id.picking_id
        shipping_address = picking.partner_id
        customer = sale_order.partner_id
        customer_commercial = customer.commercial_partner_id
        product = row.move_id.bom_line_id.product_id if row.move_id.bom_line_id else row.product_id 
        product_component = row.product_id if row.move_id.bom_line_id else ''
        # TODO: Add d365 reference 
        product_component_code = product_component.default_code if product_component else ''
        product_barcode =   product.barcode or ''
        move_qty = row.quantity
        box_qty = 1
        # box_qty = product.box_qty
        UNIDAD = 'UN'
        REFERENCIA = ''
        customer_phone = customer.phone if customer.phone else ''
        customer_mobile = customer.mobile if customer.mobile else ''
        delivery_mode = 'CL Directo'  
        OPERATION_NUMBER = ''
        #Referencia, Transportista, Direccion Transportista quedo vacio
        data = [sale_order.name, customer_commercial.id, customer.display_name, customer_phone,customer_mobile, product.ceg_code or '', product_component.ceg_code or '',
                   product.name, UNIDAD, move_qty*box_qty, move_qty,move_qty*product.volume, REFERENCIA,delivery_mode,shipping_address.contact_address_complete, shipping_address.street, 
                   shipping_address.street2, shipping_address.city, shipping_address.zip, shipping_address.state_id.name, shipping_address.country_id.name,
                     OPERATION_NUMBER,  picking.name, product.default_code, product_component_code, product_barcode]
       
        data = [bool_to_empty_string(v) for v in data ]
        file_content.write(SEPARATOR.join(data))
        file_content.write('\n')

    def _add_rows_data_to_csv(self,file_content, pickings):
        for move in pickings.move_line_ids:
            self._add_row_data_to_csv(file_content, move)

    def _add_header_to_csv(self, file_content):
        headers = ['Pedido de ventas', 'Cuenta de cliente', 'Nombre', 'Teléfono del cliente','Teléfono móvil del cliente', 'Código de artículo',	'Código de artículo componente',
               'Nombre del producto','Unidad','Cantidad','Bultos','Volumen','Referencia','Modo de entrega','Dirección', 'Nombre de calle', 'Calle 2', 'Ciudad', 'Código Postal', 'Estado', 'País',
               'Número de operación', 'Número de operación Odoo', 'SKU', 'SKU Componente', 'Código de barras'] 
        file_content.write(SEPARATOR.join(headers))
        file_content.write('\n')


    @route(['/ceg/download_picking_list/<picking_ids>'], type="http", auth="user")
    def download_sales_as_csv(self, picking_ids=False):
        """Get a sale picking in the format Pedidos formula needs it."""
        # ? Check and respond accordingly to possible user errors
        if not picking_ids:
            return Response('ERROR: No se seleccionaron pickings.', status=500)
        picking_ids = list(map(lambda _id:int(_id), picking_ids.split(',')))
        if not isinstance(picking_ids, list):
            return Response('ERROR: Las pickings no fueron seleccionados correctamente.', status=500)

        pickings = request.env['stock.picking'].browse(picking_ids) 
        
        file_content = _get_temp_file()
        self._add_header_to_csv(file_content)
        self._add_rows_data_to_csv(file_content, pickings)
        file_content.seek(0)
        df = pd.read_csv(file_content, sep=';', encoding='iso-8859-1')
        output = io.BytesIO()
        with pd.ExcelWriter(output) as writer:
            df.to_excel(writer, index=False)
        
        output.seek(0)
        now = datetime.now()
        return Response(output.read(), headers={
            'Content-Disposition':'attachment; filename="%s_%s_%s_picking_list_%s.csv"' % (now.year, now.month, now.day, int(now.timestamp()) ) })
