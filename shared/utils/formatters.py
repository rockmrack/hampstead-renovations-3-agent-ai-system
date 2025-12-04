"""
Hampstead Renovations - Text Formatters
========================================

Functions for formatting messages, emails, and documents.
"""

import re
from datetime import datetime
from typing import Any, Optional

from .validators import (
    format_currency,
    format_date_uk,
    format_phone_display,
    title_case_name,
)


# =============================================================================
# MESSAGE TEMPLATES
# =============================================================================


def format_slack_lead_notification(
    name: str,
    service_type: str,
    location: str,
    budget_band: str,
    timeline: str,
    score: int,
    priority: str,
    source: str,
    hubspot_url: Optional[str] = None,
    message_preview: Optional[str] = None,
) -> str:
    """
    Format a Slack notification for a new lead.
    """
    priority_emoji = {
        "hot": "🔥",
        "warm": "🟡",
        "cool": "🔵",
        "cold": "❄️",
    }.get(priority, "⚪")

    service_display = service_type.replace("-", " ").title() if service_type else "Not specified"
    budget_display = budget_band.replace("-", " to £").replace("under", "Under £").replace("over", "Over £") if budget_band else "Not specified"

    blocks = [
        f"{priority_emoji} *New Lead - {priority.upper()}*",
        "",
        f"*Name:* {name}",
        f"*Service:* {service_display}",
        f"*Location:* {location or 'Not specified'}",
        f"*Budget:* {budget_display}",
        f"*Timeline:* {timeline.replace('-', ' ') if timeline else 'Not specified'}",
        f"*Score:* {score}/100",
        f"*Source:* {source.replace('-', ' ').title() if source else 'Unknown'}",
    ]

    if message_preview:
        preview = message_preview[:200] + "..." if len(message_preview) > 200 else message_preview
        blocks.extend(["", f"_\"{preview}\"_"])

    if hubspot_url:
        blocks.extend(["", f"<{hubspot_url}|View in HubSpot>"])

    return "\n".join(blocks)


def format_slack_deal_won(
    name: str,
    service_type: str,
    amount: float,
    location: str,
    project_manager: Optional[str] = None,
) -> str:
    """
    Format a Slack celebration notification for a won deal.
    """
    service_display = service_type.replace("-", " ").title() if service_type else "Renovation"

    blocks = [
        "🎉 *DEAL WON!* 🎉",
        "",
        f"*Client:* {name}",
        f"*Project:* {service_display}",
        f"*Location:* {location}",
        f"*Value:* {format_currency(amount)}",
    ]

    if project_manager:
        blocks.append(f"*Project Manager:* {project_manager}")

    blocks.extend([
        "",
        "Congratulations team! 🏠✨",
    ])

    return "\n".join(blocks)


def format_slack_pipeline_report(
    total_leads: int,
    total_value: float,
    stage_breakdown: dict[str, dict[str, Any]],
    hot_leads: int,
    deals_won_this_month: int,
    deals_lost_this_month: int,
) -> str:
    """
    Format a daily/weekly pipeline report for Slack.
    """
    win_rate = (
        deals_won_this_month / (deals_won_this_month + deals_lost_this_month) * 100
        if (deals_won_this_month + deals_lost_this_month) > 0
        else 0
    )

    blocks = [
        "📊 *Pipeline Report*",
        f"_Generated {format_date_uk(datetime.now())}_",
        "",
        "*Summary*",
        f"• Active Leads: {total_leads}",
        f"• Pipeline Value: {format_currency(total_value)}",
        f"• Hot Leads: {hot_leads} 🔥",
        f"• This Month: {deals_won_this_month} won, {deals_lost_this_month} lost ({win_rate:.0f}% win rate)",
        "",
        "*By Stage*",
    ]

    for stage, data in stage_breakdown.items():
        stage_display = stage.replace("-", " ").title()
        count = data.get("count", 0)
        value = data.get("value", 0)
        blocks.append(f"• {stage_display}: {count} ({format_currency(value)})")

    return "\n".join(blocks)


# =============================================================================
# EMAIL FORMATTERS
# =============================================================================


def format_email_subject(template: str, **kwargs: Any) -> str:
    """
    Format an email subject line with dynamic values.

    Args:
        template: Subject template with {placeholders}
        **kwargs: Values to substitute

    Returns:
        Formatted subject line (max 60 chars for preview)
    """
    subject = template.format(**kwargs)
    # Trim to 60 chars for email preview
    if len(subject) > 60:
        subject = subject[:57] + "..."
    return subject


