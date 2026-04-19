export function bookingActionEndpoints(bookingId) {
  return {
    acknowledge: `/api/trips/bookings/${bookingId}/ack/`,
    cancel: `/api/trips/bookings/${bookingId}/cancel/`,
    noShow: `/api/trips/bookings/${bookingId}/no-show/`,
    refundRequest: `/api/trips/bookings/${bookingId}/refund-request/`,
    refundDecision: `/api/trips/bookings/${bookingId}/refund-decision/`,
    timeline: `/api/trips/bookings/${bookingId}/timeline/`,
  };
}
