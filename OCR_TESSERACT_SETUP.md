# OCR mit Tesseract einrichten

Die App kann digitale PDFs direkt mit `pdfplumber` auslesen. Für gescannte PDFs oder Bilder braucht sie zusätzlich OCR.

## Windows

1. Tesseract OCR installieren.
2. Den Installationsordner, z. B. `C:\Program Files\Tesseract-OCR`, zum Windows-PATH hinzufügen.
3. Deutsche Sprachdatei `deu.traineddata` installieren, falls nicht enthalten.
4. Optional Poppler installieren und zum PATH hinzufügen, damit gescannte PDF-Seiten in Bilder umgewandelt werden können.
5. Danach prüfen:

```bat
tesseract --version
python -c "import pytesseract; print('pytesseract OK')"
```

## Verhalten in der App

- Digitale PDF: Text wird direkt gelesen.
- Gescannte PDF: Fallback über `pdf2image` + Tesseract.
- JPG/PNG: direkte OCR über Tesseract.
- Wenn Tesseract fehlt, bleibt die App lauffähig, zeigt aber eine Warnung.

## Wichtig

OCR ist nie hundertprozentig zuverlässig. Rechnungen, Beträge, IBANs und Kundendaten müssen bei unsicherer Erkennung manuell geprüft werden.
