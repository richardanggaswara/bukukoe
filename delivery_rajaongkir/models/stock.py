# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _track_rajaongkir(self):
        self.ensure_one()
        print ("\n tracking \n")
        try:
            vals = self.carrier_id.rajaongkir_get_tracking_value(self)
            print ("\n vals",vals)
            res = {
                'destination' : vals['summary']['destination'],
                'status' : vals['summary']['status'],
                'manifest' : [{
                    'code' : m['manifest_code'],
                    'description' : m['manifest_description'],
                    'date' : m['manifest_date'],
                    'time' : m['manifest_time'],
                    'city' : m['city_name'],
                } for m in vals['manifest']],
                'delivered' : vals['delivered'],
                'receiver_name' : vals['summary']['receiver_name']
            }
            print ("\n res",res)
        except:
            return False
        return res
