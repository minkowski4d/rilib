#!/usr/bin/env python
# -*- coding: UTF-8 -*-


from datetime import datetime, date
import pandas as pd
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT,TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle

# Modify "Headings3" to remove italics
styles = getSampleStyleSheet()
# Styles for text
bold_style = styles["Heading3"]
bold_style.alignment = 0  # Left align
normal_style = styles["Normal"]
styles.add(ParagraphStyle(
    name="Headings3",
    parent=styles["Heading3"],  # Inherit properties from Heading2
    fontName="Helvetica-Bold",  # Change from italic to bold (or use "Helvetica" for normal weight)
    fontSize=12,  # Adjust size if needed
    leading=14,  # Adjust line spacing
    spaceAfter=10,  # Adjust spacing after the heading
))

styles["Heading3"].fontName = "Helvetica-Bold" 

# Logo Info
logo_path = "/Users/fabioballoni/Documents/Acct_Statement/tr_logo.png"  # Replace with the actual path to your logo

# Additional styles:
# Define styles for left and right-aligned text
left_aligned_style = ParagraphStyle(name="LeftAligned", parent=styles["Normal"], alignment=TA_LEFT)
right_aligned_style = ParagraphStyle(name="RightAligned", parent=styles["Normal"], alignment=TA_RIGHT)

# Define styles with smaller font size
small_left_style = ParagraphStyle(name="SmallLeft", fontName="Helvetica", fontSize=7, leading=9, alignment=TA_LEFT)
small_right_style = ParagraphStyle(name="SmallRight", fontName="Helvetica", fontSize=7, leading=9, alignment=TA_RIGHT)

# Create left and right-aligned text
left_text = Paragraph("Left Aligned Text", left_aligned_style)
right_text = Paragraph("Right Aligned Text", right_aligned_style)


# Account dependent variables
pages_tot=41 


def create_pdf(report_date,acct):

    # Set Report Date:
    rep_date_str = report_date.strftime("%d.%m.%Y")

    # Create the PDF document
    pdf_filename = "/Users/fabioballoni/Documents/Acct_Statement/%s_depot_%s_prudent.pdf"%(report_date.strftime("%Y%m%d"),acct)
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4)

    # Define table header data (right-aligned)
    table_header_data = [
        [Paragraph("SEITE", small_left_style), Paragraph("1 von %s"%pages_tot, small_right_style)],
        [Paragraph("DATUM", small_left_style), Paragraph(rep_date_str, small_right_style)],
        [Paragraph("DEPOT", small_left_style), Paragraph(str(acct), small_right_style)]
    ]

    # Define table width
    table_header_width = 175  # Adjust as needed

    # Create the table
    table_header = Table(table_header_data, colWidths=[40, 80])  # Column widths adjusted
    table_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Left align first column
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Right align second column
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to top
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 4),  # Set font size
        ('TOPPADDING', (0, 0), (-1, -1), 0),  # Reduce padding top
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),  # Reduce padding bottom
        ('BOX', (0, 0), (-1, -1), 0, colors.white),  # Remove border
        ('INNERGRID', (0, 0), (-1, -1), 0, colors.white)  # Remove inner grid
    ]))

    # Add a spacer to move the table to the right side of the page
    right_offset = A4[0] - table_header_width - 50  # Align table to right margin (adjust padding)
    table_header_wrapper = Table([[Spacer(1, 1), table_header]], colWidths=[right_offset, table_header_width])

    # Get Data
    df_data, tot_eur = get_data(report_date,acct)
    data = [list(df_data.columns)]
    for _, row in df_data.iterrows():
        formatted_row = [
            row["STK. / NOMINALE"],
            format_column2(row["WERTPAPIERBEZEICHNUNG"]),  # Apply formatting
            row["KURS PRO STÜCK"],
            row["KURSWERT IN EUR"]
        ]
        data.append(formatted_row)

    # Adding Footer Row:
    positions_count = len(df_data)    
                     
    footer_left = Paragraph(
        f"<b>ANZAHL POSITIONEN: {positions_count:,}</b>".replace(",", "."),
        small_left_style
    )
    footer_right = Paragraph(f"<b>{format_eur(tot_eur)} EUR</b>", small_right_style)

    # empty first column, label in second, total in last
    data.append(["", footer_left, "", footer_right])


    # Create a trading book position table
    table_tr = Table(data, colWidths=[75, 235, 70, 70])
    table_tr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),  # Header background color
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Header text color
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Align text to left
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),  # Align all columns to top
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),  # Header font
        ('FONTSIZE', (0, 0), (-1, 0), 6),  # Header font size
        ('FONTSIZE', (0, 1), (-1, -1), 8),  # Table body font size
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),  # Padding for header
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),  # Line below header
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Keep table body white
        ('BOX', (0, 0), (-1, -1), 0, colors.white),  # Remove outer box/frame
        ('INNERGRID', (0, 0), (-1, 0), 0, colors.white),  # Remove all internal grid lines in header
        ('INNERGRID', (0, 1), (-1, -1), 0, colors.white), # Remove all internal grid lines in body
        # ----- footer row (last row: -1) -----
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('SPAN', (1, -1), (2, -1)),                    # merge cols 1..2 for the label
        ('ALIGN', (1, -1), (2, -1), 'LEFT'),
        ('ALIGN', (3, -1), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 6),
        ('TOPPADDING', (0, -1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 4),
        ('BACKGROUND', (3, -1), (3, -1), colors.white),  # green box
        ('TEXTCOLOR', (3, -1), (3, -1), colors.black),
    ]))

    # Build the PDF content
    content = [
        Paragraph("TRADE REPUBLIC", bold_style),
        Paragraph('<font size="7">TRADE REPUBLIC BANK GMBH    BRUNNENSTRASSE 19-21    10119 BERLIN</font>', normal_style),
        Spacer(1, 12),
        Paragraph('<font size="7"><b>TRADE REPUBLIC BANK GMBH</b><br/>Köpenicker Strasse 40C<br/>10179 Berlin</font>', normal_style),
        Spacer(1, 5),
        table_header_wrapper,
        Spacer(1, 8),
        Paragraph('<b>DEPOTAUSZUG</b><br/><font size="9">zum 30.09.2025</font>', right_aligned_style),
        Spacer(1, 12),
        Paragraph("POSITIONEN", bold_style),
        Paragraph("Aufstellung über die Wertpapiere in Deinem Depot %s zum 30.09.2025."%acct, normal_style),
        Spacer(1, 12),
        table_tr
    ]

    # Build the PDF
    doc.build(content, onFirstPage=add_background)

    print(f"PDF '{pdf_filename}' has been created successfully!")


