#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import datetime
from decimal import Decimal
from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond import backend
from trytond.pool import Pool, PoolMeta
from functools import partial
from itertools import groupby, chain

__all__ = ['Purchase']


class Purchase():
    __metaclass__ = PoolMeta
    __name__ = 'purchase.purchase'
    _rec_name = 'reference'

    def _get_move_sale_line(self, shipment_type):
        '''
        Return move for each sale lines of the right shipment_type
        '''
        res = {}
        move_type = 'in'
        for line in self.lines:
            val = line.get_move(move_type)
            if val:
                res[line.id] = val
        return res

    def _group_shipment_key(self, moves, move):
        '''
        The key to group moves by shipments

        move is a tuple of line id and a move
        '''
        pool=Pool()
        PurchaseLine = pool.get('purchase.line')
        line_id, move = move
        line = PurchaseLine(line_id)

        planned_date = max(m.planned_date for m in moves)
        return (
            ('planned_date', planned_date),
            ('warehouse', line.purchase.warehouse.id),
            )

    _group_return_key = _group_shipment_key

    def _get_shipment_purchase(self, Shipment, key):
        values = {
            'supplier': self.party.id,
            'contact_address': self.invoice_address.id,
            'company': self.company.id,
            }
        values.update(dict(key))
        return Shipment(**values)


    def create_shipment(self, shipment_type):
        pool = Pool()

        moves = self._get_move_sale_line(shipment_type)
        if not moves:
            return
        if shipment_type == 'in':
            keyfunc = partial(self._group_shipment_key, moves.values())
            Shipment = pool.get('stock.shipment.in')
        elif shipment_type == 'return':
            keyfunc = partial(self._group_return_key, moves.values())
            Shipment = pool.get('stock.shipment.in.return')
        moves = moves.items()
        moves = sorted(moves, key=keyfunc)

        shipments = []
        for key, grouped_moves in groupby(moves, key=keyfunc):
            shipment = self._get_shipment_purchase(Shipment, key)
            shipment.moves = (list(getattr(shipment, 'moves', []))
                + [x[1] for x in grouped_moves])
            shipment.save()
            shipments.append(shipment)
        if shipment_type == 'in':
            Shipment.draft(shipments)
        return shipments


    @classmethod
    @ModelView.button
    def process(cls, purchases):
        process, done = [], []
        for purchase in purchases:
            purchase.create_invoice()
            purchase.create_shipment('in')
            purchase.create_shipment('return')
            purchase.set_invoice_state()
            purchase.create_move('in')
            return_moves = purchase.create_move('return')
            if return_moves:
                purchase.create_return_shipment(return_moves)
            purchase.set_shipment_state()
            if purchase.is_done():
                done.append(purchase)
            elif purchase.state != 'processing':
                process.append(purchase)
        if process:
            cls.proceed(process)
        if done:
            cls.do(done)
