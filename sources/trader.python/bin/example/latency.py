#!/usr/bin/env python
# randomly adds/cancels orders
# keeps track of average latency of ordering and cancelling
# this file was named take_liquidity previously

import random
import math
import time

import bitfloorapi

bitfloor = bitfloorapi.Client()

olatency = [] # order latency
clatency = [] # cancel latency

while True:
    # add order
    book = bitfloor.book()
    side = random.randrange(2)
    try:
        if side == 0:
            price = float(book['ask'][0])*1.3
        else:
            price = float(book['bid'][0])*.7
    except:
        # this can happen if the book has no liquidity
        # if so, cannot take liquidity, so wait and try again
        time.sleep(1)
        continue

    price = bitfloor.round_inc(price)


    size = round(max(0.01, 10*random.random())*1e8)/1e8
    order = bitfloor.order_new(side=side, size=size, price=price)
    id = order.get('order_id')
    if not id:
        print "ERROR:", order

    time.sleep(1)
