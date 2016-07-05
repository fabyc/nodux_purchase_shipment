#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from sql.operators import Concat

from trytond.model import Workflow, ModelView, fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond import backend

__all__ = ['ShipmentIn']



class ShipmentIn:
    __metaclass__ = PoolMeta
    __name__ = 'stock.shipment.in'

    @classmethod
    def __setup__(cls):
        super(ShipmentIn, cls).__setup__()
        cls._error_messages.update({
                'reset_move': ('You cannot reset to draft move "%s" because '
                    'it was generated by a purchase.'),
                })

    @classmethod
    def write(cls, *args):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        PurchaseLine = pool.get('purchase.line')

        super(ShipmentIn, cls).write(*args)

        actions = iter(args)
        for shipments, values in zip(actions, actions):
            if values.get('state') not in ('done', 'cancel'):
            #if values.get('state') not in ('received', 'cancel'):
                continue
            purchases = []
            move_ids = []
            for shipment in shipments:
                move_ids.extend([x.id for x in shipment.incoming_moves])

            with Transaction().set_context(_check_access=False):
                purchase_lines = PurchaseLine.search([
                        ('moves', 'in', move_ids),
                        ])
                if purchase_lines:
                    purchases = list(set(l.purchase for l in purchase_lines))
                    Purchase.process(purchases)


    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, shipments):
        PurchaseLine = Pool().get('purchase.line')
        for shipment in shipments:
            for move in shipment.incoming_moves:
                if (move.state == 'cancel'
                        and isinstance(move.origin, PurchaseLine)):
                    cls.raise_user_error('reset_move')

        return super(ShipmentIn, cls).draft(shipments)
