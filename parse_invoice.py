text = """1 HM0433 BKR® JADE BOTTLE AROMA DIFFUSER VASE – 95ML
SKU: HM0433 % 2 0 2 Sold PCS 1,100.85 0.00 2,201.70
2 HM0167 CLOTH DYING ROPE
SKU: HM0167 % 4 0 4 Sold PCS 253.39 0.00 1,013.56
3 CA0054 SHUBHAM BLIND SPOT MIRROR CAR
SKU: CA0054 % 4 0 4 Sold PCS 305.08 0.00 1,220.32
4 CA0052 ANTI SLIP BOOT MAT
SKU: CA0052 % 5 0 5 Sold PCS 120.00 0.00 600.00
5 CA0058 CLEANING MICROFIBRE CLOTH
SKU: CA0058 % 16 0 16 Sold PCS 215.00 0.00 3,440.00
6 CA0061 GLASS WIPES SET
SKU: CA0061 % 5 0 5 Sold PCS 120.00 0.00 600.00
7 CA0066 SEAT ORGANISER
SKU: CA0066 % 5 0 5 Sold PCS 267.50 0.00 1,337.50
8 HM0154 BKR HANGING 6 SHELF CLOSET
SKU: HM0154 % 4 0 4 Sold PCS 100.00 0.00 400.00
9 HM0169 CLEANING TOWEL MODEL - 3001
SKU: HM0169 % 20 0 20 Sold PCS 69.00 0.00 1,380.00
10 HM0170 DUAL CLEANING CLOTH
SKU: HM0170 % 10 0 10 Sold PCS 21.00 0.00 210.00
11 HM0173 BAMBOO CLEANING CLOTH
SKU: HM0173 % 10 0 10 Sold PCS 25.00 0.00 250.00
12 HM0168 CLOTH DRYING ROPE 5M
SKU: HM0168 % 4 0 4 Sold PCS 98.00 0.00 392.00
13 HM0413 ALARM LOCK WITH DOUBLE LOCK 146073
SKU: HM0413 % 2 0 2 Sold PCS 100.00 0.00 200.00
14 HM0427 WINE HOLDER BARREL- METAL
SKU: HM0427 % 2 0 2 Sold PCS 324.00 0.00 648.00
15 HM0432 HUMIDIFIER - BULB SHAPE SMALL
SKU: HM0432 % 2 0 2 Sold PCS 289.00 0.00 578.00
16 HM0435 HUMIDIFIER - ROUND WITH MULTI LIGHTING
SKU: HM0435 % 2 0 2 Sold PCS 395.00 0.00 790.00
17 HM0436 USB MIST HUMIDIFIER BEAR SHAPED WITH LED LAMP –
SKU: HM0436 % 2 0 2 Sold PCS 515.66 0.00 1,031.32
18 HM0713 HOUSE NIGHT LAMP BLISTER CARD PACKING 149482
SKU: HM0713 % 10 0 10 Sold PCS 44.00 0.00 440.00
19 HM0715 GRAPES NIGHT LAMP 149486
SKU: HM0715 % 10 0 10 Sold PCS 73.16 0.00 731.60
20 HM0714 CAR SHAPE NIGHT LAMP 149483
SKU: HM0714 94052090 % 10 0 10 Sold PCS 60.18 0.00 601.80
21 LG0085 2 PIPE CONNECTOR WITH ON OFF SWITCH
SKU: LG0085 % 10 0 10 Sold PCS 20.00 0.00 200.00
22 LG0089/LG0090/LG022/LG0316/LG0021/ SPRINKLER NEW
SKU: LG0089 % 20 0 20 Sold PCS 338.00 0.00 6,760.00
23 LG0329/LG0331 WATER SPRAY GUN HEAVY DUTY
SKU: LG0329 % 8 0 8 Sold PCS 79.00 0.00 632.00
24 LG0348/LG0075-76-77-78-83-84-85-86 JOINT CONNECTOR
SKU: LG0348 % 10 0 10 Sold PCS 20.00 0.00 200.00
25 LG0360 BOY GIRL PEN/ FLOWER STAND DECORATION
SKU: LG0360 % 3 0 3 Sold PCS 142.95 0.00 428.86
26 LG0371 BUCKET WITH HANDLE 6 MODELS ASSORTED 10 CM
SKU: LG0371 % 8 0 8 Sold PCS 70.00 0.00 560.00
27 LG0372 BKR METAL POT 15CM
SKU: LG0372 % 2 0 2 Sold PCS 50.00 0.00 100.00
28 LG0379 BKR 8-FUNCTION LADYBUG SPRINKLER
SKU: LG0379 % 10 0 10 Sold PCS 150.00 0.00 1,500.00
29 LG0381 BKR® GARDEN SPRINKLER WITH LONG 3 ARMS -
SKU: LG0381 % 5 0 5 Sold PCS 150.00 0.00 750.00
30 LG0328 GARDEN 3 ARM ROUND SPRINKLER ROUND BLUE BLACK
SKU: LG0328 84248200 % 10 0 10 Sold PCS 204.00 0.00 2,040.00
31 LG0656 1 MIST PIPE SET
SKU: LG0656 % 40 0 40 Sold PCS 39.00 0.00 1,560.00
32 LG0650 FLOWER POT SPRINKLER SET SXGT001
SKU: LG0650 84248200 % 2 0 2 Sold PCS 622.00 0.00 1,244.00
33 LG0651 SPRINKLER GARDEB SET PIPE
SKU: LG0651 % 5 0 5 Sold PCS 203.00 0.00 1,015.00
34 LG0652 DRIP IRRIGATION ACCESSORIES FOR FOR BIG GARDEN POTS
SKU: LG0652 % 101 0 101 Sold PCS 23.00 0.00 2,323.00
35 TR0009 FOLDABLE BUCKET
SKU: TR0009 % 10 0 10 Sold PCS 130.00 0.00 1,300.00
"""

