"""
translations.py
------------------
Multi-language reminder drafting. Static, hand-written templates for now
(no AWS needed) — once the live agent is connected to Bedrock, this can
be extended to translate into ANY language on the fly via the LLM instead
of a fixed template set. For now this covers English, Spanish, French,
and Hindi, which is enough to demonstrate the capability.
"""

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
}

TEMPLATES = {
    "en": {
        "gentle": (
            "Subject: Friendly reminder — Invoice {invoice_number}\n\n"
            "Hi {customer},\n\n"
            "Just a quick note — invoice {invoice_number} for {amount} was due on {due_date} "
            "and it looks like it hasn't been settled yet. No rush, just flagging it in case "
            "it slipped through. Let me know if you need another copy of the invoice.\n\n"
            "Thanks!"
        ),
        "polite_followup": (
            "Subject: Following up — Invoice {invoice_number} ({days_overdue} days overdue)\n\n"
            "Hi {customer},\n\n"
            "Following up on invoice {invoice_number} for {amount}, which was due on {due_date} "
            "and is now {days_overdue} days overdue. Could you let me know the expected payment date? "
            "Happy to answer any questions about the invoice.\n\n"
            "Thanks for your help."
        ),
        "firm": (
            "Subject: Action needed — Invoice {invoice_number} significantly overdue\n\n"
            "Hi {customer},\n\n"
            "Invoice {invoice_number} for {amount} is now {days_overdue} days past its due date "
            "of {due_date}. This is the third follow-up on this invoice. Please arrange payment "
            "at your earliest convenience, or let me know immediately if there's an issue "
            "preventing payment so we can resolve it.\n\n"
            "Please treat this as a priority."
        ),
        "urgent": (
            "Subject: URGENT — Invoice {invoice_number} — {days_overdue} days overdue\n\n"
            "Hi {customer},\n\n"
            "Invoice {invoice_number} for {amount} remains unpaid, {days_overdue} days past the "
            "due date of {due_date}. Despite previous reminders, we have not received payment or "
            "a response. Please settle this invoice immediately or contact us to discuss a payment "
            "plan. Continued non-payment may require us to escalate this further.\n\n"
            "We'd much rather resolve this directly — please reach out as soon as possible."
        ),
    },
    "es": {
        "gentle": (
            "Asunto: Recordatorio amistoso — Factura {invoice_number}\n\n"
            "Hola {customer},\n\n"
            "Solo un breve recordatorio: la factura {invoice_number} por {amount} venció el {due_date} "
            "y parece que aún no se ha pagado. No hay prisa, solo quería mencionarlo por si se "
            "pasó por alto. Avísame si necesitas otra copia de la factura.\n\n"
            "¡Gracias!"
        ),
        "polite_followup": (
            "Asunto: Seguimiento — Factura {invoice_number} ({days_overdue} días de retraso)\n\n"
            "Hola {customer},\n\n"
            "Le escribo para dar seguimiento a la factura {invoice_number} por {amount}, que venció "
            "el {due_date} y ahora tiene {days_overdue} días de retraso. ¿Podría indicarme la fecha "
            "estimada de pago? Con gusto respondo cualquier pregunta sobre la factura.\n\n"
            "Gracias por su ayuda."
        ),
        "firm": (
            "Asunto: Acción requerida — Factura {invoice_number} muy atrasada\n\n"
            "Hola {customer},\n\n"
            "La factura {invoice_number} por {amount} ahora tiene {days_overdue} días de retraso "
            "desde su vencimiento el {due_date}. Este es el tercer seguimiento sobre esta factura. "
            "Por favor, gestione el pago lo antes posible, o avíseme de inmediato si hay algún "
            "problema que impida el pago.\n\n"
            "Por favor, trate esto como prioritario."
        ),
        "urgent": (
            "Asunto: URGENTE — Factura {invoice_number} — {days_overdue} días de retraso\n\n"
            "Hola {customer},\n\n"
            "La factura {invoice_number} por {amount} sigue sin pagarse, {days_overdue} días "
            "después de la fecha de vencimiento del {due_date}. A pesar de los recordatorios "
            "anteriores, no hemos recibido el pago ni una respuesta. Por favor, liquide esta "
            "factura de inmediato o contáctenos para discutir un plan de pago.\n\n"
            "Preferiríamos resolver esto directamente — por favor, contáctenos lo antes posible."
        ),
    },
    "fr": {
        "gentle": (
            "Objet : Petit rappel amical — Facture {invoice_number}\n\n"
            "Bonjour {customer},\n\n"
            "Juste un petit mot — la facture {invoice_number} d'un montant de {amount} était due "
            "le {due_date} et il semble qu'elle n'ait pas encore été réglée. Pas de panique, je "
            "voulais simplement le signaler. Faites-moi savoir si vous avez besoin d'une nouvelle "
            "copie de la facture.\n\n"
            "Merci !"
        ),
        "polite_followup": (
            "Objet : Relance — Facture {invoice_number} ({days_overdue} jours de retard)\n\n"
            "Bonjour {customer},\n\n"
            "Je fais suite à la facture {invoice_number} d'un montant de {amount}, échue le "
            "{due_date} et désormais en retard de {days_overdue} jours. Pourriez-vous m'indiquer "
            "la date de paiement prévue ?\n\n"
            "Merci pour votre aide."
        ),
        "firm": (
            "Objet : Action requise — Facture {invoice_number} très en retard\n\n"
            "Bonjour {customer},\n\n"
            "La facture {invoice_number} d'un montant de {amount} a désormais {days_overdue} jours "
            "de retard par rapport à sa date d'échéance du {due_date}. Ceci est la troisième "
            "relance concernant cette facture. Merci de régler ce paiement dans les plus brefs "
            "délais.\n\n"
            "Merci de considérer ceci comme prioritaire."
        ),
        "urgent": (
            "Objet : URGENT — Facture {invoice_number} — {days_overdue} jours de retard\n\n"
            "Bonjour {customer},\n\n"
            "La facture {invoice_number} d'un montant de {amount} reste impayée, {days_overdue} "
            "jours après la date d'échéance du {due_date}. Malgré les relances précédentes, nous "
            "n'avons reçu ni paiement ni réponse. Merci de régler cette facture immédiatement.\n\n"
            "Nous préférerions résoudre cela directement — merci de nous contacter dès que possible."
        ),
    },
    "hi": {
        "gentle": (
            "विषय: सौहार्दपूर्ण अनुस्मारक — चालान {invoice_number}\n\n"
            "नमस्ते {customer},\n\n"
            "बस एक छोटी याद दिला रहा हूँ — चालान {invoice_number} जिसकी राशि {amount} है, "
            "{due_date} को देय थी और अभी तक भुगतान नहीं हुआ लगता। कोई जल्दी नहीं है, बस ध्यान "
            "में लाना चाहता था। चालान की एक और प्रति चाहिए तो बताइए।\n\n"
            "धन्यवाद!"
        ),
        "polite_followup": (
            "विषय: फॉलो-अप — चालान {invoice_number} ({days_overdue} दिन देर से)\n\n"
            "नमस्ते {customer},\n\n"
            "चालान {invoice_number} (राशि {amount}) के संबंध में फॉलो-अप कर रहा हूँ, जो {due_date} "
            "को देय थी और अब {days_overdue} दिन देर हो चुकी है। क्या अनुमानित भुगतान तिथि बता सकते हैं?\n\n"
            "आपकी मदद के लिए धन्यवाद।"
        ),
        "firm": (
            "विषय: कार्रवाई आवश्यक — चालान {invoice_number} काफी देर से\n\n"
            "नमस्ते {customer},\n\n"
            "चालान {invoice_number} (राशि {amount}) अपनी देय तिथि {due_date} से अब {days_overdue} "
            "दिन देर हो चुकी है। यह इस चालान पर तीसरा फॉलो-अप है। कृपया जल्द भुगतान की व्यवस्था करें।\n\n"
            "कृपया इसे प्राथमिकता के रूप में लें।"
        ),
        "urgent": (
            "विषय: अत्यावश्यक — चालान {invoice_number} — {days_overdue} दिन देर से\n\n"
            "नमस्ते {customer},\n\n"
            "चालान {invoice_number} (राशि {amount}) अभी भी अवैतनिक है, देय तिथि {due_date} से "
            "{days_overdue} दिन बाद भी। कृपया इसका तुरंत भुगतान करें या भुगतान योजना पर चर्चा के "
            "लिए संपर्क करें।\n\n"
            "हम इसे सीधे हल करना पसंद करेंगे — कृपया जल्द संपर्क करें।"
        ),
    },
}


def draft_reminder_multilingual(customer: str, invoice_number: str, amount: float,
                                 due_date: str, days_overdue: int, tier: str,
                                 language: str = "en") -> str:
    """Same as reminder_writer.draft_reminder, but picks the template set for `language`."""
    lang = language if language in TEMPLATES else "en"
    lang_templates = TEMPLATES[lang]

    if tier not in lang_templates:
        return f"No reminder needed — invoice {invoice_number} is not overdue."

    return lang_templates[tier].format(
        customer=customer,
        invoice_number=invoice_number,
        amount=f"₹{amount:,.2f}",
        due_date=due_date,
        days_overdue=days_overdue,
    )
