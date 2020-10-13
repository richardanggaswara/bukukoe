# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import simplejson


class WebsiteSaleDeliveryRajaongkir(WebsiteSale):

    def _get_mandatory_billing_fields(self):
        res = super(WebsiteSaleDeliveryRajaongkir, self)._get_mandatory_billing_fields()
        res.remove('city')
        return res
    
    def _get_mandatory_shipping_fields(self):
        res = super(WebsiteSaleDeliveryRajaongkir, self)._get_mandatory_shipping_fields()
        res.append("subdistrict_id")
        res.append("city_id")
        res.remove('city')
        return res

    def values_postprocess(self, order, mode, values, errors, error_msg):
        new_values, errors, error_msg = super(WebsiteSaleDeliveryRajaongkir, self).values_postprocess(order, mode, values, errors, error_msg)
        new_values['subdistrict_id'] = values['subdistrict_id'] if 'subdistrict_id' in values else None
        new_values['city_id'] = values['city_id'] if 'city_id' in values  else None
        return new_values, errors, error_msg
        
    @http.route(['/shop/address'], type='http', methods=['GET', 'POST'], auth="public", website=True)
    def address(self, **kw):
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order(force_create=1)
        mode = (False, False)
        def_country_id = order.partner_id.country_id
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            mode = ('new', 'billing')
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                        mode = ('edit', 'billing')
                else:
                    shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                if mode:
                    values = Partner.browse(partner_id)
            elif partner_id == -1:
                mode = ('new', 'shipping')
            else:  # no mode - refresh without post?
                return request.redirect('/shop/checkout')

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)

            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                partner_id = self._checkout_form_save(mode, post, kw)

                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.onchange_partner_id()
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id

                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]
                if not errors:
                    return request.redirect(kw.get('callback') or '/shop/checkout')

        country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(int(values['country_id']))
        country = country and country.exists() or def_country_id
        
        render_values = {
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'country': country,
            'countries': country.get_website_sale_countries(mode=mode[1]),
            "states": country.get_website_sale_states(mode=mode[1]),
            "cities": request.env['res.country.city'].sudo().search([]),
            "subdistricts": request.env['res.country.subdistrict'].sudo().search([]),
            'error': errors,
            'callback': kw.get('callback'),
            'website_sale_order': order,
        }
        return request.render("website_sale.address", render_values)
        

    @http.route('/selectize/countries', type='http', auth="public", website=True)
    def countries(self, **kw):
        res = request.env['res.country'].sudo().search([('name','ilike',kw.get('q'))])
        countries = [{'id': str(r.id), 'name': r.name} for r in res]
        return simplejson.dumps(countries)

    @http.route('/selectize/states/<int:country_id>', type='http', auth="public", website=True)
    def states(self, country_id=None, **kw):
        res = request.env['res.country.state'].sudo().search([('country_id.id','=',country_id)])
        states = [{'id': str(r.id), 'name': r.name} for r in res]
        return simplejson.dumps(states)

    @http.route('/selectize/cities/<int:state_id>', type='http', auth="public", website=True)
    def cities(self, state_id=None, **kw):
        res = request.env['res.country.city'].sudo().search([('state_id','=',state_id)])
        cities = [{'id': str(r.id), 'name': r.name} for r in res]
        return simplejson.dumps(cities)

    @http.route('/selectize/subdistricts/<int:city_id>', type='http', auth="public", website=True)
    def subdistricts(self, city_id=None, **kw):
        res = request.env['res.country.subdistrict'].sudo().search([('city_id','=',city_id)])
        subdistricts = [{'id': str(r.id), 'name': r.name} for r in res]
        return simplejson.dumps(subdistricts)

 