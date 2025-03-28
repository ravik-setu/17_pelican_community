from odoo import fields, models


class UserRestrictionWarning(models.TransientModel):

    _name = 'user.restriction.warning'
    _description = 'User Restriction'

    warning_msg = fields.Html()
