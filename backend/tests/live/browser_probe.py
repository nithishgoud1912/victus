import argparse
import asyncio

from victus.adapters.playwright.session import BrowserSession


async def main(*, headless: bool = False) -> None:
    async with BrowserSession(headless=headless) as session:
        reference = await session.new_page()
        # This probe runs inside the adapter's owning loop, not across the tool boundary.
        page = session._resolve_page(reference)
        await page.set_content('<button type="button">VICTUS probe</button>')
        assert await page.get_by_role("button", name="VICTUS probe").count() == 1
        print("Browser launched and one accessible button was found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    asyncio.run(main(headless=parser.parse_args().headless))
