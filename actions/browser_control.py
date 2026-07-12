import os
import json
import re
import time
import asyncio
import threading
import concurrent.futures
import platform
import shutil
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


def _log(message: str) -> None:
    try:
        print(message.encode("ascii", "replace").decode("ascii"))
    except UnicodeEncodeError:
        print(message.encode("ascii", "replace").decode("ascii"))


def _get_default_browser_id() -> str:
    """Returns raw default browser identifier string for current OS."""
    system = platform.system()
    try:
        if system == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
            )
            prog_id = winreg.QueryValueEx(key, "ProgId")[0].lower()
            winreg.CloseKey(key)
            return prog_id

        elif system == "Darwin":
            result = subprocess.run(
                ["defaults", "read",
                 "com.apple.LaunchServices/com.apple.launchservices.secure",
                 "LSHandlers"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.lower()

        elif system == "Linux":
            result = subprocess.run(
                ["xdg-settings", "get", "default-web-browser"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.lower()

    except Exception:
        pass

    return ""


_BROWSER_BINARIES = {
    "Windows": {
        "opera":   ["opera.exe"],
        "brave":   ["brave.exe"],
        "vivaldi": ["vivaldi.exe"],
        "chrome":  ["chrome.exe"],
        "firefox": ["firefox.exe"],
    },
    "Darwin": {
        "opera":   ["opera"],
        "brave":   ["brave browser", "brave"],
        "vivaldi": ["vivaldi"],
        "chrome":  ["google chrome", "google-chrome"],
        "firefox": ["firefox"],
    },
    "Linux": {
        "opera":   ["opera", "opera-stable"],
        "brave":   ["brave-browser", "brave"],
        "vivaldi": ["vivaldi-stable", "vivaldi"],
        "chrome":  ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
        "firefox": ["firefox"],
    },
}


def _get_opera_executable() -> str | None:
    if platform.system() != "Windows":
        return None
    try:
        import winreg
        candidate_keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\launcher.exe",
            r"SOFTWARE\Clients\StartMenuInternet\OperaStable\shell\open\command",
            r"SOFTWARE\Clients\StartMenuInternet\OperaGXStable\shell\open\command",
        ]
        for key_path in candidate_keys:
            for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    key = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(key, None)
                    winreg.CloseKey(key)
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        _log(f"[Browser] 🔍 Opera found via registry: {exe}")
                        return exe
                except Exception:
                    continue
    except Exception:
        pass
    return None


def _find_browser_executable(prog_id: str) -> tuple:
    """
    Returns (engine_name, exe_path, channel, is_opera).
    Prioritizes Google Chrome.
    """
    system  = platform.system()
    os_bins = _BROWSER_BINARIES.get(system, {})

    # Check for Google Chrome explicitly first
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe") if system == "Windows" else None,
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
    ]
    for c in chrome_candidates:
        if c and os.path.exists(c):
            _log(f"[Browser] 🔍 Preferred Google Chrome found at: {c}")
            return "chromium", c, "chrome", False

    if any(x in prog_id for x in ["firefox", "mozilla"]):
        return "firefox", None, None, False

    if "safari" in prog_id:
        return "webkit", None, None, False

    if "opera" in prog_id:
        exe = _get_opera_executable()
        if exe:
            return "chromium", exe, None, True
        for binary in os_bins.get("opera", []):
            path = shutil.which(binary)
            if path:
                return "chromium", path, None, True

    browser_patterns = {
        "brave":   ["brave"],
        "vivaldi": ["vivaldi"],
        "chrome":  ["chrome"],
    }
    for browser_name, patterns in browser_patterns.items():
        if not any(p in prog_id for p in patterns):
            continue
        binaries = os_bins.get(browser_name, [])
        for binary in binaries:
            path = shutil.which(binary)
            if path:
                _log(f"[Browser] 🔍 Found {browser_name} at: {path}")
                return "chromium", path, None, False

    if "edge" in prog_id:
        return "chromium", None, "msedge", False

    return "chromium", None, "chrome", False


class _BrowserThread:

    def __init__(self):
        self._loop       = None
        self._thread     = None
        self._ready      = threading.Event()
        self._playwright = None
        self._browser    = None
        self._context    = None
        self._page       = None
        self._pages      = []
        self._engine_name = "chromium"
        self._exe_path   = None
        self._channel    = None
        self._is_opera   = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="BrowserThread"
        )
        self._thread.start()
        self._ready.wait(timeout=15)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._init())
        self._ready.set()
        self._loop.run_forever()

    async def _init(self):
        self._playwright = await async_playwright().start()

    def run(self, coro, timeout: int = 30):
        if not self._loop:
            raise RuntimeError("BrowserThread not started.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ── Tarayıcı ve sayfa yönetimi ───────────────────────────────────────────

    async def _launch_browser_if_needed(self):
        """
        Tarayıcıyı başlatır. Zaten açıksa hiçbir şey yapmaz.
        Her zaman default tarayıcıyı kullanır, özel sekme açmaz.
        """
        if self._browser and self._browser.is_connected():
            return

        prog_id = _get_default_browser_id()
        self._engine_name, self._exe_path, self._channel, self._is_opera = _find_browser_executable(prog_id)
        engine = getattr(self._playwright, self._engine_name)

        # Temel chromium argümanları
        chromium_args = ["--start-maximized"]

        if self._is_opera:
            # Opera GX bazı sürümlerde varsayılan olarak private modda başlar.
            # Aşağıdaki flag'ler bunu engeller.
            chromium_args += [
                "--disable-features=OperaPrivacyMode",
                "--no-private",
            ]
            _log("[Browser] 🎭 Opera detected — disabling private-mode flags")

        launch_kwargs = {"headless": False}
        if self._engine_name == "chromium":
            launch_kwargs["args"] = chromium_args
        if self._exe_path:
            launch_kwargs["executable_path"] = self._exe_path
        elif self._channel:
            launch_kwargs["channel"] = self._channel

        try:
            self._browser = await engine.launch(**launch_kwargs)
            _log(
                f"[Browser] ✅ Launched ({self._engine_name}"
                f"{' / ' + self._channel if self._channel else ''}"
                f"{' / ' + self._exe_path if self._exe_path else ''})"
            )
        except Exception as e:
            _log(f"[Browser] ⚠️ Launch failed ({e}), falling back to built-in Chromium")
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )

    async def _get_page(self):
        """
        Mevcut sayfayı döndürür.
        - Tarayıcı kapalıysa açar.
        - Context yoksa oluşturur.
        - Sayfa kapalıysa yeni sekme açar (aynı pencerede).
        - Sayfa zaten açıksa aynı sayfayı döndürür (yeni pencere açmaz).
        """
        await self._launch_browser_if_needed()

        if self._context is None:
            self._context = await self._browser.new_context(
                viewport=None,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
            if self._page not in self._pages:
                self._pages.append(self._page)

        return self._page

    async def _new_tab(self, url: str | None = None) -> str:
        await self._launch_browser_if_needed()
        if self._context is None:
            self._context = await self._browser.new_context(
                viewport=None,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
        page = await self._context.new_page()
        if page not in self._pages:
            self._pages.append(page)
        self._page = page
        if url:
            return await self._go_to(url)
        return f"Opened new tab ({len(self._pages)} total)."

    async def _switch_tab(self, index: int = 1) -> str:
        await self._launch_browser_if_needed()
        if not self._pages:
            await self._get_page()
        if not self._pages:
            return "No open tabs."
        idx = max(1, index) - 1
        if idx >= len(self._pages):
            return f"Tab {index} does not exist."
        page = self._pages[idx]
        if page.is_closed():
            return f"Tab {index} is already closed."
        self._page = page
        try:
            await page.bring_to_front()
        except Exception:
            pass
        return f"Switched to tab {index}: {page.url}"

    async def _list_tabs(self) -> str:
        await self._launch_browser_if_needed()
        if not self._pages and self._page:
            self._pages = [self._page]
        if not self._pages:
            return "No tabs open."
        rows = []
        for i, page in enumerate(self._pages, 1):
            if page.is_closed():
                continue
            title = await page.title() if page.url else ""
            rows.append(f"{i}. {title or 'Untitled'} | {page.url or 'about:blank'}")
        return "\n".join(rows) if rows else "No open tabs."

    async def _back(self) -> str:
        page = await self._get_page()
        try:
            await page.go_back(wait_until="domcontentloaded", timeout=10000)
            return f"Back: {page.url}"
        except Exception as e:
            return f"Back error: {e}"

    async def _forward(self) -> str:
        page = await self._get_page()
        try:
            await page.go_forward(wait_until="domcontentloaded", timeout=10000)
            return f"Forward: {page.url}"
        except Exception as e:
            return f"Forward error: {e}"

    async def _reload(self) -> str:
        page = await self._get_page()
        try:
            await page.reload(wait_until="domcontentloaded", timeout=15000)
            return f"Reloaded: {page.url}"
        except Exception as e:
            return f"Reload error: {e}"

    # ── Eylemler ─────────────────────────────────────────────────────────────

    async def _go_to(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        page = await self._get_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return f"Opened: {page.url}"
        except PlaywrightTimeout:
            return f"Timeout loading: {url}"
        except Exception as e:
            return f"Navigation error: {e}"

    async def _search(self, query: str, engine: str = "google") -> str:
        engines = {
            "google":     f"https://www.google.com/search?q={query.replace(' ', '+')}",
            "bing":       f"https://www.bing.com/search?q={query.replace(' ', '+')}",
            "duckduckgo": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
        }
        url = engines.get(engine.lower(), engines["google"])
        return await self._go_to(url)

    async def _click(self, selector=None, text=None) -> str:
        page = await self._get_page()
        try:
            if text:
                await page.get_by_text(text, exact=False).first.click(timeout=8000)
                return f"Clicked: '{text}'"
            elif selector:
                await page.click(selector, timeout=8000)
                return f"Clicked: {selector}"
            return "No selector or text provided."
        except PlaywrightTimeout:
            return "Element not found or not clickable."
        except Exception as e:
            return f"Click error: {e}"

    async def _type(self, selector=None, text: str = "", clear_first: bool = True) -> str:
        page = await self._get_page()
        try:
            element = page.locator(selector).first if selector else page.locator(":focus")
            if clear_first:
                await element.clear()
            await element.type(text, delay=50)
            return "Text typed."
        except Exception as e:
            return f"Type error: {e}"

    async def _scroll(self, direction: str = "down", amount: int = 500) -> str:
        page = await self._get_page()
        try:
            y = amount if direction == "down" else -amount
            await page.mouse.wheel(0, y)
            return f"Scrolled {direction}."
        except Exception as e:
            return f"Scroll error: {e}"

    async def _press(self, key: str) -> str:
        page = await self._get_page()
        try:
            await page.keyboard.press(key)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Key error: {e}"

    async def _get_text(self) -> str:
        page = await self._get_page()
        try:
            text = await page.inner_text("body")
            return text[:4000] if len(text) > 4000 else text
        except Exception as e:
            return f"Could not get page text: {e}"

    async def _fill_form(self, fields: dict) -> str:
        page    = await self._get_page()
        results = []
        for selector, value in fields.items():
            try:
                el = page.locator(selector).first
                await el.clear()
                await el.type(str(value), delay=40)
                results.append(f"✓ {selector}")
            except Exception as e:
                results.append(f"✗ {selector}: {e}")
        return "Form filled: " + ", ".join(results)

    async def _smart_click(self, description: str) -> str:
        page       = await self._get_page()
        desc_lower = description.lower()

        role_hints = {
            "button":    ["button", "buton", "btn"],
            "link":      ["link", "bağlantı"],
            "searchbox": ["search", "arama"],
            "textbox":   ["input", "field", "alan"],
        }
        for role, keywords in role_hints.items():
            if any(k in desc_lower for k in keywords):
                try:
                    await page.get_by_role(role).first.click(timeout=5000)
                    return f"Clicked ({role}): '{description}'"
                except Exception:
                    pass

        try:
            await page.get_by_text(description, exact=False).first.click(timeout=5000)
            return f"Clicked (text): '{description}'"
        except Exception:
            pass

        try:
            await page.get_by_placeholder(description, exact=False).first.click(timeout=5000)
            return f"Clicked (placeholder): '{description}'"
        except Exception:
            pass

        return f"Could not find: '{description}'"

    async def _smart_type(self, description: str, text: str) -> str:
        page = await self._get_page()

        for method, locator in [
            ("placeholder", page.get_by_placeholder(description, exact=False)),
            ("label",       page.get_by_label(description, exact=False)),
            ("role",        page.get_by_role("textbox")),
        ]:
            try:
                el = locator.first
                await el.clear()
                await el.type(text, delay=50)
                return f"Typed into ({method}): '{description}'"
            except Exception:
                continue

        return f"Could not find input: '{description}'"

    async def _close_browser(self) -> str:
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page    = None
            self._pages   = []

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        return "Browser closed."

    async def _get_interactive_tree(self) -> dict:
        page = await self._get_page()
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=4000)
        except Exception:
            pass

        js_script = """
        () => {
            // Dismiss cookie modals / popups
            const popupSelectors = [
                'button#L2AGLb',
                'button[aria-label*="cookie" i]',
                'button[aria-label*="accept" i]',
                'button[title*="accept" i]',
                '#onetrust-accept-btn-handler',
                '.cookie-banner button',
                'button.consent-accept',
                'button[aria-label*="agree" i]'
            ];
            for (const sel of popupSelectors) {
                try {
                    const btn = document.querySelector(sel);
                    if (btn && btn.offsetParent !== null) {
                        btn.click();
                    }
                } catch (e) {}
            }

            document.querySelectorAll('[data-veda-id]').forEach(el => el.removeAttribute('data-veda-id'));

            const selectors = [
                'a[href]',
                'button',
                'input',
                'textarea',
                'select',
                '[role="button"]',
                '[role="link"]',
                '[role="textbox"]',
                '[role="searchbox"]',
                '[role="checkbox"]',
                '[role="combobox"]',
                '[role="menuitem"]',
                '[role="tab"]',
                '[tabindex]:not([tabindex="-1"])'
            ];

            const found = Array.from(document.querySelectorAll(selectors.join(', ')));
            const elements = [];
            let idCounter = 1;

            for (const el of found) {
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
                const rect = el.getBoundingClientRect();
                if (rect.width <= 3 || rect.height <= 3) continue;
                if (rect.bottom < -600 || rect.top > window.innerHeight + 2000) continue;

                const tag = el.tagName.toLowerCase();
                const role = el.getAttribute('role') || tag;
                const type = el.getAttribute('type') || '';
                let label = (
                    el.getAttribute('aria-label') ||
                    el.getAttribute('placeholder') ||
                    el.getAttribute('title') ||
                    el.innerText ||
                    el.value ||
                    ''
                ).trim().replace(/\\s+/g, ' ');

                if (label.length > 80) label = label.substring(0, 80) + '...';

                el.setAttribute('data-veda-id', String(idCounter));
                elements.push({
                    id: idCounter,
                    tag: tag,
                    role: role,
                    type: type,
                    text: label,
                    value: el.value || '',
                    href: (tag === 'a' && el.href) ? el.href.substring(0, 80) : ''
                });
                idCounter++;
                if (idCounter > 150) break;
            }

            return {
                title: document.title,
                url: window.location.href,
                elements: elements
            };
        }
        """
        try:
            tree = await page.evaluate(js_script)
            return tree
        except Exception as e:
            return {
                "title": await page.title() if page.url else "",
                "url": page.url,
                "elements": [],
                "error": str(e)
            }

    async def _click_element(self, element_id: int | str = None, selector: str = None, text: str = None) -> str:
        page = await self._get_page()
        try:
            if element_id is not None:
                loc = page.locator(f'[data-veda-id="{element_id}"]').first
                if await loc.count() == 0:
                    await self._get_interactive_tree()
                    loc = page.locator(f'[data-veda-id="{element_id}"]').first
                if await loc.count() > 0:
                    await loc.click(timeout=8000)
                    return f"Clicked element [id: {element_id}]."
                return f"Element [id: {element_id}] not found on page."
            if selector:
                await page.click(selector, timeout=8000)
                return f"Clicked selector '{selector}'."
            if text:
                await page.get_by_text(text, exact=False).first.click(timeout=8000)
                return f"Clicked text '{text}'."
            return "No element_id, selector, or text provided."
        except PlaywrightTimeout:
            return f"Element [id: {element_id}] not clickable or timed out."
        except Exception as e:
            return f"Click error: {e}"

    async def _type_element(self, element_id: int | str = None, text: str = "", selector: str = None, clear_first: bool = True) -> str:
        page = await self._get_page()
        try:
            if element_id is not None:
                loc = page.locator(f'[data-veda-id="{element_id}"]').first
                if await loc.count() == 0:
                    await self._get_interactive_tree()
                    loc = page.locator(f'[data-veda-id="{element_id}"]').first
                if await loc.count() > 0:
                    if clear_first:
                        try:
                            await loc.clear()
                        except Exception:
                            pass
                    await loc.fill(text)
                    return f"Typed '{text}' into [id: {element_id}]."
                return f"Element [id: {element_id}] not found on page."
            if selector:
                loc = page.locator(selector).first
                if clear_first:
                    await loc.clear()
                await loc.fill(text)
                return f"Typed '{text}' into selector '{selector}'."
            await page.keyboard.type(text, delay=30)
            return f"Typed '{text}'."
        except Exception as e:
            return f"Type error: {e}"

    async def _extract_element(self, element_id: int | str = None, selector: str = None) -> str:
        page = await self._get_page()
        try:
            if element_id is not None:
                loc = page.locator(f'[data-veda-id="{element_id}"]').first
                if await loc.count() == 0:
                    await self._get_interactive_tree()
                    loc = page.locator(f'[data-veda-id="{element_id}"]').first
                if await loc.count() > 0:
                    txt = await loc.inner_text()
                    return txt.strip() or f"[id: {element_id} has no text]"
                return f"Element [id: {element_id}] not found on page."
            if selector:
                loc = page.locator(selector).first
                return (await loc.inner_text()).strip()
            return await self._get_text()
        except Exception as e:
            return f"Extract error: {e}"



# ── Singleton browser thread ─────────────────────────────────────────────────

_bt         = _BrowserThread()
_bt_started = False
_bt_lock    = threading.Lock()


def _ensure_started():
    global _bt_started
    with _bt_lock:
        if not _bt_started:
            _bt.start()
            _bt_started = True


_GEMINI_COOLDOWN_UNTIL = 0.0


def _call_llm_for_agent(prompt: str) -> str:
    """Invokes Gemini 2.5 Flash with smart quota protection and fallback to OpenRouter/SeekAI."""
    global _GEMINI_COOLDOWN_UNTIL
    now = time.time()

    if now > _GEMINI_COOLDOWN_UNTIL:
        try:
            config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                gemini_key = cfg.get("gemini_api_key", "").strip()
                if gemini_key:
                    from google import genai
                    client = genai.Client(api_key=gemini_key, http_options={"api_version": "v1beta"})
                    resp = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                    )
                    if resp and resp.text:
                        return resp.text.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                _GEMINI_COOLDOWN_UNTIL = now + 45.0
                _log("[BrowserAgent] ⏳ Gemini free quota limit reached (429) — routing to OpenRouter/SeekAI for 45s")
            else:
                _log(f"[BrowserAgent] Gemini call fallback: {e}")

    try:
        from llm_client import client as ai_client
        res = ai_client.chat(prompt, max_tokens=1024)
        if res:
            return res.strip()
    except Exception as e:
        _log(f"[BrowserAgent] LLM client fallback failed: {e}")

    return ""


def _parse_agent_json(raw: str) -> dict:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"(\{.*\})", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {"thought": "Parsing fallback", "action": "finish", "parameters": {"result": raw}}


def run_autonomous_browser_agent(
    goal: str,
    max_turns: int = 15,
    speak=None,
    player=None,
) -> str:
    """
    Autonomous Browser Automation Agent (Astra-6 style).
    Executes multi-step tasks across the web using observation of the DOM accessibility tree
    and the strict action space: click, type, navigate, scroll, extract, finish.
    """
    _ensure_started()
    _log(f"[BrowserAgent] 🚀 Starting autonomous task: {goal}")
    if player and hasattr(player, "write_log"):
        player.write_log(f"[browser-agent] 🚀 Starting: {goal[:50]}")
    if speak:
        speak(f"Starting browser automation for {goal[:40]}")

    current_tree = _bt.run(_bt._get_interactive_tree())
    curr_url = current_tree.get("url", "")
    if not curr_url or curr_url in ("about:blank", "chrome://newtab/"):
        url_match = re.search(r"https?://[^\s]+|(?:www\.)[^\s]+|[a-zA-Z0-9-]+\.(?:com|org|in|net|edu|io|co)", goal)
        if url_match:
            initial_url = url_match.group(0)
            if not initial_url.startswith("http"):
                initial_url = "https://" + initial_url
            _bt.run(_bt._go_to(initial_url))
        else:
            _bt.run(_bt._search(goal))
        time.sleep(1.5)

    last_result = "Browser initialized."
    action_history: list[str] = []
    consecutive_errors = 0

    for turn in range(1, max_turns + 1):
        tree = _bt.run(_bt._get_interactive_tree())
        page_url = tree.get("url", "unknown")
        page_title = tree.get("title", "")
        elements = tree.get("elements", [])
        body_text = _bt.run(_bt._get_text())
        if len(body_text) > 1200:
            body_text = body_text[:1200] + "..."

        tree_lines = []
        for el in elements:
            parts = [f"[id: {el['id']}]", el['tag']]
            if el.get("role") and el["role"] != el["tag"]:
                parts.append(f"({el['role']})")
            if el.get("type"):
                parts.append(f"[type={el['type']}]")
            if el.get("text"):
                parts.append(f'"{el["text"]}"')
            if el.get("value") and el["value"] != el.get("text"):
                parts.append(f'[value="{el["value"]}"]')
            if el.get("href"):
                parts.append(f'href="{el["href"]}"')
            tree_lines.append(" ".join(parts))

        tree_str = "\n".join(tree_lines) if tree_lines else "(No interactive elements found)"
        history_str = "\n".join(action_history[-4:]) if action_history else "(None yet - this is your first step)"

        prompt = f"""# ROLE
You are an autonomous Browser Automation Agent. Your goal is to navigate the web, interact with UI elements, and complete complex multi-step tasks based on user instructions.

# ACTION SPACE
You have access to the following tools. You must select one tool per turn.
- click(element_id): Click a specific element on the current page.
- type(element_id, text): Input text into a specific form field.
- navigate(url): Navigate to a new URL.
- scroll(direction): Scroll the page "up" or "down".
- extract(element_id): Extract the text content of a specific element.
- finish(result): Terminate the task and return the final answer to the user.

# OBSERVATION STATE
1. Current URL: {page_url}
2. Page Title: {page_title}
3. Visible Page Content / Text Snippet:
\"\"\"{body_text}\"\"\"
4. Previous Action Result: {last_result}
5. Actions Taken So Far in This Session:
{history_str}
6. Accessibility Tree (DOM elements currently on page):
{tree_str}

# USER INSTRUCTION / GOAL
{goal}

# RULES & CONSTRAINTS
1. NEVER hallucinate element IDs. Only interact with IDs currently visible in your Observation State.
2. THINK BEFORE YOU ACT. Always write out your logical reasoning in the `thought` field before taking an action.
3. If the user's question or requested information is ALREADY visible in the 'Visible Page Content / Text Snippet' or page title, IMMEDIATELY call `finish(result)` with the answer! Do not take unnecessary extra steps.
4. Do NOT re-navigate to the starting URL if you are already on the page or have navigated past it.
5. HANDLE INTERRUPTIONS. If a cookie consent banner, newsletter popup, or modal appears, your immediate priority is to dismiss it before proceeding with the core task.
6. When you have found the requested information or completed the task, call `finish` with the complete result.

# OUTPUT FORMAT
You must return your response in strictly valid JSON format:
{{
  "thought": "Your reasoning here",
  "action": "click" | "type" | "navigate" | "scroll" | "extract" | "finish",
  "parameters": {{
    "element_id": "1",
    "text": "sample text",
    "url": "https://...",
    "direction": "down",
    "result": "final answer"
  }}
}}
"""
        raw_resp = _call_llm_for_agent(prompt)
        parsed = _parse_agent_json(raw_resp)
        thought = parsed.get("thought", "")
        action = parsed.get("action", "").lower().strip()
        params = parsed.get("parameters", {})

        _log(f"[BrowserAgent Turn {turn}] 💭 Thought: {thought}")
        _log(f"[BrowserAgent Turn {turn}] ⚡ Action: {action} {params}")
        if player and hasattr(player, "write_log"):
            player.write_log(f"[browser-agent T{turn}] {action}: {str(params)[:50]}")

        if action == "finish":
            final_res = params.get("result") or thought or "Task completed."
            _log(f"[BrowserAgent] ✅ Finished: {final_res}")
            if speak:
                speak(final_res[:100])
            return final_res

        try:
            if action == "click":
                eid = params.get("element_id")
                last_result = _bt.run(_bt._click_element(element_id=eid, selector=params.get("selector"), text=params.get("text")))
            elif action == "type":
                eid = params.get("element_id")
                txt = params.get("text", "")
                last_result = _bt.run(_bt._type_element(element_id=eid, text=txt, selector=params.get("selector")))
            elif action == "navigate":
                url = params.get("url", "")
                last_result = _bt.run(_bt._go_to(url))
            elif action == "scroll":
                direction = params.get("direction", "down")
                last_result = _bt.run(_bt._scroll(direction=direction, amount=600))
            elif action == "extract":
                eid = params.get("element_id")
                last_result = _bt.run(_bt._extract_element(element_id=eid, selector=params.get("selector")))
            else:
                last_result = f"Unsupported action '{action}'."
            consecutive_errors = 0
        except Exception as err:
            last_result = f"Error during {action}: {err}"
            consecutive_errors += 1
            if consecutive_errors >= 3:
                return f"Browser agent halted after repeated errors: {last_result}"

        action_history.append(f"Turn {turn}: action={action} params={params} -> {last_result}")
        time.sleep(1.0)


    return f"Browser agent reached maximum turns ({max_turns}). Last status: {last_result}"


# ── Public API ───────────────────────────────────────────────────────────────

def browser_control(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Browser controller — auto-detects and uses system default browser.
    Always reuses the existing browser window/page; never opens incognito.
    Supports autonomous multi-turn tasks (Astra-6 style), single actions, and DOM inspection.
    """
    _ensure_started()

    params = parameters or {}
    action = params.get("action", "").lower().strip()
    goal = params.get("goal") or params.get("task") or params.get("instruction")

    # If an autonomous task or goal is specified, run the autonomous agent loop
    if action in {"autonomous_task", "agent", "astra", "multi_step"} or (goal and action in {"", "run", "do"}):
        return run_autonomous_browser_agent(goal=goal, speak=speak, player=player)

    result = "Unknown action."

    try:
        if action in {"go_to", "navigate"}:
            result = _bt.run(_bt._go_to(params.get("url", "")))

        elif action == "search":
            result = _bt.run(_bt._search(
                params.get("query", ""),
                params.get("engine", "google"),
            ))

        elif action == "click":
            if "element_id" in params:
                result = _bt.run(_bt._click_element(
                    element_id=params.get("element_id"),
                    selector=params.get("selector"),
                    text=params.get("text"),
                ))
            else:
                result = _bt.run(_bt._click(
                    selector=params.get("selector"),
                    text=params.get("text"),
                ))

        elif action == "type":
            if "element_id" in params:
                result = _bt.run(_bt._type_element(
                    element_id=params.get("element_id"),
                    text=params.get("text", ""),
                    selector=params.get("selector"),
                    clear_first=params.get("clear_first", True),
                ))
            else:
                result = _bt.run(_bt._type(
                    selector=params.get("selector"),
                    text=params.get("text", ""),
                    clear_first=params.get("clear_first", True),
                ))

        elif action == "scroll":
            result = _bt.run(_bt._scroll(
                direction=params.get("direction", "down"),
                amount=params.get("amount", 500),
            ))

        elif action == "extract":
            result = _bt.run(_bt._extract_element(
                element_id=params.get("element_id"),
                selector=params.get("selector"),
            ))

        elif action in {"get_tree", "observation", "elements"}:
            tree = _bt.run(_bt._get_interactive_tree())
            elems = tree.get("elements", [])
            lines = [f"[id: {e['id']}] {e['tag']} ({e.get('role','')}) \"{e.get('text','')}\"" for e in elems[:40]]
            result = f"URL: {tree.get('url')}\nElements ({len(elems)} found):\n" + "\n".join(lines)

        elif action == "fill_form":
            result = _bt.run(_bt._fill_form(params.get("fields", {})))

        elif action == "smart_click":
            result = _bt.run(_bt._smart_click(params.get("description", "")))

        elif action == "smart_type":
            result = _bt.run(_bt._smart_type(
                params.get("description", ""),
                params.get("text", ""),
            ))

        elif action == "get_text":
            result = _bt.run(_bt._get_text())

        elif action == "press":
            result = _bt.run(_bt._press(params.get("key", "Enter")))

        elif action in {"open_tab", "new_tab"}:
            result = _bt.run(_bt._new_tab(params.get("url")))

        elif action == "switch_tab":
            result = _bt.run(_bt._switch_tab(int(params.get("tab", 1))))

        elif action == "list_tabs":
            result = _bt.run(_bt._list_tabs())

        elif action == "back":
            result = _bt.run(_bt._back())

        elif action == "forward":
            result = _bt.run(_bt._forward())

        elif action in {"refresh", "reload"}:
            result = _bt.run(_bt._reload())

        elif action == "close":
            result = _bt.run(_bt._close_browser())

        else:
            result = f"Unknown action: {action}"

    except concurrent.futures.TimeoutError:
        result = "Browser action timed out."
    except Exception as e:
        result = f"Browser error: {e}"

    _log(f"[Browser] {result[:80]}")
    if player and hasattr(player, "write_log"):
        player.write_log(f"[browser] {result[:60]}")

    return result