def format_email_greeting(name: str, time_of_day: Optional[str] = None) -> str:
    """
    Format an email greeting based on time of day.

    Args:
        name: Recipient's name
        time_of_day: "morning", "afternoon", "evening", or None for auto

    Returns:
        Greeting like "Good morning John,"
    """
    if time_of_day is None:
        hour = datetime.now().hour
        if hour < 12:
            time_of_day = "morning"
        elif hour < 17:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"

    first_name = name.split()[0] if name else "there"
    first_name = title_case_name(first_name)

    return f"Good {time_of_day} {first_name},"


def format_quote_email_body(
    name: str,
    service_type: str,
    quote_amount: float,
    quote_number: str,
    valid_until: datetime,
    project_duration: Optional[str] = None,
) -> str:
    """
    Format the body of a quote delivery email.
    """
    first_name = name.split()[0] if name else "there"
    service_display = service_type.replace("-", " ") if service_type else "renovation"

    body = f"""Thank you for taking the time to discuss your {service_display} project with us. It was great to meet you and see your property.

Please find attached our detailed quotation ({quote_number}) for the works we discussed. The quote totals {format_currency(quote_amount)} including VAT.

"""

    if project_duration:
        body += f"Based on our survey, we estimate the project would take approximately {project_duration} to complete.\n\n"

    body += f"""This quote is valid until {format_date_uk(valid_until, include_day=False)}.

Please don't hesitate to get in touch if you have any questions or would like to discuss any aspect of the quote. We're happy to arrange a call or meeting to go through everything in detail.

We look forward to hearing from you.

Best regards,
Ross
Hampstead Renovations

P.S. If you'd like to see examples of similar projects we've completed, do let me know and I'll send over some photos and case studies."""

    return body


def format_survey_confirmation(
    name: str,
    date: datetime,
    time_slot: str,
    address: str,
    surveyor_name: str = "Ross",
    duration_minutes: int = 30,
) -> str:
    """
    Format a survey confirmation message (WhatsApp/Email).
    """
    first_name = name.split()[0] if name else ""

    message = f"""Hi {first_name},

Your site survey is confirmed! 🏠

📅 {format_date_uk(date)}
⏰ {time_slot}
📍 {address}

{surveyor_name} from Hampstead Renovations will visit to discuss your project. The survey usually takes around {duration_minutes} minutes.

What to expect:
• We'll measure the space and take photos
• Discuss your ideas and requirements
• Talk through options and rough timings
• Answer any questions you have

If you need to reschedule, just reply to this message.

See you soon!
Hampstead Renovations"""

    return message


def format_survey_reminder(
    name: str,
    date: datetime,
    time_slot: str,
    address: str,
) -> str:
    """
    Format a survey reminder message (24h before).
    """
    first_name = name.split()[0] if name else ""

    message = f"""Hi {first_name},

Just a reminder that your site survey is tomorrow:

📅 {format_date_uk(date, include_day=False)}
⏰ {time_slot}
📍 {address}

Looking forward to meeting you!

Reply to this message if anything has changed.

Hampstead Renovations"""

    return message


def format_follow_up_message(
    name: str,
    stage: str,
    service_type: str,
    days_since_activity: int,
    quote_amount: Optional[float] = None,
    context: Optional[str] = None,
) -> str:
    """
    Format a follow-up message based on deal stage.
    """
    first_name = name.split()[0] if name else ""
    service_display = service_type.replace("-", " ") if service_type else "project"

    if stage == "quote-sent" and days_since_activity >= 5:
        if quote_amount:
            message = f"""Hi {first_name},

I wanted to check in about the quote we sent for your {service_display}. I know there's a lot to consider with a project like this.

If you have any questions about the quote or would like to discuss anything – whether that's the scope, timeline, or price – I'm happy to arrange a quick call.

No pressure at all, just want to make sure you have everything you need to make your decision.

Best,
Ross
Hampstead Renovations"""
        else:
            message = f"""Hi {first_name},

Just following up on your {service_display} enquiry. I wanted to check if you've had a chance to look through our proposal?

Happy to answer any questions or discuss your thoughts.

Ross
Hampstead Renovations"""

    elif stage == "contacted" and days_since_activity >= 3:
        message = f"""Hi {first_name},

Hope you're well! I wanted to follow up on our conversation about your {service_display}.

Would you like to arrange a site survey? It's free and no-obligation – just a chance for us to see the space and give you accurate pricing.

Let me know if you'd like to book a time that works for you.

Best,
Ross
Hampstead Renovations"""

    elif stage == "survey-completed":
        message = f"""Hi {first_name},

Thank you again for showing me around your property. It was great to see the space and understand what you're hoping to achieve.

I'm working on your quote now and will have it with you within the next few days.

In the meantime, if any other questions come to mind, just drop me a message.

Speak soon,
Ross
Hampstead Renovations"""

    else:
        # Generic follow-up
        message = f"""Hi {first_name},

I hope you're well. I wanted to touch base about your {service_display}.

Is there anything I can help with or any questions I can answer?

Best,
Ross
Hampstead Renovations"""

    return message


