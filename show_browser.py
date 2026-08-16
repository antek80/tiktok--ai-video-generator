import asyncio
from agent.browser import BrowserManager

async def main():
    bm = BrowserManager(headless=False)
    context, page = await bm.get_stealth_context()
    print("Otwieram panel TikTok Creator Center w oknie Playwright Stealth...")
    await page.goto("https://www.tiktok.com/creator-center/content", wait_until="domcontentloaded")
    print("Okno pozostanie otwarte dopóki go nie zamkniesz.")
    
    # Wait until page is closed by user
    try:
        await page.wait_for_timeout(3600000)  # 1 hour
    except Exception:
        pass
    finally:
        await bm.close()

if __name__ == "__main__":
    asyncio.run(main())
