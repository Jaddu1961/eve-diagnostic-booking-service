"""Payment/booking state machine shared by POST /payments/ and the webhook."""
import logging

from .models import Booking, BookingStatus, Payment, PaymentStatus

log = logging.getLogger(__name__)


def apply_payment_result(booking: Booking, payment: Payment, new_status: PaymentStatus) -> bool:
    """Move a payment (and its booking) to a new status.

    Returns True if anything changed. The function is idempotent and refuses
    illegal transitions, which also makes it safe against out-of-order or
    replayed provider events:
      * a terminal payment (SUCCESS/FAILED) never changes again
      * a CONFIRMED booking is never downgraded by a later failure
      * a CANCELLED booking is never resurrected by a late success
    """
    if payment.status != PaymentStatus.PENDING:
        if payment.status != new_status:
            log.warning("Ignoring %s for payment %s already %s", new_status, payment.id, payment.status)
        return False

    payment.status = new_status

    if new_status == PaymentStatus.SUCCESS:
        if booking.status in (BookingStatus.PENDING, BookingStatus.FAILED):
            booking.status = BookingStatus.CONFIRMED
        elif booking.status == BookingStatus.CANCELLED:
            # Money was captured for a cancelled booking: needs a refund (out of scope here).
            log.warning("Payment %s succeeded for cancelled booking %s", payment.id, booking.id)
    elif new_status == PaymentStatus.FAILED:
        if booking.status == BookingStatus.PENDING:
            booking.status = BookingStatus.FAILED
    return True