# =============================================================================
# DOCUMENT FORMATTERS
# =============================================================================


def format_quote_number(date: datetime, sequence: int) -> str:
    """
    Generate a formatted quote number.

    Format: HR-YYMMDD-XXXX
    Example: HR-241204-0001
    """
    return f"HR-{date.strftime('%y%m%d')}-{sequence:04d}"


def format_invoice_number(date: datetime, sequence: int) -> str:
    """
    Generate a formatted invoice number.

    Format: INV-YYYY-XXXX
    Example: INV-2024-0001
    """
    return f"INV-{date.strftime('%Y')}-{sequence:04d}"


def format_contract_number(date: datetime, sequence: int) -> str:
    """
    Generate a formatted contract number.

    Format: CON-YYYY-XXXX
    Example: CON-2024-0001
    """
    return f"CON-{date.strftime('%Y')}-{sequence:04d}"


def format_project_folder_name(
    client_name: str,
    postcode: str,
    service_type: str,
) -> str:
    """
    Generate a standardized project folder name.

    Format: YYYY-MM_Postcode_ClientName_ServiceType
    Example: 2024-12_NW3-1QE_Smith_Kitchen-Extension
    """
    date_prefix = datetime.now().strftime("%Y-%m")
    clean_postcode = postcode.upper().replace(" ", "-")
    clean_name = re.sub(r"[^a-zA-Z]", "", client_name.split()[-1])[:15]  # Last name, cleaned
    clean_service = service_type.replace(" ", "-")[:20]

    return f"{date_prefix}_{clean_postcode}_{clean_name}_{clean_service}"


def format_payment_terms() -> str:
    """
    Return standard payment terms text.
    """
    return """PAYMENT TERMS

1. A deposit of 10% is payable upon acceptance of this quotation to secure your booking in our schedule.

2. Stage payments will be agreed before work commences and are typically:
   • 40% at commencement of works
   • 40% at agreed midpoint
   • 10% upon completion

3. All invoices are payable within 7 days of issue.

4. We accept payment by bank transfer, debit card, or credit card. Cheques are accepted but may delay commencement.

5. Late payments may incur interest at 4% above Bank of England base rate.

6. The deposit is non-refundable if the client cancels after works have been ordered or scheduled."""


def format_warranty_statement() -> str:
    """
    Return standard warranty statement.
    """
    return """WARRANTY & GUARANTEE

All workmanship carried out by Hampstead Renovations is guaranteed for a period of 24 months from the date of practical completion.

This warranty covers:
• Defects in workmanship
• Issues arising from installation errors
• Structural work (where applicable)

This warranty does not cover:
• Normal wear and tear
• Damage caused by the client or third parties
• Issues arising from client-supplied materials
• Manufacturer defects (covered by manufacturer warranty)
• Settling or movement of the building not caused by our works

All materials carry the manufacturer's standard warranty, certificates for which will be provided upon completion.

In the event of a warranty claim, please contact us within 14 days of discovering the issue. We will arrange an inspection within 5 working days and, where the claim is valid, carry out remedial works at no additional cost."""


def format_consumer_rights_notice() -> str:
    """
    Return Consumer Rights Act 2015 notice.
    """
    return """YOUR RIGHTS UNDER THE CONSUMER RIGHTS ACT 2015

This notice does not affect your statutory rights.

When you enter into a contract with us, you have legal rights under the Consumer Rights Act 2015. These include:

1. The service must be performed with reasonable care and skill.

2. If a price isn't agreed beforehand, what you're asked to pay must be reasonable.

3. If a time for the service isn't agreed beforehand, it must be carried out within a reasonable time.

4. If anything goes wrong, you may be entitled to:
   • Ask for repeat performance of the service
   • Request a price reduction

For more information, visit: www.gov.uk/consumer-protection-rights"""


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Slack
    "format_slack_lead_notification",
    "format_slack_deal_won",
    "format_slack_pipeline_report",
    # Email
    "format_email_subject",
    "format_email_greeting",
    "format_quote_email_body",
    "format_survey_confirmation",
    "format_survey_reminder",
    "format_follow_up_message",
    # Documents
    "format_quote_number",
    "format_invoice_number",
    "format_contract_number",
    "format_project_folder_name",
    "format_payment_terms",
    "format_warranty_statement",
    "format_consumer_rights_notice",
]
