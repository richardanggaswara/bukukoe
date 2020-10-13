# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    subdistrict_id = fields.Many2one('res.country.subdistrict', 'Subdistrict')
    subdistrict = fields.Char('Subdistrict Char', related='subdistrict_id.name', store=True)
    city_id = fields.Many2one('res.country.city', 'City')
    city = fields.Char('City Char', related='city_id.name', store=True)
    
    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        res = super(ResPartner, self)._address_fields()
        res += 'subdistrict',
        return res


    def _display_address(self, without_company=False):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format
        address_format = self.country_id.address_format or \
              "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.commercial_company_name or '',
            'city': self.city or '',
            'subdistrict_name': self.subdistrict or '',
        }
        for field in self._address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

class ResCountryState(models.Model):
    _inherit = 'res.country.state'
    
    city_ids = fields.One2many('res.country.city', 'state_id', 'Cities')
    
class ResCountrySubdistrict(models.Model):
    _name = 'res.country.subdistrict'
    _description = 'Subdistrict'
    
    name = fields.Char('Subdistrict', required=True)
    city_id = fields.Many2one('res.country.city', 'City', required=True)
    rajaongkir_id = fields.Integer('Rajaongkir Ref', index=True)
    
    _sql_constraints = [
        ('unique_rajaongkir_subdistrict', 'unique(rajaongkir_id)', "Rajaongkir Ref Should be Unique!"),
    ]
    
class ResCountryCity(models.Model):
    _name = 'res.country.city'
    _description = 'City'
    
    name = fields.Char('City', required=True)
    state_id = fields.Many2one('res.country.state', 'State', required=True)
    rajaongkir_id = fields.Integer('Rajaongkir Ref', index=True)
    subdistrict_ids = fields.One2many('res.country.subdistrict', 'city_id', 'Subdistricts')

    _sql_constraints = [
        ('unique_rajaongkir_city', 'unique(rajaongkir_id)', "Rajaongkir Ref Should be Unique!"),
    ]
