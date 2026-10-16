"""Explicit request preview/review bridge to the shared, bounded model gateway."""

import hashlib
import threading
import time

from victus.adapters.credentials import WindowsCredentials
from victus.models.cloud import CloudProvider
from victus.models.contracts import ErrorCode, ModelError, ModelPin
from victus.models.gateway import ModelGateway, RequestBudget
from victus.models.transfer_policy import ConsentRequired, TransferPolicy


class CloudService:
    def __init__(self, model, upstream, stopped, *, credentials=None, transport=None):
        self.pin = ModelPin(name=model, digest="sha256:" + hashlib.sha256(
            ("remote-config:" + model + ":" + upstream).encode()).hexdigest())
        self.upstream, self.stopped = upstream, stopped
        self.credentials, self.transport = credentials or WindowsCredentials(), transport
        self.policy = TransferPolicy()
        self.pending = {}
        self.lock = threading.Lock()
        self.state = "consent_required"

    def _provider(self):
        return CloudProvider(self.pin, self.upstream, self.policy, self.credentials,
                             transport=self.transport)

    def preview(self, request):
        if self.stopped.is_set():
            raise ModelError(ErrorCode.CANCELLED)
        if request.pin != self.pin:
            raise ModelError(ErrorCode.PIN)
        with self.lock:
            self.pending = {key: entry for key, entry in self.pending.items()
                            if entry[1] > time.monotonic()}
            preview = self._provider().preview(request)
            self.pending[preview.id] = (request, time.monotonic() + preview.expires_in_seconds)
            return preview

    async def review(self, key, *, approve, confirmation):
        with self.lock:
            entry = self.pending.pop(key, None)
            if entry is None or entry[1] <= time.monotonic():
                raise ConsentRequired()
            self.policy.decide(key, approve=approve, confirmation=confirmation)
        if not approve:
            self.state = "consent_denied"
            return None
        provider = self._provider()
        provider.consent_id = key
        request = entry[0]
        # One exact reviewed operation; any retry or repair requires a new preview.
        budget = RequestBudget(max_requests=1, max_output_tokens=request.max_output_tokens,
                               timeout_seconds=12, repairs_remaining=0)
        try:
            return await ModelGateway(provider, budget, cancelled=self.stopped,
                                      timeout_seconds=8).request(request)
        finally:
            self.state = provider.dependency_state
            if self.stopped.is_set():
                self.policy.clear()

    def clear(self):
        with self.lock:
            self.pending.clear()
            self.policy.clear()
