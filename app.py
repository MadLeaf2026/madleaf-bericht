from flask import Flask, render_template, request, send_file, redirect
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import datetime
import os
from werkzeug.utils import secure_filename
import json
import base64
import textwrap
from PIL import Image

# -------- NUOVI IMPORT EMAIL --------
import smtplib
from email.message import EmailMessage
# -----------------------------------

app = Flask(__name__)

BASE_FOLDER = "C:/Users/peppe/OneDrive/BERICHT_APP"

REPORT_FOLDER = os.path.join(BASE_FOLDER, "reports")
UPLOAD_FOLDER = os.path.join(BASE_FOLDER, "uploads")
SIGNATURE_FOLDER = os.path.join(BASE_FOLDER, "signatures")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SIGNATURE_FOLDER'] = SIGNATURE_FOLDER


# -------- CONFIG EMAIL (AGGIUNTO) --------

SMTP_SERVER = "smtp.udag.de"
SMTP_PORT = 587
EMAIL_ADDRESS = "giuseppe.maddalena@madleaf.de"
EMAIL_PASSWORD = "19Scurcione81!"

# invia copia a te
EMAIL_CC = "giuseppe.maddalena@madleaf.de"

def send_report_email(receiver, pdf_path):

    try:

        msg = EmailMessage()

        msg["Subject"] = "MadLeaf – Arbeitsbericht"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = receiver
        msg["Cc"] = EMAIL_CC

        msg.set_content(
"""Sehr geehrte Damen und Herren,

anbei erhalten Sie den Arbeitsbericht der heutigen Begehung.

Mit freundlichen Grüßen"""
        )

        with open(pdf_path, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(pdf_path)

        msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:

            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email erfolgreich gesendet")

    except Exception as e:

        # NON blocca l'app
        print("Email Fehler:", e)

# -----------------------------------------


for folder in [REPORT_FOLDER, UPLOAD_FOLDER, SIGNATURE_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/bericht", methods=["GET", "POST"])
def bericht():

    try:
        with open('customers.json', 'r') as f:
            customers = json.load(f)
    except:
        customers = []

    if request.method == "POST":

        kunde = request.form.get("kunde")

        kunde_data = None
        for c in customers:
            if c["name"] == kunde:
                kunde_data = c

        beschreibung = request.form["beschreibung"]
        datum = request.form["datum"]
        arbeitszeit = request.form["arbeitszeit"]

        startzeit = request.form.get("startzeit")
        endzeit = request.form.get("endzeit")

        signature_reason = request.form.get("signature_reason")
        signature_name = request.form.get("signature_name")
        photo_comment = request.form.get("photo_comment")

        signature_data = request.form.get("signature_data")
        signature_path = None

        if signature_data and "base64" in signature_data:

            signature_data = signature_data.split(",")[1]
            signature_bytes = base64.b64decode(signature_data)

            signature_filename = f"signature_{datetime.datetime.now().timestamp()}.png"
            signature_path = os.path.join(SIGNATURE_FOLDER, signature_filename)

            with open(signature_path, "wb") as f:
                f.write(signature_bytes)

        photos = request.files.getlist("photos")
        photo_paths = []

        for photo in photos:

            if photo and photo.filename != "":

                filename = secure_filename(photo.filename)

                save_path = os.path.join(
                    UPLOAD_FOLDER,
                    f"{datetime.datetime.now().timestamp()}_{filename}"
                )

                photo.save(save_path)

                try:
                    img = Image.open(save_path)

                    # ---------- COMPRESSIONE MIGLIORATA ----------
                    img.thumbnail((1200,1200))
                    img.save(save_path, optimize=True, quality=55)
                    # --------------------------------------------

                except:
                    pass

                photo_paths.append(save_path)

        safe_kunde = "".join(c for c in kunde if c.isalnum() or c in (" ", "_")).rstrip()
        safe_kunde = safe_kunde.replace(" ", "_")

        customer_folder = os.path.join(REPORT_FOLDER, safe_kunde)

        if not os.path.exists(customer_folder):
            os.makedirs(customer_folder)

        filename = f"MadLeaf_Report_{datum}_{safe_kunde}.pdf"
        filepath = os.path.join(customer_folder, filename)

        # -------- AGGIUNTO: EVITA SOVRASCRITTURA --------
        counter = 1
        while os.path.exists(filepath):
            filename = f"MadLeaf_Report_{datum}_{safe_kunde}_{counter}.pdf"
            filepath = os.path.join(customer_folder, filename)
            counter += 1
        # ------------------------------------------------

        c = canvas.Canvas(filepath, pagesize=A4)

        width, height = A4

        def draw_header(first_page=True):

            logo_path = "static/logo.png"

            if os.path.exists(logo_path):

                if first_page:
                    c.drawImage(logo_path, 50, height - 140, width=260, height=80)
                else:
                    c.drawImage(logo_path, 50, height - 70, width=120, height=35)

            if first_page:

                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, height - 40, "MadLeaf – Arbeitsbericht")

                c.setLineWidth(1)
                c.line(50, height - 50, width - 50, height - 50)

                c.setFont("Helvetica", 10)

                c.drawString(50, height - 150, "Dr. Giuseppe Maddalena")
                c.drawString(50, height - 165, "Applied Entomology & Environmental Risk")
                c.drawString(50, height - 180, "Schillerstraße 8")
                c.drawString(50, height - 195, "79369 Wyhl am Kaiserstuhl")
                c.drawString(50, height - 210, "+49 163 3661630")
                c.drawString(50, height - 225, "giuseppe.maddalena@madleaf.de")

                if kunde_data:

                    right_x = width - 50

                    c.drawRightString(right_x, height - 150, kunde_data.get("name",""))
                    c.drawRightString(right_x, height - 165, kunde_data.get("address",""))
                    c.drawRightString(right_x, height - 180, kunde_data.get("city",""))
                    c.drawRightString(right_x, height - 195, kunde_data.get("email",""))
                    c.drawRightString(right_x, height - 210, kunde_data.get("phone",""))

        def draw_footer():

            c.setFont("Helvetica", 9)
            c.drawString(width/2 - 20, 20, f"Seite {c.getPageNumber()}")

            if os.path.exists("static/Signature_giuseppe.png"):
                c.drawImage(
                    "static/Signature_giuseppe.png",
                    50,
                    30,
                    width=110,
                    height=40,
                    mask='auto'
                )

            if signature_path:
                c.drawImage(
                    signature_path,
                    width - 160,
                    30,
                    width=110,
                    height=40,
                    mask='auto'
                )

        draw_header(True)

        y = height - 260

        c.setFont("Helvetica-Bold", 12)

        c.drawString(50, y, f"Datum: {datum}")
        y -= 20

        c.drawString(50, y, f"Kunde: {kunde}")
        y -= 20

        c.drawString(50, y, f"Arbeitszeit: {arbeitszeit}")
        y -= 20

        if startzeit:
            c.drawString(50, y, f"Arbeitsbeginn: {startzeit}")
            y -= 20

        if endzeit:
            c.drawString(50, y, f"Arbeitsende: {endzeit}")
            y -= 30

        c.setFont("Helvetica", 11)

        lines = []
        for paragraph in beschreibung.split("\n"):
            lines.extend(textwrap.wrap(paragraph, 90))

        for line in lines:

            if y < 120:

                draw_footer()
                c.showPage()
                draw_header(False)

                y = height - 80
                c.setFont("Helvetica", 11)

            c.drawString(50, y, line)
            y -= 15


        # ----------- NUOVO BLOCCO FIRMA MOTIVAZIONE -----------
        if signature_reason:

            y -= 20

            reason_lines = textwrap.wrap(
                f"Keine Unterschrift möglich: {signature_reason}",
                90
            )

            for line in reason_lines:

                if y < 120:

                    draw_footer()
                    c.showPage()
                    draw_header(False)

                    y = height - 80

                c.drawString(50, y, line)
                y -= 15
        # ------------------------------------------------------


        # -------- AGGIUNTO: PAGINA FOTO --------
        if photo_paths:

            draw_footer()
            c.showPage()
            draw_header(False)

            y = height - 120

            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, "Fotodokumentation")

            y -= 40

            for path in photo_paths:

                try:
                    img = Image.open(path)
                    img_width, img_height = img.size
                except:
                    continue

                max_width = 450
                ratio = max_width / img_width

                new_width = max_width
                new_height = img_height * ratio

                if y - new_height < 140:

                    draw_footer()
                    c.showPage()
                    draw_header(False)

                    y = height - 120

                x_position = (width - new_width) / 2

                c.drawImage(
                    path,
                    x_position,
                    y - new_height,
                    width=new_width,
                    height=new_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )

                y -= new_height + 20
        # --------------------------------------


        draw_footer()
        c.save()

        # -------- INVIO EMAIL (AGGIUNTO) --------
        if kunde_data and kunde_data.get("email"):
            send_report_email(kunde_data.get("email"), filepath)
        # ----------------------------------------

        return redirect("/")

    return render_template("bericht.html", customers=customers)


