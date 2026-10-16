"""Guarded concrete operations, not public tools or authorization decisions."""

from playwright.async_api import Error as PlaywrightError

from victus.adapters.playwright.locators import TargetResolutionError, TargetResolver
from victus.tools.verifiers.browser import verify_field_value


class BrowserActionError(RuntimeError):
    """A write was attempted but its effect is uncertain; never blindly retry."""


async def fill_target(resolver: TargetResolver, ref: str, observation_id: str, text: str) -> bool:
    """Fill a checked, pinned field and independently read its resulting value.

    Dispatcher integration must still supply scope, authorization, cancellation,
    audit and action status. False means the value could not be verified.
    """
    if not isinstance(text, str) or len(text) > 100_000:
        raise ValueError("Invalid field text")
    resolver._session._check_owner()
    async with resolver._operation_lock:
        return await _fill_target(resolver, ref, observation_id, text)


async def _fill_target(resolver: TargetResolver, ref: str, observation_id: str, text: str) -> bool:
    resolved = await resolver.resolve_target(ref, observation_id)
    try:
        if "fill" not in resolved.binding.public.operations:
            raise TargetResolutionError("OPERATION_NOT_SUPPORTED")
        # Pin the checked DOM node rather than letting a locator silently retarget
        # a newly rendered element between validation and Playwright's auto-wait.
        try:
            await resolved.element.fill(text, timeout=5000)
        except PlaywrightError:
            # Playwright call logs can include the text passed to fill().
            raise BrowserActionError("BROWSER_FILL_UNCERTAIN") from None
        return await verify_field_value(resolver, resolved, text)
    finally:
        resolver.invalidate(observation_id)
        await resolved.element.dispose()
