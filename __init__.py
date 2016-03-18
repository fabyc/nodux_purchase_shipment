#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from .stock import *
from .purchase import *
def register():
    Pool.register(
        ShipmentIn,
        Purchase,
        module='nodux_purchase_shipment', type_='model')

