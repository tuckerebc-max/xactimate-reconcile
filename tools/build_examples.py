"""Rebuild public synthetic originals and case ledgers. No real claim or market price."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]
SKILL=Path(os.environ.get('XR_DEV_SKILL',ROOT/'.agents/skills/xactimate-reconcile'))
sys.path.insert(0,str(SKILL/'scripts'))
from xactimate_reconcile.store import init_case,read_json,write_json
from xactimate_reconcile.intake import add_document,extract_document

SCENARIOS={
 'shingle':{
  'title':'Measured area and duplicate flashing correction',
  'rows':[
   ('Shingle installation','SQ','20','400','25','450','installation','quantity_price','Correct measured surface area and the documented unit price.','The synthetic measurement record establishes 25 SQ; the first estimate used 20 SQ.','The measured surface is already slope-adjusted. The rate comparison uses the same fictional specification and excludes taxes and general O&P.','The aerial report may already include pitch or waste.','Use the face-by-face synthetic takeoff and check that neither slope nor waste is added twice.',['A-O01','A-O18','B-I02','B-I12']),
   ('Flashing replacement','LF','100','10','80','10','flashing','quantity_price','Reduce the flashing allowance to 80 LF.','The fixture includes a 20 LF segment twice in the baseline takeoff.','The two entries describe the same physical segment, so the revision removes that overlap.','The second entry could describe a different location.','The synthetic location map assigns both entries to the same segment; a distinct field location would change this conclusion.',['A-O10','B-I10']),
   ('Debris handling','EA','1','350','1','350','disposal','quantity_price','Retain the existing debris allowance.','The fictional allowance covers the complete documented disposal scope.','No additional disposal operation is supported.','A separate dumpster charge may overlap the removal price.','Retain this allowance and do not add a second charge for the same disposal.',['A-O16','B-I14'])],
  'expected':{'baseline_direct':'9350.00','proposed_direct':'12400.00','delta_direct':'3050.00','partial':False},
  'notes':'Scenario premise: a 25 SQ roof surface, 80 LF of unique flashing and one disposal operation. All conditions and prices are fictional test data. No policy or market quote is supplied.'},
 'tile':{
  'title':'Feasible tile repair with a documented underlayment rate question',
  'rows':[
   ('Tile lift and reset','SQ','18','200','18','200','tile-reset','quantity_price','Retain the bounded lift-and-reset scope.','The synthetic case specifies reusable compatible tiles and access to the affected underlayment.','The supplied scenario supports reuse, not replacement of all roof tile.','Widespread handling damage could prevent reuse.','No such finding is supplied; hold any additional tile quantity until documented.',['A-O07','A-O04','B-I05']),
   ('Compatible replacement tile','EA','10','30','10','30','replacement-tile','quantity_price','Retain replacement of ten documented damaged tiles.','Ten damaged units are identified in the synthetic record and compatible replacements are available.','Individual replacement is feasible on the stipulated facts.','Discontinued products can be unavailable or incompatible.','This fictional sourcing record identifies compatible stock; discontinuation alone cannot defeat that evidence.',['A-O03','B-I05']),
   ('Underlayment installation','SQ','18','150','18','175','underlayment','quantity_price','Review the supported rate difference for the same underlayment scope.','The synthetic price record uses 175 per SQ for the specified replacement assembly, compared with 150 in the first estimate.','The quantities and assembly are held constant to isolate the rate effect.','The higher quote may include an upgrade or work already counted.','The fixture holds specification and included work constant. A real case needs comparable dated pricing and licensed item detail.',['A-O06','A-O18','B-I10','B-I12'])],
  'expected':{'baseline_direct':'6600.00','proposed_direct':'7050.00','delta_direct':'450.00','partial':False},
  'notes':'Scenario premise: localized repair remains feasible; eighteen SQ of lift/reset and underlayment; ten compatible replacement tiles. No blanket breakage factor, matching entitlement or market price is asserted.'},
 'low_slope':{
  'title':'Bounded low-slope correction with concealed work held',
  'rows':[
   ('Compatible membrane repair','SQ','4','250','6','250','membrane-repair','quantity_price','Review repair of the documented six SQ area.','The synthetic damage map identifies six SQ within a compatible repair area.','The scenario supports a bounded repair; it does not establish the need for complete system replacement.','Maintenance, ponding or a smaller patch may explain the condition.','The fictional evidence stipulates the six SQ repair area. A real case needs system identification and causation evidence.',['A-O08','B-I06']),
   ('Drain flashing repair','EA','1','180','1','180','drain-flashing','quantity_price','Retain the existing drain-flashing repair.','One affected drain detail is identified in both fictional estimates.','The same operation is priced once on each side.','Drain cleaning may be maintenance rather than covered repair.','The fixture separates flashing repair from cleaning; no maintenance charge is added.',['A-O13','B-I03']),
   ('Concealed substrate work','EA','1','100',None,'100','substrate','quantity_price','Obtain exposure photographs and a measured substrate assessment before pricing additional work.','The substrate below the repair has not been exposed or measured.','There is insufficient evidence to revise the concealed-work quantity.','The material may be sound or deteriorated for an unrelated reason.','Retain the uncertainty and request a focused inspection; do not convert an unknown quantity to zero.',['A-O11','B-I03'])],
  'expected':{'baseline_direct':'1280.00','proposed_direct':None,'delta_direct':None,'partial':True,'supported_delta':'500.00'},
  'notes':'Scenario premise: six SQ of compatible membrane repair and one drain detail. Concealed substrate extent remains unknown. This is a partial comparison and cannot support a complete revised estimate or payment amount.'}
}


def source_pdf(path,side,rows,title):
    from reportlab.pdfgen import canvas
    c=canvas.Canvas(str(path),pagesize=(612,792))
    c.setTitle('Synthetic '+side+' roof estimate')
    c.setFont('Helvetica-Bold',15);c.drawString(48,746,'SYNTHETIC EXAMPLE - NOT A CLIENT CLAIM')
    c.setFont('Helvetica',11);c.drawString(48,720,title[:85])
    c.drawString(48,697,side.upper()+' v1 | 2026-09-21 | direct pre-tax USD')
    c.setFont('Helvetica-Bold',10)
    for x,t in [(48,'Item'),(332,'Qty'),(380,'Unit'),(426,'Rate'),(504,'Total')]:c.drawString(x,653,t)
    boxes=[];total=Decimal(0);known=True
    for i,row in enumerate(rows):
        y=622-i*45
        qty,rate=(row[2],row[3]) if side=='baseline' else (row[4],row[5])
        amount=(Decimal(qty)*Decimal(rate)).quantize(Decimal('.01')) if qty is not None else None
        if amount is None:known=False
        else:total+=amount
        c.setFont('Helvetica',10)
        for x,t in [(48,row[0]),(332,qty or 'Unknown'),(380,row[1]),(426,rate),(504,str(amount) if amount is not None else 'Unknown')]:c.drawString(x,y,t)
        boxes.append([88,2*(792-y-13),1140,2*(792-y+7)])
    y=622-len(rows)*45-18
    c.setFont('Helvetica-Bold',11);c.drawString(48,y,'Direct subtotal: '+str(total if known else 'Unknown'))
    footer=[88,2*(792-y-14),1140,2*(792-y+8)]
    c.setFont('Helvetica',9)
    c.drawString(48,160,'All quantities, observations and rates are fictional test assumptions.')
    c.drawString(48,145,'Taxes, general overhead/profit, coverage and payment are not determined.')
    c.save()
    return boxes,footer,str(total) if known else None


def field(value,doc,box):
    page=doc['pages'][0]
    return {'value':value,'raw_text':value if value is not None else 'Unknown','alternatives':[],'resolution':None,
            'verification':'synthetic_checked','reviewer':'synthetic fixture author','reviewed_at':'2026-09-21T23:00:00Z','ocr_confidence':None,
            'source':{'doc_id':doc['id'],'page':1,'bbox':box,'coordinate_space':'pixels','image_size':[page['width'],page['height']],'method':'manual_synthetic'}}


def build(roof,data):
    dest=SKILL/'assets/examples'/roof
    if dest.exists():shutil.rmtree(dest)
    init_case(dest,'SYN-'+roof.upper().replace('_','-'),roof,True)
    scratch=ROOT/'validation/example_sources';scratch.mkdir(parents=True,exist_ok=True)
    generated={}
    for side in ('baseline','proposed'):
        file=scratch/(roof+'-'+side+'.pdf')
        boxes,footer,total=source_pdf(file,side,data['rows'],data['title'])
        doc=add_document(dest,file,side)
        extract_document(dest,doc['id'],'off')
        active=next(d for d in read_json(dest/'case.json')['documents'] if d['id']==doc['id'])
        active['reported_direct_total']=field(total,active,footer)
        generated[side]=(active,boxes)
    notes=scratch/(roof+'-notes.txt');notes.write_text('SYNTHETIC SCENARIO PREMISES\n'+data['notes']+'\n')
    evidence=add_document(dest,notes,'evidence');extract_document(dest,evidence['id'],'off')
    case=read_json(dest/'case.json')
    case['documents']=[generated['baseline'][0],generated['proposed'][0],next(d for d in case['documents'] if d['id']==evidence['id'])]
    case['as_of']='2026-09-21';case['title']=data['title'];case['sender']['name']='Synthetic estimator';case['notes']=data['notes']
    case['jurisdiction']={'country':'US','state':'AZ','municipality':'Phoenix','verified':True}
    case['price_context']['location']='Synthetic Phoenix setting; no market prices supplied'
    case['evidence']=[{'id':'E-BASE','doc_id':generated['baseline'][0]['id'],'page':1,'description':'Synthetic baseline estimate'},
                      {'id':'E-PROP','doc_id':generated['proposed'][0]['id'],'page':1,'description':'Synthetic proposed estimate'},
                      {'id':'E-NOTES','doc_id':evidence['id'],'page':1,'description':'Fictional scenario premises and limitations'}]
    for i,row in enumerate(data['rows']):
        for side,prefix in [('baseline','B'),('proposed','P')]:
            doc,boxes=generated[side];qty,rate=(row[2],row[3]) if side=='baseline' else (row[4],row[5])
            amount=str((Decimal(qty)*Decimal(rate)).quantize(Decimal('.01'))) if qty is not None else None
            line={'id':prefix+str(i+1),'side':side,'description':row[0],'specification':'synthetic-same-assembly','roof_location':'main-roof',
                  'quantity':field(qty,doc,boxes[i]),'unit':row[1],'unit_price':field(rate,doc,boxes[i]),'reported_total':field(amount,doc,boxes[i]),
                  'financial_basis':'direct_pre_tax','area_basis':'roof_surface' if row[1] in ('SQ','SF') else 'not_area',
                  'geometry':{'slope_included':row[1] in ('SQ','SF'),'waste_included':False,'apply_slope':False,'apply_waste':False},
                  'work_components':[row[6]],'quote_inclusions':[],'source':field(qty,doc,boxes[i])['source'],'kind':'work'}
            case['lines'].append(line)
        case['groups'].append({'claim_id':'I-'+str(i+1).zfill(3),'title':row[0],'baseline':['B'+str(i+1)],'proposed':['P'+str(i+1)],'roof_location':'main-roof',
                               'change_type':row[7],'mapping_rationale':'The two lines describe the same synthetic operation, location and specification.',
                               'source_ids':['E-BASE','E-PROP','E-NOTES'],'scope_support':{'status':'supported' if row[4] is not None else 'needs_evidence','source_ids':['E-NOTES']},
                               'coverage':{'status':'unknown','source_ids':[],'reviewer':None},'counterargument':row[11],
                               'disposition':'needs_evidence' if row[4] is None else ('retain' if (row[2],row[3])==(row[4],row[5]) else 'candidate_change'),
                               'absence_verified':False,'requested_action':row[8],'observation':row[9],'necessity':row[10],'reply':row[12],'category_ids':row[13]})
    write_json(dest/'case.json',case)
    write_json(dest/'expected.json',data['expected'])
    return dest


if __name__=='__main__':
    for roof,data in SCENARIOS.items():print(build(roof,data))
