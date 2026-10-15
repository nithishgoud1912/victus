import asyncio

from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content('<button type="button">VICTUS probe</button>')
        assert await page.get_by_role("button", name="VICTUS probe").count() == 1
        print("Browser launched and one accessible button was found")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())