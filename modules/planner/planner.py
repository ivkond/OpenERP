# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from tools.translate import _
import time

# TODO: Создать временный объект Статистика, который будет выводить рассчитанные доходы/расходы и баланс.
# TODO: Прикрепить Статистику к Задачам в выпадающий пункт меню.
# TODO: Расширить Статистику - добавить возможность подсчёта для нескольких объектов по заданному критерию.
# TODO: Расширить Статистику - подсчёт по заданному периоду времени.

TASK_PRIORITY = [(3, 'Low'), (2, 'Medium'), (1, 'High')]
TASK_STATES = [('draft', 'Draft'), ('proceed', 'Proceed'), ('completed', 'Completed'), ('cancel', 'Cancelled')]
TASK_TYPES = [('purchase', 'Purchase'), ('point', 'Point'), ('other', 'Other')]


class planner_money(osv.osv):
    _name = 'planner.money'
    _columns = {
        'state': fields.selection([('planned', 'Planned'), ('completed', 'Completed'), ('cancel', 'Cancelled')], string="State"),
        'type': fields.selection([('in', 'In'), ('out', 'Out')], string='Move type', required=True),
        'amount_expected': fields.float('Amount expected', required=True),
        'amount_factual': fields.float('Amount factual', required=True),
        'purpose': fields.char('Purpose', size=64, required=True),
        'description': fields.text('Description'),
        'date': fields.datetime('Date', required=True),
        'date_completed': fields.datetime('Date realized'),
        'task_id': fields.many2one('planner.task', string="Task", ondelete='cascade'),
    }

    def button_complete(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False
        })
        return {
            'name': 'Money move completion',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'planner.money.wizard',
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
        'date_completed': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'amount_factual': 0.0,
    }


class planner_money_wizard(osv.osv_memory):
    _name = 'planner.money.wizard'
    _columns = {
        'date_completed': fields.datetime('Completion date', required=True),
        'amount_factual': fields.float('Amount factual', required=True),
    }

    def action_complete(self, cr, uid, ids, context=None):
        money_id = context.get('active_id')
        if not money_id:
            raise osv.except_osv(_('Error!'), _('No ID in context. Can\'t update record!'))

        for move in self.browse(cr, uid, ids, context):
            if not move.amount_factual:
                raise osv.except_osv(_('Error!'), _('Wrong amount!'))

            self.pool.get('planner.money').write(cr, uid, [money_id], {
                'state': 'completed',
                'amount_factual': move.amount_factual,
                'date_completed': move.date_completed,
            })

        return True

    _defaults = {
        'date_completed': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }


# TODO: В меню задач добавить пункты - Текущие задачи, Черновики.
# TODO: Убрать из задач тип Встреча.
# TODO: Убрать из задач подсчёт статистики.
# TODO: Сделать календарь доходов/расходов.
class planner_task(osv.osv):
    _name = 'planner.task'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'date': fields.datetime('Date', required=True),
        # 'date_completed': fields.datetime('Date completed', required=True),
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
            else:
                self.write(cr, uid, [row.id], {'state': 'completed'}, context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context)
        return True
    