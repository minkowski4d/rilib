from lxml import etree
from utils.irrbb_cell_mapping import CELL_MAPPING
from typing import List

def element(ns, name):
    return etree.Element(etree.QName(ns, name))


def explicit_member(dimension, field):
    NS = "http://xbrl.org/2006/xbrldi"
    e = element(NS, "explicitMember")
    e.set("dimension", "eba_dim:" + dimension)
    e.text = "eba_" + field
    return e


def scenario(dimensions):
    NS = "http://www.xbrl.org/2003/instance"
    e = element(NS, "scenario")
    for dim in dimensions:
        m = explicit_member(dim[0], dim[1])
        e.append(m)
    return e


# period expected in format YYYY-MM-DD
def period(period):
    NS = "http://www.xbrl.org/2003/instance"
    e = element(NS, "period")
    c = element(NS, "instant")
    c.text = period
    e.append(c)
    return e


def entity_ident(creditorNumber):
    NS = "http://www.xbrl.org/2003/instance"
    e = element(NS, "entity")
    i = element(NS, "identifier")
    i.set("scheme", "https://eurofiling.info/eu/rs")
    i.text = creditorNumber
    e.append(i)
    return e


def base_context(cid, creditorNumber, pPeriod):
    NS = "http://www.xbrl.org/2003/instance"
    c = element(NS, "context")
    c.set("id", cid)
    e = entity_ident(creditorNumber)
    p = period(pPeriod)
    c.append(e)
    c.append(p)
    return c


def context(cid, creditorNumber, pPeriod, dimensions):
    c = base_context(cid, creditorNumber, pPeriod)
    s = scenario(dimensions)
    c.append(s)
    return c


def filingIndicator(cid, filed, report):
    NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"
    e = element(NS, "filingIndicator")
    e.set("contextRef", cid)
    e.set("{" + NS + "}" + "filed", filed)
    e.text = report
    return e


def fIndicators(cid, reports):
    NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"
    f = element(NS, "fIndicators")
    for report in reports:
        fi = filingIndicator(cid, report[1], report[0])
        f.append(fi)
    return f


def unit(uid, unit):
    NS = "http://www.xbrl.org/2003/instance"
    m = element(NS, "measure")
    m.text = unit
    u = element(NS, "unit")
    u.set("id", uid)
    u.append(m)
    return u


def metric(metric, cid, decimals, uid, value):
    NS = "http://www.eba.europa.eu/xbrl/crr/dict/met"
    e = element(NS, metric)
    e.set("contextRef", cid)
    if uid is not None:
        e.set("unitRef", uid)
        e.set("decimals", decimals)
    e.text = str(value)
    return e


def de_external_metric(metric, cid, value):
    NS = "http://www.bundesbank.de/xbrl/dict/met"
    NS_ref = "{http://www.xbrl.org/2003/instance}"
    e = element(NS, metric)
    e.set(NS_ref + "contextRef", cid)
    e.text = value
    return e


def schema_ref(href):
    NS = "http://www.xbrl.org/2003/linkbase"
    NS_xlink = "{http://www.w3.org/1999/xlink}"
    e = element(NS, "schemaRef")
    e.set(NS_xlink + "type", "simple")
    e.set(NS_xlink + "href", href)
    return e


def get_unit_ref(dimension_list:List[str]) -> str:
    # Check the beginning of dimension_list[0] to determine the unit
    if dimension_list[0].startswith("mi"):
        unit_ref = "uEUR"
    elif (
        dimension_list[0].startswith("ri") or 
        dimension_list[0].startswith("ii") or 
        dimension_list[0].startswith("pi") or 
        dimension_list[0].startswith("si")
    ):
        unit_ref = "uPURE"
    else: # if the dimension starts with 'ei', then it's a string and shouldn't have a unit
        unit_ref = None
    
    return unit_ref


def get_decimal(unit_ref):
    # The logic was extracted from the sample file from EBA
    if unit_ref == "uEUR":
        return -3
    elif unit_ref == "uPURE":
        return 4
    else:
        return None


# Function to get cell mapping value based on idx and group_1, using the specified report key
def get_mapping(row, report):
    key = (row['idx'], row['group_1'])
    return CELL_MAPPING.get(report, {}).get(key, None)  # Returns None if key not found
