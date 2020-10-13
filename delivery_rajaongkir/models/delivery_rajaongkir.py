# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .rajaongkir_request import RajaOngkirProvider
from odoo import models, fields, api, _

class RajaongkirAPI(models.Model):
    _name = 'delivery.carrier.rajaongkirapi'
    _description = "Rajaongkir API Key"
    
    name = fields.Char('API Key Name')
    api_key = fields.Char("API Key")
    
class RajaongkirURL(models.Model):
    _name = 'delivery.carrier.rajaongkirurl'
    _description = "Rajaongkir URL"
    
    name = fields.Char('URL Name')
    url = fields.Char("URL")

class ProviderRajaongkir(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('rajaongkir', "RajaOngkir")])

    rajaongkir_url = fields.Many2one('delivery.carrier.rajaongkirurl', 'URL')
    rajaongkir_apikey = fields.Many2one('delivery.carrier.rajaongkirapi', "API Key")
    rajaongkir_courier = fields.Selection([
        ('jne', 'JNE'),
        ('pos', 'POS'),
        ('tiki', 'TIKI'),
        ('jnt', 'J&T Express'),
        ('rpx', 'RPX'),
        ('esl', 'ESL'),
        ('pcp', 'PCP'),
        ('pandu', 'Pandu Logistic'),
        ('wahana', 'Wahana'),
        ('sicepat', 'Si Cepat'),
        ('pahala', 'Pahala'),
        ('cahaya', 'Cahaya'),
        ('sap', 'SAP'),
        ('jet', 'Jet'),
        ('indah', 'Indah'),
        ('dse', 'DSE'),
        ('slis', 'SLIS'),
        ('first', 'First Logistic'),
        ('ncs', 'NCS'),
	('ninja', 'Ninja Xpress'),
        ('star', 'Star')], default='jne', string='Courier')
    rajaongkir_service = fields.Char('Courier Services', help="Optional, leave blank")
    sp_active = fields.Boolean(string='Activate Special Origin')
    sp_city_id = fields.Many2one('res.country.city', string='Special City')
    sp_subdistrict_id = fields.Many2one('res.country.subdistrict', string='Special Subdistrict')

    def rate_shipment(self, order):
        if self.delivery_type == 'rajaongkir' :
            price = self.rajaongkir_get_shipping_price_from_so(order)
            if type(price) == list :
                price = price[0]
            return {
                'price': price,
                'carrier_price': price,
                'error_message': '',
                'warning_message': '',
                'success': True,
            }
        return super(ProviderRajaongkir, self).rate_shipment(order)

    def rajaongkir_get_shipping_price_from_so(self, orders):
        res = []
        srm = RajaOngkirProvider(self.rajaongkir_url.url, self.rajaongkir_apikey.api_key, self.rajaongkir_courier, self.sp_active, self.sp_city_id)
        for order in orders:
            srm.check_required_value(self, order.partner_shipping_id, order.warehouse_id.partner_id, order=order)
            price = srm.rate_request(order, self)
            if order.currency_id.name != 'IDR':
                quote_currency = self.env['res.currency'].search([('name', '=', 'IDR')], limit=1)
                price = quote_currency.compute(float(price), order.currency_id)
            res += [price]
        # print ("\n res",res)
        return res
    
    def rajaongkir_get_tracking_link(self, picking):
        return '/report/pdf/stock.report_deliveryslip/%s' % picking.id

    def rajaongkir_get_tracking_value(self, pickings):
        res = []
        srm = RajaOngkirProvider(self.rajaongkir_url.url, self.rajaongkir_apikey.api_key, self.rajaongkir_courier)
        # print("\n srm",srm)
        for picking in pickings:
            res = srm.track_request(picking.carrier_tracking_ref)
        return res
    
    def rajaongkir_sync_address(self):
        srm = RajaOngkirProvider(self.rajaongkir_url.url, self.rajaongkir_apikey.api_key, self.rajaongkir_courier)
        # print("\n srm",srm)
        country = self.env['res.country'].search([('code', '=', 'ID')])
        country_id = country.id
        state_query = []
        for state in srm._get_all_states():
            state_query.append("('%s', %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', 1, 1)" % (state['province'], state['province_id'], country_id))
        self._cr.execute("""
            INSERT INTO res_country_state AS d (name, code, country_id, create_date, write_date, create_uid, write_uid) values %s 
            ON CONFLICT(code, country_id) DO UPDATE SET 
                name = EXCLUDED.name, 
                write_date = NOW() AT TIME ZONE 'UTC', 
                write_uid=1 RETURNING name, id""" % ', '.join(state_query))
        self._cr.execute("""SELECT name, id FROM res_country_state WHERE country_id = %s""" % country_id)
        states = dict(self._cr.fetchall())
        city_query = []
        cities_query = srm._get_all_cities()
        for city in cities_query:
            city_query.append("('%s', %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', 1, 1)" % (city['type'] + " " + city['city_name'], city['city_id'], states[city['province']]))
                
        self._cr.execute("""
            INSERT INTO res_country_city AS d (name, rajaongkir_id, state_id, create_date, write_date, create_uid, write_uid) values %s 
            ON CONFLICT(rajaongkir_id) DO UPDATE SET 
                name = EXCLUDED.name, 
                state_id = EXCLUDED.state_id, 
                write_date = NOW() AT TIME ZONE 'UTC', 
                write_uid=1""" % ', '.join(city_query))
        
        self._cr.execute("""SELECT rajaongkir_id, city.id FROM res_country_city city LEFT JOIN res_country_state st ON st.id=city.state_id""")
        cities = self._cr.dictfetchall()
        # print("\n cities",cities)
        
        subdistrict_query = []
        for city in cities_query[:1]:
            for subdistrict in srm._get_subdistrict(city['city_id']):
                city_id = list(filter(lambda x: x['rajaongkir_id'] == int(subdistrict['city_id']), cities))[0]['id']
                # print("\n city_id",city_id)
                subdistrict_query.append("('%s', %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', 1, 1)" % (subdistrict['subdistrict_name'].replace("'", "''"), subdistrict['subdistrict_id'], city_id))
        
        self._cr.execute("""
            INSERT INTO res_country_subdistrict AS d (name, rajaongkir_id, city_id, create_date, write_date, create_uid, write_uid) values %s 
            ON CONFLICT(rajaongkir_id) DO UPDATE SET 
                name = EXCLUDED.name, 
                city_id = EXCLUDED.city_id, 
                write_date = NOW() AT TIME ZONE 'UTC', 
                write_uid=1""" % ', '.join(subdistrict_query))
        
        self._cr.execute("""DELETE FROM res_country_state WHERE country_id = %s AND not code ~ '^[0-9\.]+$' AND 
        id NOT IN (SELECT DISTINCT state_id FROM res_partner WHERE state_id IS NOT NULL)""" % country_id)
        
            
    @api.model
    def _rajaongkir_sync_address(self):
        rajaongkir_carrier = self.search([('delivery_type', '=', 'rajaongkir')], limit=1)
        if rajaongkir_carrier:
            rajaongkir_carrier.rajaongkir_sync_address()
        
