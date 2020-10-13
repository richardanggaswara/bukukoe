# -*- coding: utf-8 -*-
from odoo import _
from odoo.exceptions import ValidationError
import requests, json

class RajaOngkirProvider(object):

    def __init__(self, url, key, courier, activated=False, SpCity=False):
        self.url = url
        self.key = key
        self.courier = courier
        self.active = activated
        self.sp_city = SpCity
        
    def _get_all_cities(self):
        return self._get_all_address('city')['rajaongkir']['results']
    
    def _get_all_states(self):
        return self._get_all_address('province')['rajaongkir']['results']
    
    def _get_subdistrict(self, city_id):
        return self._get_all_address(address_type='subdistrict', data={'city' : city_id})['rajaongkir']['results']
    
    def _get_all_address(self, address_type='city', data={}):
        try:
            req = requests.get(self.url + address_type, headers={'key' : self.key, 'Accept': 'application/json'}, params=data)
            response = json.loads(req.content.decode('utf-8'))
        except :
            raise ValidationError("RajaOngkir Server not found. Check your connectivity.")
        try:
            response['rajaongkir']['results']
        except:
            try:
                if response['rajaongkir']['status']['code'] != 200:
                    raise ValidationError(_(response['rajaongkir']['status']['description']))
            except:
                raise ValidationError(_('Unable to get response'))
        return response
        
    def _convert_weight(self, weight):
        # Weight in odoo is Kg, so we convert the way rajaongkir.com request (In Gram)
        return int(weight * 1000)

    def rate_request(self, order, carrier):
        price = False
        header = {
            'Accept': 'application/json',
            'content-type': "application/x-www-form-urlencoded"
        }
        payload = self._get_rate_payload(order)
        response = self._send_request(header, payload)
        # print ("\n response",response)
        try:
            if response['rajaongkir']['status']['code'] != 200:
                raise ValidationError(_(response['rajaongkir']['status']['description']))
            elif response['rajaongkir']['status']['code'] == 200:
                found = False
                available_service = []
                for result in response['rajaongkir']['results']:
                    if result['code'].lower() == carrier.rajaongkir_courier.lower():
                        for costs in result['costs']:
                            available_service.append(costs['service'])
                            if (carrier.rajaongkir_service and costs['service'].lower() == carrier.rajaongkir_service.lower()) or \
                                not carrier.rajaongkir_service and costs['cost']:
                                    price = costs['cost'][0]['value']
                                    found = True
                                    break
                if not found:
                    raise ValidationError(_("No Service Available!" + ((' Available Service ' + ', '.join(available_service)) if available_service else '')))
        except Exception as e:
            raise ValidationError(e)
        except:
            raise ValidationError(_('Unable to get response!, response = %s' % response))
        # print ("\n price",price)
        return price
    
    def _get_rate_payload(self, order):
        total_weight = self._convert_weight(sum([(line.product_id.weight * line.product_qty) for line in order.order_line]))
        res = {
            'key' : self.key,
            'originType' : 'city',
            'destinationType' : 'city',
            'origin': order.warehouse_id.partner_id.city_id.rajaongkir_id,
            'destination': order.partner_shipping_id.city_id.rajaongkir_id,
            'weight': total_weight,
        }
        if self.courier:
            res['courier'] = self.courier.lower()
            if self.courier in ['wahana', 'cahaya', 'sap']:
                res['destinationType'] = 'subdistrict'
                res['destination'] = order.partner_shipping_id.subdistrict_id.rajaongkir_id
                if self.active:
                    res['originType'] = 'city'
                    res['origin'] = self.sp_city.rajaongkir_id
        return res

    def _send_request(self, header, payload):
        try:
            req = requests.post(self.url + 'cost', data=payload, headers=header)
            # print("\n req",req)
            response = json.loads(req.content.decode('utf-8'))
            # print("\n response _send_request",response)
        except :
            raise ValidationError("RajaOngkir Server not found. Check your connectivity.")
        return response
    
    def track_request(self, ref):
        header = {
            'key': self.key,
            'content-type': "application/x-www-form-urlencoded"
        }
        payload = {
            'waybill' : ref,
            'courier' : self.courier
        }
        try:
            req = requests.post(self.url + 'waybill', headers=header, data=payload)
            response = json.loads(req.content.decode('utf-8'))
            # print("\n ref track_request",ref)
            # print("\n response track_request",response)
        except:
            raise ValidationError("RajaOngkir Server not found. Check your connectivity.")
        try:
            response['rajaongkir']['results']
        except:
            try:
                if response['rajaongkir']['status']['code'] != 200:
                    raise ValidationError(_(response['rajaongkir']['status']['description']))
            except:
                raise ValidationError(_('Unable to get response'))
        return response['rajaongkir']['result']

    def check_required_value(self, carrier, recipient, shipper, order=False):
        carrier = carrier.sudo()
        if not carrier.rajaongkir_courier:
            raise ValidationError(_("RajaOngkir Courier is not defined"))
        
        recipient_required_field = ['city_id', 'state_id']
        if carrier.rajaongkir_courier in ['wahana', 'cahaya', 'sap']:
            recipient_required_field.append('subdistrict_id')
        if not recipient.street and not recipient.street2:
            recipient_required_field.append('street')
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            raise ValidationError(_("The address of the custommer is missing or wrong (Missing field(s) :\n %s)") % ", ".join(res).replace("_id", ""))

        shipper_required_field = ['city_id', 'state_id']
        if not shipper.street and not shipper.street2:
            shipper_required_field.append('street')
        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            raise ValidationError(_("The address of your company warehouse is missing or wrong (Missing field(s) :\n %s)") % ", ".join(res).replace("_id", ""))

        if order:
            if not order.order_line:
                raise ValidationError(_("Please provide at least one item to ship."))
            elif order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type == 'stockable'):
            # elif order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and not line.product_id.type in ['service', 'digital']):
                raise ValidationError(_('The estimated price cannot be computed because the weight of your product is missing.'))
        return True
