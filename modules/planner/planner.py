from openerp.osv import osv, fields
from tools.translate import _
import time

TASK_PRIORITY = [(5, 'Lowest'), (4, 'Low'), (3, 'Medium'), (2, 'High'), (1, 'Highest')]
TASK_STATES = [('draft', 'Draft'), ('proceed', 'Proceed'), ('completed', 'Completed'), ('cancel', 'Cancelled')]
TASK_TYPES = [('event', 'Event'), ('purchase', 'Purchase'), ('other', 'Other')]


class planner_money(osv.osv):
    _name = 'planner.money'
    _columns = {
        'state': fields.selection([('expected', 'Expected'), ('factual', 'Factual'), ('cancel', 'Cancelled')], string="State"),
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
        'state': 'expected',
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
                'state': 'factual',
                'amount_factual': move.amount_factual,
                'date_realize': move.date_realize,
            })

        return True

    _defaults = {
        'date_realize': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }


class planner_task(osv.osv):
    _name = 'planner.task'

    def _compute_money(self, cr, uid, ids, move_type, state, context=None):
        res = {}

        for row in self.browse(cr, uid, ids, context):
            money = 0
            if row.is_have_outlay:
                for line in row.outlay_ids:
                    if line.type == move_type:
                        money += line.amount_expected if state == 'expected' else line.amount_factual
            res[row.id] = money
        return res

    def _compute_exp_in_money(self, cr, uid, ids, field, value, context=None):
        return self._compute_money(cr, uid, ids, 'in', 'expected', context=context)
    def _compute_exp_out_money(self, cr, uid, ids, field, value, context=None):
        return self._compute_money(cr, uid, ids, 'out', 'expected', context=context)
    def _compute_fact_in_money(self, cr, uid, ids, field, value, context=None):
        return self._compute_money(cr, uid, ids, 'in', 'factual', context=context)
    def _compute_fact_out_money(self, cr, uid, ids, field, value, context=None):
        return self._compute_money(cr, uid, ids, 'out', 'factual', context=context)

    def _compute_balance(self, cr, uid, ids, state, context=None):
        res = {}
        for row in self.browse(cr, uid, ids, context):
            balance = 0
            if row.is_have_outlay:
                in_money = row.expected_in_money if state == 'expected' else row.factual_in_money
                out_money = row.expected_out_money if state == 'expected' else row.factual_out_money
                balance = in_money - out_money
            res[row.id] = balance
        return res

    def _compute_exp_balance(self, cr, uid, ids, field, value, context=None):
        return self._compute_balance(cr, uid, ids, 'expected', context=context)
    def _compute_fact_balance(self, cr, uid, ids, field, value, context=None):
        return self._compute_balance(cr, uid, ids, 'factual', context=context)

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
        'expected_in_money': fields.function(_compute_exp_in_money, type="float", string="Money in (Expected)", store=False),
        'expected_out_money': fields.function(_compute_exp_out_money, type="float", string="Money out (Expected)", store=False),
        'expected_balance': fields.function(_compute_exp_balance, type="float", string="Balance (Expected)", store=False),
        'factual_in_money': fields.function(_compute_fact_in_money, type="float", string="Money in (Factual)", store=False),
        'factual_out_money': fields.function(_compute_fact_out_money, type="float", string="Money out (Factual)", store=False),
        'factual_balance': fields.function(_compute_fact_balance, type="float", string="Balance (Factual)", store=False),
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
                    if line.state == 'expected':
                        flag = False
                if flag:
                    self.write(cr, uid, [row.id], {'state': 'completed'}, context)
                else:
                    raise osv.except_osv(_("Can't complete task!"), _("Some lines in outlay is not realized!"))
            else:
                self.write(cr, uid, [row.id], {'state': 'completed'}, context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context)
        return True
