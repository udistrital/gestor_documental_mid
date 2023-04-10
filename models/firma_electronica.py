

import os

from cryptography.fernet import Fernet

# Imports ElectronicSign
from pdfminer.layout import LAParams, LTTextBox
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from reportlab.pdfgen import canvas
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pdfminer.high_level import extract_pages
from textwrap import wrap
import time

os.environ['TZ'] = 'America/Bogota'
time.tzset()


class ElectronicSign:
    """
        Permite el manejo de pdf para estampa la firma electronica en un documento,
        ademas de calcular el espacio necesario para estampar dicha firma con su información.
        También permite la encriptación desincriptación de una firma
    """
    def __init__(self):
        self.YFOOTER = 80
        self.YHEEADER = 100
        key = os.environ['ENCRYPTION_KEY']
        self.fernet = Fernet(key)

    def lastPageItems(self, pdfIn):
        """
            Analiza el pdf para determinar las posiciones de sus elementos
            Parameters
            ----------
            pdfIn : _io.BufferedReader
                pdf abierto en buffer como lectura
           
            Return
            ----------
            list : lista de posiciones en y de cada uno de los elementos de un pdf
        """
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        #pages = PDFPage.get_pages(pdfIn)
        pages = extract_pages(pdfIn)
        pages = list(pages)
        page = pages[len(pages)-1]

        yText = []

        for lobj in page:
            if isinstance(lobj, LTTextBox):
                x, y, text = lobj.bbox[0], lobj.bbox[3], lobj.get_text()
                yText.append(y)

        return yText

    def signPosition(self, pdfIn):
        yText = self.lastPageItems(pdfIn)
        yText.reverse()

        for i in range(1,19):
            if yText[i] > 80:
                y = yText[i]
                break

        return int(y-20)

    def descrypt(self, codigo):
        """
            Desencripta un texto 
            Parameters
            ----------
            codigo : bytes
                codigo en formato bytes encriptado
            Return
            ----------
            bytes : codigo en formato bytes desencriptado
        """
        return self.fernet.decrypt(codigo)

    def hashCode(self, firma):
        """
            Desencripta un texto 
            Parameters
            ----------
            codigo : String
                codigo desencriptado
            Return
            ----------
            bytes : codigo en formato bytes encriptado
        """
        return self.fernet.encrypt(firma.encode())
        
    def signature(self, pdfIn, yPosition, datos):
        """
            Crea el estampado de la firma electronica
            Parameters
            ----------
            pdfIn : _io.BufferedReader
                pdf abierto en buffer como lectura
            yPosition : int
                posición del ultimo elemeento del pdf
            datos : dict
                 diccionario con datos a estampar {tipo_documento, firmantes, representantes, firma, idDoc}

            Return
            ----------
            String : id y firma encriptados
            Boolean : True si se puede estampar en la ultima pagina, False si se debe crear una nueva pagina
        """

        x = 80
        y = yPosition
        signPageSize = 3 + len(datos["firmantes"]) + len(datos["representantes"]) + 2.5 #Espacios

        wraped_firmantes = []
        for firmante in datos["firmantes"]:
            text = firmante["cargo"] + ": " + firmante["nombre"] + ". " + firmante["tipoId"] + " " + firmante["identificacion"]
            text = "\n".join(wrap(text, 60))
            signPageSize += text.count("\n")
            wraped_firmantes.append(text)

        wraped_representantes = []
        for representante in datos["representantes"]:
            text = representante["cargo"] + ": " + representante["nombre"] + ". " + representante["tipoId"] + " " + representante["identificacion"]
            text = "\n".join(wrap(text, 60))
            text.count("\n")
            signPageSize += text.count("\n")
            wraped_representantes.append(text)

        firmaID = str(datos["idDoc"]) + "/////" + datos["firma"]

        firma = self.hashCode(firmaID).decode()

        wraped_firma = "\n".join(wrap(firma, 60))
  
        signPageSize += wraped_firma.count("\n")

        signPageSize *= 10



        if(yPosition - self.YFOOTER < signPageSize):
            y = int(PdfFileReader(pdfIn).getPage(0).mediabox[3] - self.YHEEADER)


        c = canvas.Canvas('documents/signature.pdf')
        # Create the signPdf from an image
        # c = canvas.Canvas('signPdf.pdf')

        # Draw the image at x, y. I positioned the x,y to be where i like here
        # c.drawImage('test.png', 15, 720)
        pdfmetrics.registerFont(TTFont('Vera', 'Vera.ttf'))
        pdfmetrics.registerFont(TTFont('VeraBd', 'VeraBd.ttf'))

        c.setFont('VeraBd', 10)
        y = y - 10
        c.drawString(x + 20, y,"Firmado Digitalmente")
        
        c.setFont('Vera', 8)
        t = c.beginText()
        


        if len(datos["firmantes"]) > 1:
            t.setFont('VeraBd', 8)
            y = y - 15
            t.setTextOrigin(x, y)
            t.textLine("Firmantes:")
        elif len(datos["firmantes"]) == 1:
            t.setFont('VeraBd', 8)
            y = y - 15
            t.setTextOrigin(x, y)
            t.textLine("Firmante:")


        count = 1
        t.setFont('Vera', 8)
        for firmante in wraped_firmantes:
            if(count > 1):
                y = y - 10
            t.setTextOrigin(x+140,y)
            t.textLines(firmante)
            y = y-firmante.count("\n")*10
            count += 1

        if len(wraped_firmantes):
            y = y - 5

        if len(datos["representantes"]) > 1:
            t.setFont('VeraBd', 8)
            y = y - 10
            t.setTextOrigin(x, y)
            t.textLine("Representantes:")
        elif len(datos["representantes"]) == 1:
            t.setFont('VeraBd', 8)
            y = y - 10
            t.setTextOrigin(x, y)
            t.textLine("Representante:")

        count = 1
        t.setFont('Vera', 8)
        for representante in wraped_representantes:
            if(count > 1):
                y = y - 10
            t.setTextOrigin(x+140,y)
            t.textLines(representante)
            y = y-representante.count("\n")*10
            count += 1

        if len(wraped_representantes):
            y = y - 5

        t.setFont('VeraBd', 8)
        y = y - 10
        t.setTextOrigin(x, y)
        t.textLine("Tipo de documento:")
        t.setFont('Vera', 8)
        t.setTextOrigin(x+140, y)
        t.textLine(datos["tipo_documento"])

        y = y - 5

        t.setFont('VeraBd', 8)
        y = y - 10
        t.setTextOrigin(x, y)
        t.textLine("Firma electrónica:")
        t.setFont('Vera', 8)
        t.setTextOrigin(x+140, y)
        t.textLines(wraped_firma)

        y = y - 5

        t.setFont('VeraBd', 8)
        y = y - 10 - wraped_firma.count("\n")*10
        t.setTextOrigin(x, y)
        t.textLine("Fecha y hora:")
        t.setFont('Vera', 8)
        fechaHoraActual = time.strftime("%x") + " " + time.strftime("%X")
        t.setTextOrigin(x+140, y)
        t.textLine(fechaHoraActual)

        c.drawText(t)
        c.showPage()
        c.save()

        if(yPosition - self.YFOOTER > signPageSize):
            return firma, True
        else:
            return firma, False
 
    def estamparUltimaPagina(self, pdfIn):

        """
            Estampa la firma en la ultima pagina del cocumento ya existente
            Parameters
            ----------
            pdfIn : _io.BufferedReader
                pdf abierto en buffer como lectura
        """

        signPdf = PdfFileReader(open("documents/signature.pdf", "rb"))
        documentPdf = PdfFileReader(pdfIn)
        
        # Get our files ready
        output_file = PdfFileWriter()

        # Number of pages in input document
        page_count = documentPdf.getNumPages()

        for page_number in range(page_count-1):
            input_page = documentPdf.getPage(page_number)
            output_file.addPage(input_page)

        input_page = documentPdf.getPage(page_count-1)
        input_page.mergePage(signPdf.getPage(0))
        output_file.addPage(input_page)

        with open("documents/documentSigned.pdf", "wb") as outputStream:
            output_file.write(outputStream)

    def estamparNuevaPagina(self, pdfIn):
        """
            Crea una nueva pagina y la estampa para ser unida con el pdf

            Parameters
            ----------
            pdfIn : _io.BufferedReader
                pdf abierto en buffer como lectura
        """
        signPdf = PdfFileReader(open("documents/signature.pdf", "rb"))
        documentPdf = PdfFileReader(pdfIn)

        # Get our files ready
        output_file = PdfFileWriter()

        # Number of pages in input document
        page_count = documentPdf.getNumPages()

        for page_number in range(page_count):
            input_page = documentPdf.getPage(page_number)
            output_file.addPage(input_page)

        
        output_file.addBlankPage()
        output_file.getPage(output_file.getNumPages()-1).mergePage(signPdf.getPage(0))

        with open("documents/documentSigned.pdf", "wb") as outputStream:
            output_file.write(outputStream)


    def estamparFirmaElectronica(self, datos):
        """
            Metodo principal para el proceso de estampado

            Parameters
            ----------
            datos : dict
                diccionario con datos a estampar {tipo_documento, firmantes, representantes, firma, idDoc}

            Returns
            -------
            firmaEncriptada : String
                firma con id encriptadas en un solo texto
        """
        pdfIn = open("documents/documentToSign.pdf","rb")
        yPosition = self.signPosition(pdfIn)
        firmaEncriptada, suficienteEspacio = self.signature(pdfIn, yPosition, datos)

        if suficienteEspacio:
            self.estamparUltimaPagina(pdfIn)
        else:
            self.estamparNuevaPagina(pdfIn)

        return firmaEncriptada

    #_________________________________________