"""Celery Task for Sending Emails"""

import logging
from smtplib import SMTPException

# from celery import shared_task
# from celery.exceptions import MaxRetriesExceededError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_email(subject, plain_text_content, html_content, recipient_list):
    """
    Helper function to send an email with both plain text and HTML content.
    """
    try:
        # Create the email
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_text_content,  # Plain text content
            to=recipient_list,
        )
        email.attach_alternative(html_content, "text/html")  # Attach HTML content

        # Send the email
        email.send()
        logger.info("Email sent successfully to %s", recipient_list)
    except Exception as e:
        logger.error("Failed to send email to %s: %s", recipient_list, str(e))
        raise e  # Raise the exception to allow retries


# @shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def send_registration_email(username, user_email):
    """
    Send a welcome email to the user after registration.
    Retries the task if it fails.
    """
    try:
        subject = "Welcome to Our Platform!"
        to_email = [user_email]

        # Render the HTML email template
        html_content = render_to_string(
            "emails/registration.html", {"username": username}
        )

        # Create a plain text version of the email
        plain_text_content = (
            f"Hi {username},\n\n"
            "Thank you for registering with us. We're excited to have you on board!"
        )

        # Send the email
        send_email(subject, plain_text_content, html_content, to_email)
    except SMTPException as exc:  # Catch specific email-related exceptions
        logger.error(
            "Failed to send registration email to %s: %s", user_email, exc
        )  # Use lazy % formatting
        return False


logger = logging.getLogger(__name__)


# @shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def send_order_email(order_data, user_email):
    """
    Send an email with order details to the user.
    Retries the task if it fails.
    """
    try:
        # Extract order details
        orders = order_data.get("orders", [])
        user = (
            orders[0].get("user") if orders else "Valued Customer"
        )  # Default if no orders
        subject = "Your Order(s) Confirmation"
        to_email = [user_email]

        # Render the HTML email template
        html_content = render_to_string(
            "emails/order_confirmation.html", {"orders": orders, "user": user}
        )

        # Create a plain text version of the email
        plain_text_content = (
            "Thank you for your order(s). Please check your email for details."
        )

        # Send the email
        send_email(subject, plain_text_content, html_content, to_email)
    except SMTPException as exc:
        logger.error(
            "Failed to send order confirmation email to %s: %s", user_email, exc
        )
        return False
