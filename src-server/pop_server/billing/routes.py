"""Stripe billing routes — checkout + webhook."""

from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from pop_server.auth.middleware import require_auth
from pop_server.config import settings
from pop_server.db import (
    get_user_by_id,
    update_subscription,
    update_subscription_by_customer,
)
from pop_server.models import CheckoutResponse

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(user: dict = Depends(require_auth)):
    """Create a Stripe Checkout Session for the $4.99/mo subscription.

    Returns the checkout URL for the desktop app to open in a browser.
    """
    stripe.api_key = settings.stripe_secret_key

    # Reuse existing Stripe customer if we have one
    customer_id = user.get("stripe_customer_id") or None

    if not customer_id:
        customer = stripe.Customer.create(
            metadata={
                "discord_id": user["discord_id"],
                "pop_user_id": str(user["id"]),
            },
        )
        customer_id = customer.id
        # Save the customer ID to the user record
        update_subscription(
            discord_id=user["discord_id"],
            stripe_customer_id=customer_id,
            subscription_id=user.get("subscription_id", ""),
            subscription_status=user["subscription_status"],
        )

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        mode="subscription",
        success_url="https://pathofpurpose.app/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://pathofpurpose.app/cancel",
        metadata={
            "discord_id": user["discord_id"],
            "pop_user_id": str(user["id"]),
        },
    )

    return CheckoutResponse(checkout_url=session.url)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for subscription lifecycle.

    Events handled:
    - checkout.session.completed: new subscription activated
    - customer.subscription.updated: status change (active, past_due, etc.)
    - customer.subscription.deleted: subscription cancelled
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer", "")
        subscription_id = data.get("subscription", "")
        discord_id = data.get("metadata", {}).get("discord_id", "")

        if discord_id:
            update_subscription(
                discord_id=discord_id,
                stripe_customer_id=customer_id,
                subscription_id=subscription_id,
                subscription_status="active",
            )

    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer", "")
        subscription_id = data.get("id", "")
        status = data.get("status", "active")

        update_subscription_by_customer(
            stripe_customer_id=customer_id,
            subscription_id=subscription_id,
            subscription_status=status,
        )

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer", "")
        subscription_id = data.get("id", "")

        update_subscription_by_customer(
            stripe_customer_id=customer_id,
            subscription_id=subscription_id,
            subscription_status="cancelled",
        )

    return {"status": "ok"}
