"""Celery Task for Sending Emails
"""

import logging

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task
def send_order_email(order_data, user_email):
    """
    Send an email with order details to the user.
    """
    # Extract order details
    orders = order_data.get("orders", [])
    user = (
        orders[0].get("user") if orders else "Valued Customer"
    )  # Default if no orders
    subject = "Your Order(s) Confirmation"
    to_email = user_email

    # Render the HTML email template
    html_content = render_to_string(
        "emails/order_confirmation.html", {"orders": orders, "user": user}
    )

    # Log the rendered HTML content for debugging
    # logger.info("Rendered HTML content: %s", html_content)

    # Create a plain text version of the email
    plain_text_content = (
        "Thank you for your order(s). Please check your email for details."
    )

    # Create the email
    email = EmailMultiAlternatives(
        subject=subject, body=plain_text_content, to=[to_email]  # Plain text content
    )
    email.attach_alternative(html_content, "text/html")  # Attach HTML content

    # Send the email
    email.send()
