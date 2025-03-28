from odoo import fields, models, api, _
from datetime import date, datetime, timedelta
import calendar as cal
import math
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
MAINTENANCE_CYCLE = 30


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    is_hourly_maintenance = fields.Boolean(string='Allow Auto Hourly Maintenance')
    is_daily_maintenance = fields.Boolean(string='Allow Auto Daily Maintenance')
    is_weekly_maintenance = fields.Boolean(string='Allow Auto Weekly Maintenance')
    is_monthly_maintenance = fields.Boolean(string='Allow Auto Monthly Maintenance')
    is_quarterly_maintenance = fields.Boolean(string='Allow Auto Quarterly Maintenance')
    is_half_yearly_maintenance = fields.Boolean(string='Allow Auto Half Yearly Maintenance')
    is_yearly_maintenance = fields.Boolean(string='Allow Auto Yearly Maintenance')
    maintenance_date = fields.Date(default=date.today())
    hourly_maintenance_hours = fields.Integer(string='Hourly Maintenance Hours')
    auto_maintenance_type = fields.Char(compute='_compute_auto_maintenance_type')
    hours_in_per_day = fields.Integer(string='Hours In Per Day')

    @api.depends('name')
    def _compute_auto_maintenance_type(self):
        IrDefault = self.env['ir.default'].sudo()
        for rec in self:
            auto_maintenance_request_type = IrDefault.get(model_name='res.config.settings',
                                                          field_name='auto_maintenance_request_type',
                                                          company_id=self.env.company.id)
            rec.auto_maintenance_type = auto_maintenance_request_type and auto_maintenance_request_type or 'dayswise'

    @api.constrains('maintenance_date')
    def _constrains_maintenance_date(self):
        """
        Author: Gaurav Vipani | Date: 26th July, 2023
        Purpose: For start is not allow less then current date
        """
        for rec in self:
            if rec.maintenance_date < date.today():
                raise UserError(_("Maintenance date is not less then current date."))

    def _cron_create_equipment_maintenance_request(self):
        """
        Author: Gaurav Vipani | Date: 26th July, 2023
        Purpose: Auto create equipment maintenance request based on equipment set maintenance frequancy.
        """
        if not self.is_holiday(date.today()) and self.is_weekday(date.today()):
            team_id = self.env["maintenance.team"].search(['|', ('company_id', '=', self.env.company.id),
                                                           ('company_id', '=', False)], limit=1)
            IrDefault = self.env['ir.default'].sudo()
            domain = [('maintenance_date', '!=', False)]
            auto_maintenance_request_type = IrDefault.get(model_name='res.config.settings',
                                                          field_name='auto_maintenance_request_type',
                                                          company_id=self.env.company.id) or 'dayswise'
            if auto_maintenance_request_type == 'hourwise':
                domain += [('is_hourly_maintenance', '!=', False)]
            else:
                domain += ['|', '|', '|', '|', '|', ('is_monthly_maintenance', '!=', False),
                           ('is_quarterly_maintenance', '!=', False), ('is_half_yearly_maintenance', '!=', False),
                           ('is_yearly_maintenance', '!=', False), ('is_weekly_maintenance', '!=', False),
                           ('is_daily_maintenance', '!=', False)]
            equipment_ids = self.search(domain)
            for equipment in equipment_ids:
                maintenance_date = equipment.maintenance_date
                if maintenance_date and maintenance_date <= date.today():
                    if equipment.is_yearly_maintenance:
                        equipment._create_auto_maintenance_request(team_id=team_id,
                                                                   preventive_maintenance_frequency='yearly',
                                                                   maintenance_cycle_days=MAINTENANCE_CYCLE * 12)
                    if equipment.is_half_yearly_maintenance:
                        equipment._create_auto_maintenance_request(team_id=team_id,
                                                                   preventive_maintenance_frequency='half_yearly',
                                                                   maintenance_cycle_days=MAINTENANCE_CYCLE * 6)
                    if equipment.is_quarterly_maintenance:
                        equipment._create_auto_maintenance_request(team_id=team_id,
                                                                   preventive_maintenance_frequency='quarterly',
                                                                   maintenance_cycle_days=MAINTENANCE_CYCLE * 3)
                    if equipment.is_monthly_maintenance:
                        equipment._create_auto_maintenance_request(team_id=team_id,
                                                                   preventive_maintenance_frequency='monthly',
                                                                   maintenance_cycle_days=MAINTENANCE_CYCLE)
                    if equipment.is_weekly_maintenance:
                        equipment._create_auto_maintenance_request(team_id=team_id,
                                                                   preventive_maintenance_frequency='weekly',
                                                                   maintenance_cycle_days=MAINTENANCE_CYCLE // 4)
                    if equipment.is_hourly_maintenance:
                        equipment._create_auto_maintenance_request(team_id=team_id,
                                                                   preventive_maintenance_frequency='hourly',
                                                                   maintenance_cycle_days=math.ceil(equipment.hourly_maintenance_hours/equipment.hours_in_per_day))
                    if equipment.is_daily_maintenance:
                        equipment._create_auto_maintenance_request(team_id=team_id,
                                                                   preventive_maintenance_frequency='daily',
                                                                   maintenance_cycle_days=0)

    def _create_auto_maintenance_request(self, team_id, preventive_maintenance_frequency,
                                         maintenance_cycle_days):
        """
        Author: Gaurav Vipani | Date: 26th July, 2023
        Purpose: For create auto maintenance request.
        """
        self.ensure_one()
        maintenance_date = self.get_maintenance_date_by_maintenance_frequency(preventive_maintenance_frequency)
        start_date = maintenance_date
        end_date = date.today()
        if start_date > end_date:
            start_date = date.today()
            end_date = maintenance_date
        days_count = self.get_days_count(start_date=start_date+timedelta(1), end_date=end_date)
        if maintenance_cycle_days <= days_count:
            next_maintenance_date = date.today()
            maintenance_scheduling_date = self.get_maintenance_schedule_date(
                start_date=next_maintenance_date, end_date=next_maintenance_date)
            equipment_existing_maintenance_by_frequency = self.find_maintenance_request(
                scheduled_date=maintenance_scheduling_date,
                preventive_maintenance_frequency=preventive_maintenance_frequency)
            existing_maintenance = self.find_maintenance_request(scheduled_date=maintenance_scheduling_date)
            if not equipment_existing_maintenance_by_frequency and preventive_maintenance_frequency == 'daily' or not \
                    existing_maintenance.filtered(
                        lambda maintenance: maintenance.preventive_maintenance_frequency != 'daily'):
                maintenance_checkpoint_template = self.get_maintenance_checkpoints_template(
                    maintenance_frequency=preventive_maintenance_frequency)
                maintenance_checkpoints = self.get_maintenance_checkpoints(
                    checkpoint_template=maintenance_checkpoint_template)
                maintenance_request = self.create_maintenance_request(
                    schedule_date=maintenance_scheduling_date,
                    maintenance_type='preventive',
                    maintenance_frequency=preventive_maintenance_frequency,
                    team_id=team_id,
                    maintenance_quality_points=maintenance_checkpoints)
                return maintenance_request

    def get_maintenance_schedule_date(self, start_date, end_date):
        """
        Author: Gaurav Vipani | Date: 18th Aug, 2023
        Purpose: For get maintenance schedule date.
        """
        dates = self.generate_dates(start_date=start_date, end_date=end_date)
        for date in dates:
            if not self.is_holiday(date=date) and self.is_weekday(date=date):
                return date

    def generate_dates(self, start_date, end_date):
        """
        Author: Gaurav Vipani | Date: 18th Aug, 2023
        Purpose: For generate list of date in between start date & end date.
        """
        # Base case: If the start date is greater than or equal to the end date, return an empty list
        if start_date > end_date:
            return []
        # Recursive case: Generate the list of dates between start and end dates
        next_date = start_date + timedelta(days=1)
        remaining_dates = self.generate_dates(next_date, end_date)
        return [start_date] + remaining_dates

    def get_days_count(self, start_date, end_date):
        """
        Author: Gaurav Vipani | Date: 18th Aug, 2023
        Purpose: For get days count.
        """
        dates = [date for date in self.generate_dates(start_date, end_date) if not
        self.is_holiday(date) and self.is_weekday(date)]
        return len(dates)

    def get_maintenance_date_by_maintenance_frequency(self, preventive_maintenance_frequency):
        """
        Author: Gaurav Vipani | Date: 18th Aug, 2023
        Purpose : For get maintenance date by maintenance frequency.
        """
        self.ensure_one()
        maintenance_date = self.maintenance_date
        previous_maintenance_request = self.find_previous_maintenance_request(
            preventive_maintenance_frequency=preventive_maintenance_frequency)
        if previous_maintenance_request:
            if previous_maintenance_request.schedule_date.date() > self.maintenance_date:
                maintenance_date = previous_maintenance_request.schedule_date.date()
        return maintenance_date

    def is_weekday(self, date):
        """
        Author: Gaurav Vipani | Date: 26th July, 2023
        Purpose: For check day is weekday or not.
        """
        is_weekday = date.weekday() not in (cal.SUNDAY, cal.SATURDAY)
        return is_weekday

    def is_holiday(self, date):
        """
        Author: Gaurav Vipani | Date: 18th Aug, 2023
        Purpose: For check day is holiday or not.
        """
        return self.env['resource.calendar.leaves'].search(
            [('time_type', '=', 'leave'), ('date_from', '<=', date),
             ('date_to', '>=', date), ('resource_id', '=', False)])

    def find_maintenance_request(self, scheduled_date, preventive_maintenance_frequency=False):
        """
        Author: Gaurav Vipani | Date: 01st Aug, 2023
        Purpose: This method will find maintenance request in system
        """
        self.ensure_one()
        new_stage_id = self.env.ref("maintenance.stage_0")
        inprogress_stage_id = self.env.ref("maintenance.stage_1")
        scheduled_date_start = scheduled_date.strftime('%Y-%m-%d 00:00:00')
        scheduled_date_end = scheduled_date.strftime('%Y-%m-%d 23:59:59')
        domain = [('stage_id', 'in', [new_stage_id.id, inprogress_stage_id.id]), ('equipment_id', '=', self.id),
                  ('schedule_date', '>=', scheduled_date_start), ('schedule_date', '<=', scheduled_date_end)]
        if preventive_maintenance_frequency:
            domain += [('preventive_maintenance_frequency', '=', preventive_maintenance_frequency)]
        maintenance_request = self.env['maintenance.request'].search(domain)
        return maintenance_request

    def find_previous_maintenance_request(self, preventive_maintenance_frequency):
        """
        Author: Gaurav Vipani | Date: 01st Aug, 2023
        Purpose: This method will find previous maintenance request.
        """
        self.ensure_one()
        domain = [('equipment_id', '=', self.id),
                  ('preventive_maintenance_frequency', '=', preventive_maintenance_frequency)]
        maintenance_request = self.env['maintenance.request'].search(domain, limit=1)
        return maintenance_request

    def get_maintenance_checkpoints_template(self, maintenance_frequency):
        """
        Author: Gaurav Vipani | Date: 01st Aug, 2023
        Purpose: This method will get checkpoint template.
        """
        self.ensure_one()
        return self.env["maintenance.checkpoint.template"].search(['|', ('maintenance_equipment_ids', '=', self.id),
                                                                   ('maintenance_equipment_ids', '=', False), (
                                                                       'preventive_maintenance_request_frequency', '=',
                                                                       maintenance_frequency)])

    def get_maintenance_checkpoints(self, checkpoint_template):
        """
        Author: Gaurav Vipani | Date: 01st Aug, 2023
        Purpose: This method will get maintenance checkpoints.
        """
        return self.env["maintenance.checkpoint"].search([('maintenance_checkpoint_template_id', 'in',
                                                           checkpoint_template.ids)])

    def prepare_maintenance_request_vals(self, name, maintenance_type, preventive_frequency, team, schedule_date,
                                         maintenance_quality_points):
        """
        Author: Gaurav Vipani | Date: 01st Aug, 2023
        Purpose: This method will prepare maintenance request vals
        """
        maintenance_quality_checks = []
        for quality_point in maintenance_quality_points:
            maintenance_quality_checks.append((0, 0, {'name': quality_point.name}))
        vals = {
            'name': name,
            'equipment_id': self.id,
            'maintenance_team_id': team.id,
            'schedule_date': schedule_date,
            'maintenance_type': maintenance_type,
            'company_id': self.company_id.id or self.env.company.id,
            'preventive_maintenance_frequency': preventive_frequency,
            'maintenance_equipment_quality_checks_ids': maintenance_quality_checks
        }
        return vals

    def create_maintenance_request(self, schedule_date, maintenance_type, maintenance_frequency, team_id,
                                   maintenance_quality_points):
        """
        Author: Gaurav Vipani | Date: 01st Aug, 2023
        Purpose: This method will find maintenance and create if not found
        """
        self.ensure_one()
        maintenance_request_env = self.env['maintenance.request']
        maintenance_name = self.name + " - " + maintenance_frequency.replace('_', ' ').title()
        maintenance_vals = self.prepare_maintenance_request_vals(name=maintenance_name,
                                                                 maintenance_type=maintenance_type,
                                                                 preventive_frequency=maintenance_frequency,
                                                                 team=team_id,
                                                                 schedule_date=schedule_date,
                                                                 maintenance_quality_points=maintenance_quality_points)
        maintenance_request = maintenance_request_env.create(maintenance_vals)
        return maintenance_request

    def write(self, vals):
        # If user change maintenance date
        old_maintenance_date = self.maintenance_date
        date = vals.get("maintenance_date", False)
        res = super(MaintenanceEquipment, self).write(vals)
        if date:
            if isinstance(date, str):
                new_maintenance_date = datetime.strptime(date, "%Y-%m-%d").date()
            else:
                new_maintenance_date = date
            if old_maintenance_date < new_maintenance_date:
                diff_days = new_maintenance_date - old_maintenance_date
                date_list = [(new_maintenance_date - timedelta(days=day)) for day in range(1,diff_days.days+1)]
                for old_date in date_list:
                    maintenance_request = self.find_maintenance_request(old_date)
                    for request in maintenance_request:
                        if request.preventive_maintenance_frequency:
                            equipment_name = request.equipment_id.name
                            request.unlink()
                            _logger.info("{} has deleted {} date's maintenance request".format(equipment_name,
                                                                                               old_date))
        return res