lines = text.strip().split('\n')
parsed_items = []
for i in range(0, len(lines), 2):
    name_line = lines[i]
    details_line = lines[i+1]
    
    parts = details_line.split()
    sku = parts[1]
    
    qty_idx = parts.index('%') + 1
    qty = int(parts[qty_idx])
    rate = float(parts[-3].replace(',', ''))
    
    parsed_items.append({
        "sku": sku,
        "quantity": qty,
        "selling_price": rate,
    })

import sys
sys.path.append('.')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.schema import *
DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# find gst rate for each product
for idx, item in enumerate(parsed_items):
    product = db.query(Product).filter(Product.sku == item["sku"], Product.company_id == 2).first()
    if product:
        item["product_id"] = product.id
        item["gst_rate"] = product.default_gst_rate
        item["product_name"] = product.name
        item["hsn_sac"] = product.hsn
        item["unit"] = product.unit
    else:
        print(f"Product not found for SKU: {item['sku']}")
        sys.exit(1)
        
    taxable_amount = item["quantity"] * item["selling_price"]
    tax = taxable_amount * (item["gst_rate"] / 100)
    
    item["taxable_amount"] = taxable_amount
    item["igst"] = tax
    item["cgst"] = 0
    item["sgst"] = 0
    item["line_total"] = taxable_amount + tax

total_taxable = sum(i["taxable_amount"] for i in parsed_items)
total_tax = sum(i["igst"] for i in parsed_items)
grand_total = total_taxable + total_tax

sale = db.query(Sale).filter(Sale.id == 50).first()
sale.total_taxable_amount = total_taxable
sale.total_tax = total_tax
sale.grand_total = grand_total

# delete current items
db.query(SaleItem).filter(SaleItem.sale_id == 50).delete()
db.flush()

for item in parsed_items:
    si = SaleItem(
        sale_id=50,
        product_id=item["product_id"],
        sku=item["sku"],
        product_name=item["product_name"],
        hsn_sac=item["hsn_sac"],
        unit=item["unit"],
        quantity=item["quantity"],
        selling_price=item["selling_price"],
        discount=0,
        gst_rate=item["gst_rate"],
        taxable_amount=item["taxable_amount"],
        cgst=item["cgst"],
        sgst=item["sgst"],
        igst=item["igst"],
        line_total=item["line_total"]
    )
    db.add(si)

db.commit()
print(f"Successfully restored 35 items! Grand Total: {grand_total}")
