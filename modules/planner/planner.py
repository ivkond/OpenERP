from openerp.osv import osv, fields
from tools.translate import _
import time

TASK_PRIORITY = [(5, 'Lowest'), (4, 'Low'), (3, 'Medium'), (2, 'High'), (1, 'Highest')]
TASK_STATES = [('draft', 'Draft'), ('proceed', 'Proceed'), ('completed', 'Completed'), ('cancel', 'Cancelled')]
TASK_TYPES = [('event', 'Event'), ('purchase', 'Purchase'), ('other', 'Other')]


class planner_money(osv.osv):
    _name = 'planner.money'
    _columns = {
        'state': fields.selection([('planned', 'Planned'), ('realized', 'Realized'), ('cancel', 'Cancelled')], string="State"),
        'type': fields.selection([('in', 'In'), ('out', 'Out')], string='Move type', required=True),
        'amount_expected': fields.float('Amount expected', required=True),
        'amount_factual': fields.float('Amount factual', required=True),
        'purpose': fields.char('Purpose', size=64, required=True),
        'description': fields.text('Description'),
        'date': fields.datetime('Date', required=True),
        'date_realized': fields.datetime('Date realized'),
        'task_id': fields.many2one('planner.task', string="Task", ondelete='cascade'),
    }

    def button_realize(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False
        })
        return {
            'name': 'Money move realize',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'planner.money.realize',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy': True,
        }

    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context)
        return True

    _defaults = {
        'state': 'planned',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_realized': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'amount_factual': 0.0,
    }


class planner_money_realize(osv.osv_memory):
    _name = 'planner.money.realize'
    _columns = {
        'date_realize': fields.datetime('Realize date', required=True),
        'amount_factual': fields.float('Amount factual', required=True),
    }

    def action_realize(self, cr, uid, ids, context=None):
        money_id = context.get('active_id')
        if not money_id:
            raise osv.except_osv(_('Error!'), _('No ID in context. Can\'t update record!'))

        for move in self.browse(cr, uid, ids, context):
            if not move.amount_factual:
                raise osv.except_osv(_('Error!'), _('Wrong amount!'))

            self.pool.get('planner.money').write(cr, uid, [money_id], {
                'state': 'realized',
                'amount_factual': move.amount_factual,
                'date_realize': move.date_realize,
            })

        return True

    _defaults = {
        'date_realize': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }


class planner_task(osv.osv):
    _name = 'planner.task'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'date': fields.datetime('Date', required=True),
        'description': fields.text('Description'),
        'priority': fields.selection(TASK_PRIORITY, string="Priority", required=True),
        'state': fields.selection(TASK_STATES, string="State"),
        'type': fields.selection(TASK_TYPES, string="Type", required=True),
        'location_id': fields.char('Location'),
        'is_have_outlay': fields.boolean('Have outlay'),
        'outlay_ids': fields.one2many('planner.money', 'task_id', string="Outlays"),
    }
    _defaults = {
        'state': 'draft',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'is_have_outlay': True,
    }

    def button_proceed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'proceed'}, context)
        return True

    def button_complete(self, cr, uid, ids, context=None):
        for row in self.browse(cr, uid, ids, context):
            if row.is_have_outlay:
                flag = True
                for line in row.outlay_ids:
                    if line.state == 'planned':
                        flag = False
                if flag:
                    self.write(cr, uid, [row.id], {'state': 'completed'}, context)
                else:
                    raise osv.except_osv(_("Can't complete task!"), _("Some lines in outlay is not realized!"))
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context)
        return True


# TODO: WRITE IT MOTHERFUCKER!
# class planner_budget(osv.osv):
#     _name = 'planner.budget'
#     _columns = {
#         'money_on_hands': fields.float('On hands'),
#         'piggy': fields.float('In piggy'),
#         'money_incoming': fields.function(),
#         'money_outgoing': fields.h
#     }
# class planner_statistic(osv.osv):
#     _name = 'planner.statistic'
#     _columns = {
#         'money_out': fields.function(),
#         'money_in': fields.function(),
#     }





