@app.route("/berichte")
def berichte():

    all_files = []

    for root, dirs, files in os.walk(REPORT_FOLDER):
        for f in files:
            if f.endswith(".pdf"):
                all_files.append(f)

    all_files.sort(reverse=True)

    return render_template("berichte.html", files=all_files)


@app.route("/view/<filename>")
def view(filename):

    for root, dirs, files in os.walk(REPORT_FOLDER):
        if filename in files:
            path = os.path.join(root, filename)
            return send_file(path)

    return redirect("/berichte")


@app.route("/download/<filename>")
def download(filename):

    for root, dirs, files in os.walk(REPORT_FOLDER):
        if filename in files:
            path = os.path.join(root, filename)
            return send_file(path, as_attachment=True)

    return redirect("/berichte")


@app.route("/delete_report/<filename>")
def delete_report(filename):

    for root, dirs, files in os.walk(REPORT_FOLDER):
        if filename in files:
            path = os.path.join(root, filename)
            os.remove(path)

    return redirect("/berichte")


@app.route("/add_customer", methods=["POST"])
def add_customer():

    name = request.form["name"]
    address = request.form["address"]
    city = request.form["city"]
    email = request.form["email"]
    phone = request.form["phone"]

    customer_data = {
        "name": name,
        "address": address,
        "city": city,
        "email": email,
        "phone": phone
    }

    try:
        with open('customers.json', 'r') as f:
            customers = json.load(f)
    except:
        customers = []

    customers.append(customer_data)

    with open('customers.json', 'w') as f:
        json.dump(customers, f, indent=4)

    return redirect('/kunden')


@app.route("/kunden")
def kunden():

    try:
        with open('customers.json', 'r') as f:
            customers = json.load(f)
    except:
        customers = []

    return render_template("kunden.html", customers=customers)


@app.route("/delete_customer/<int:index>")
def delete_customer(index):

    try:
        with open('customers.json', 'r') as f:
            customers = json.load(f)
    except:
        customers = []

    if index < len(customers):
        customers.pop(index)

    with open('customers.json', 'w') as f:
        json.dump(customers, f, indent=4)

    return redirect("/kunden")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")