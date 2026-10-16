"""Independent browser postconditions; never accept the action's return as evidence."""

from playwright.async_api import Error as PlaywrightError

from victus.adapters.playwright.locators import (
    TargetResolutionError,
    TargetResolver,
    _ResolvedTarget,
)


async def verify_field_value(
    resolver: TargetResolver, target: _ResolvedTarget, expected_text: str
) -> bool:
    """Read the actual field; do not return/log its potentially private contents.

    A fill produces input events, so the old observation revision is deliberately
    not used as postcondition evidence. Identity, origin and uniqueness still are.
    """
    try:
        page = resolver._session._resolve_page(target.observation.page_ref)
        await resolver._assert_identity(page, target.element, target.binding, target.observation)
        actual = await target.element.input_value(timeout=5000)
        await resolver._assert_identity(page, target.element, target.binding, target.observation)
        return actual == expected_text
    except (PlaywrightError, TargetResolutionError, ValueError):
        return False