def format_eur(v):
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234,56


def format_column2(text):
    
    """Formats the second column to make the first two lines bold."""

    # Define styles for bold and normal text with custom font and size
    normal_style = ParagraphStyle(name="NormalStyle", fontName="Helvetica", fontSize=8, leading=10)  # Normal with size 8

    lines = text.split("\n")  # Split text by new lines
    if len(lines) >= 2:
        bold_text = f"<b>{lines[0]}<br/>{lines[1]}</b>"  # Make first two lines bold
        normal_text = "<br/>".join(lines[2:])  # Keep remaining lines normal
        formatted_text = f"{bold_text}<br/>{normal_text}" if normal_text else bold_text
    else:
        formatted_text = f"<b>{text}</b>"  # If only one line, just bold it

    return Paragraph(formatted_text, normal_style)



def add_background(canvas, doc):
    """Function to add a logo behind the header"""
    logo_width = 19.95  # Adjust width
    logo_height = 19.475  # Adjust height
    x_position = 185  # Adjust horizontal position
    y_position = A4[1] - 95  # Adjust vertical position

    canvas.drawImage(logo_path, x_position, y_position, width=logo_width, height=logo_height, mask='auto')



def get_data(report_date,acct):

    df = pd.read_csv('~/Documents/Acct_Statement/account_balances/20250930_%s_positions.csv'%acct)
    
    df = df[df.mkt_eur_prudent!=0]
    df = df[~df.mkt_eur_prudent.isnull()]
    df = df[df.quantity!=0]
    df = df[['quantity','name_short','instrument_type','instrument_id','ask_price','bid_price','mkt_eur_prudent']]
    df['instrument_id']=df['instrument_id'].apply(lambda x: x)

    tot_eur=df.mkt_eur_prudent.sum()
    print(tot_eur)

    # Calculate Prudent Price
    df['prudent_price'] = df[['ask_price','bid_price', 'quantity']].apply(lambda row: row['ask_price'] if row['quantity'] < 0 else row['bid_price'], axis=1)

    # Format Columns:
    # Adjust Name
    # df['name_short']=df['name_short'].apply(lambda x: '<b>' + str(x) + '</b>')
    df['name_short']=df.name_short.replace(np.nan, '[...]',regex=True)
    df['name_short']=df['name_short'].apply(lambda x: x)
    

    # Adjust quantity
    df['STK. / NOMINALE']=df['quantity'].apply(lambda x: str(np.round(x,6)).replace('.',',')+' Stk.')

    # Adjust Instrument Type
    #df['instrument_type']=df['instrument_type'].map({'BOND':'<b>Anleihe</b>','STOCK':'<b>Aktie</b>','FUND':'<b>Exchange Traded Fund (ETF)</b>'})
    df['instrument_type']=df['instrument_type'].map({'BOND':'Anleihe',
                                                     'STOCK':'Aktie',
                                                     'FUND':'Exchange Traded Fund (ETF)',
                                                     'FX':'FX Spot'})

    # Adjust ISIN Name
    df['instrument_id']=df['instrument_id'].apply(lambda x: 'ISIN: '+str(x))

    # Adjust Valuation
    df['prudent_price']=df['prudent_price'].apply(lambda x: str(np.round(x,2)).replace('.',','))
    df['KURSWERT IN EUR']=df['mkt_eur_prudent'].apply(lambda x: str(np.round(x,2)).replace('.',','))

    # Add Date
    df['valuation_date']=report_date.strftime("%d.%m.%Y")

    # Combine Description Column
    df['WERTPAPIERBEZEICHNUNG']=df[['name_short', 'instrument_type', 'instrument_id']].apply(lambda x: '\n'.join(x), axis=1)
    df['KURS PRO STÜCK']=df[['prudent_price', 'valuation_date']].apply(lambda x: '\n'.join(x), axis=1)

    out = df[['STK. / NOMINALE', 'WERTPAPIERBEZEICHNUNG', 'KURS PRO STÜCK', 'KURSWERT IN EUR']]



    return out,tot_eur