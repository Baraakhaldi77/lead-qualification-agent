"""Email composition for tiered lead emails and internal review alerts. See workflows/dispatch_email.md."""

from tools.config import EMAIL_TEMPLATES


def compose_tier_email(lead, label):
    template = EMAIL_TEMPLATES[label]
    return _fill(template["subject"], lead), _fill(template["body"], lead)


def compose_admin_alert(lead, flags):
    subject = f"Lead needs manual review: {lead.get('name') or lead.get('email') or 'unknown'}"
    body = (
        "A new lead submission was flagged and was NOT scored/emailed automatically.\n\n"
        f"Name: {lead.get('name')}\n"
        f"Phone: {lead.get('phone')}\n"
        f"Email: {lead.get('email')}\n"
        f"Flags: {', '.join(flags)}\n\n"
        "Please review this row in the Leads sheet."
    )
    return subject, body


def _fill(text, lead):
    return (
        text.replace("{{name}}", lead.get("name") or "there")
        .replace("{{area}}", lead.get("area") or "your area of interest")
    )
