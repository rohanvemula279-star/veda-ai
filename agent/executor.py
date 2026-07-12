import json
import re
import sys
import threading
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Callable, Any, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from agent.planner       import create_plan, replan
from agent.error_handler import analyze_error, generate_fix, ErrorDecision


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _get_api_key() -> str:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "").strip()
    except Exception:
        return ""

def _run_generated_code(description: str, speak: Callable | None = None) -> str:
    import google.generativeai as genai

    if speak:
        speak("Writing custom code for this task, sir.")

    home      = Path.home()
    desktop   = home / "Desktop"
    downloads = home / "Downloads"
    documents = home / "Documents"

    if not desktop.exists():
        try:
            import winreg
            key     = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            desktop = Path(winreg.QueryValueEx(key, "Desktop")[0])
        except Exception:
            pass

    genai.configure(api_key=_get_api_key())
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=(
            "You are an expert Python developer. "
            "Write clean, complete, working Python code. "
            "Use standard library + common packages. "
            "Install missing packages with subprocess + pip if needed. "
            "Return ONLY the Python code. No explanation, no markdown, no backticks.\n\n"
            f"SYSTEM PATHS:\n"
            f"  Desktop   = r'{desktop}'\n"
            f"  Downloads = r'{downloads}'\n"
            f"  Documents = r'{documents}'\n"
            f"  Home      = r'{home}'\n"
        )
    )

    try:
        response = model.generate_content(
            f"Write Python code to accomplish this task:\n\n{description}"
        )
        code = response.text.strip()
        code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        print(f"[Executor] 🐍 Running generated code: {tmp_path}")

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True,
            timeout=120, cwd=str(Path.home())
        )

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        output = result.stdout.strip()
        error  = result.stderr.strip()

        if result.returncode == 0 and output:
            return output
        elif result.returncode == 0:
            return "Task completed successfully."
        elif error:
            raise RuntimeError(f"Code error: {error[:400]}")
        return "Completed."

    except subprocess.TimeoutExpired:
        raise RuntimeError("Generated code timed out after 120 seconds.")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Generated code failed: {e}")

def _inject_context(params: dict, tool: str, step_results: dict, goal: str = "") -> dict:
    if not step_results:
        return params

    params = dict(params)

    if tool == "file_controller" and params.get("action") in ("write", "create_file"):
        content = params.get("content", "")
        if not content or len(content) < 50:
            all_results = [
                v for v in step_results.values()
                if v and len(v) > 100 and v not in ("Done.", "Completed.")
            ]
            if all_results:
                combined = "\n\n---\n\n".join(all_results)
                translated = _translate_to_goal_language(combined, goal)
                params["content"] = translated
                print(f"[Executor] 💉 Injected + translated content")

    return params
def _detect_language(text: str) -> str:
    key = _get_api_key()
    if not key.startswith("AIza"):
        try:
            from or_client import client as ai_client
            res = ai_client.chat(
                f"What language is this text written in? Reply with ONLY the language name in English (e.g. English, Spanish, Hindi).\n\nText: {text[:200]}"
            )
            return (res or "English").strip()
        except Exception:
            return "English"

    import google.generativeai as genai
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    try:
        response = model.generate_content(
            f"What language is this text written in? "
            f"Reply with ONLY the language name in English (e.g. Turkish, English, French).\n\n"
            f"Text: {text[:200]}"
        )
        return response.text.strip()
    except Exception:
        return "English"


def _translate_to_goal_language(content: str, goal: str) -> str:
    if not goal:
        return content
    try:
        key = _get_api_key()
        target_lang = _detect_language(goal)
        print(f"[Executor] 🌐 Translating to: {target_lang}")

        prompt = (
            f"You are a professional translator. "
            f"Translate the following text into {target_lang}.\n"
            f"IMPORTANT:\n"
            f"- Translate EVERYTHING, leave nothing in English\n"
            f"- Keep all facts, numbers, and data intact\n"
            f"- Keep the structure and formatting\n"
            f"- Output ONLY the translated text, nothing else\n\n"
            f"Text to translate:\n{content[:4000]}"
        )

        if not key.startswith("AIza"):
            from or_client import client as ai_client
            res = ai_client.chat(prompt)
            translated = (res or content).strip()
            print(f"[Executor] ✅ Translation done (SeekAI) ({target_lang})")
            return translated

        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        translated = response.text.strip()
        print(f"[Executor] ✅ Translation done ({target_lang})")
        return translated
    except Exception as e:
        print(f"[Executor] ⚠️ Translation failed: {e}")
        return content

def _call_tool(tool: str, parameters: dict, speak: Callable | None, player: Any = None) -> str:

    if tool == "open_app":
        from actions.open_app import open_app
        return open_app(parameters=parameters, player=player) or "Done."

    elif tool == "web_search":
        from actions.web_search import web_search
        return web_search(parameters=parameters, player=player) or "Done."
    elif tool == "game_updater":
        from actions.game_updater import game_updater
        return game_updater(parameters=parameters, player=player, speak=speak) or "Done."
    elif tool == "browser_control":
        from actions.browser_control import browser_control
        return browser_control(parameters=parameters, player=player, speak=speak) or "Done."

    elif tool == "file_controller":
        from actions.file_controller import file_controller
        return file_controller(parameters=parameters, player=player) or "Done."

    elif tool == "cmd_control":
        from actions.cmd_control import cmd_control
        return cmd_control(parameters=parameters, player=player) or "Done."

    elif tool == "claude_code":
        from actions.claude_code_bridge import run_developer_mode_request
        claude_parameters = dict(parameters or {})
        claude_parameters.setdefault("workspace_path", str(Path.cwd()))
        return run_developer_mode_request(claude_parameters, speak=speak)

    elif tool == "screen_process":
        from actions.screen_processor import screen_process
        screen_process(parameters=parameters, player=player)
        return "Screen captured and analyzed."

    elif tool == "send_message":
        from actions.send_message import send_message
        return send_message(parameters=parameters, player=player) or "Done."

    elif tool == "reminder":
        from actions.reminder import reminder
        return reminder(parameters=parameters, player=player) or "Done."

    elif tool == "youtube_video":
        from actions.youtube_video import youtube_video
        return youtube_video(parameters=parameters, player=player) or "Done."

    elif tool == "weather_report":
        from actions.weather_report import weather_action
        return weather_action(parameters=parameters, player=player) or "Done."

    elif tool == "computer_settings":
        from actions.computer_settings import computer_settings
        return computer_settings(parameters=parameters, player=player) or "Done."

    elif tool == "desktop_control":
        from actions.desktop import desktop_control
        return desktop_control(parameters=parameters, player=player) or "Done."

    elif tool == "computer_control":
        from actions.computer_control import computer_control
        return computer_control(parameters=parameters, player=player) or "Done."

    elif tool == "generated_code":
        description = parameters.get("description", "")
        if not description:
            raise ValueError("generated_code requires a 'description' parameter.")
        from actions.claude_code_bridge import run_developer_mode_request
        return run_developer_mode_request(
            {"description": description, "workspace_path": str(Path.cwd())},
            speak=speak,
        )

    elif tool == "flight_finder":
        from actions.flight_finder import flight_finder
        return flight_finder(parameters=parameters, player=player, speak=speak) or "Done."

    elif tool in ("spotify_controller", "spotify", "music"):
        from actions.spotify_controller import spotify_controller
        return spotify_controller(parameters=parameters, player=player, speak=speak) or "Done."

    elif tool in ("calendar_scheduler", "calendar", "schedule"):
        from actions.calendar_scheduler import calendar_scheduler
        return calendar_scheduler(parameters=parameters, player=player, speak=speak) or "Done."

    elif tool in ("daily_briefing", "briefing"):
        from actions.daily_briefing import daily_briefing
        return daily_briefing(parameters=parameters, player=player, speak=speak) or "Done."

    elif tool in ("code_helper", "code_agent"):
        from actions.code_helper import code_helper
        return code_helper(parameters=parameters, player=player, speak=speak) or "Done."

    elif tool == "calorie_counter":
        from actions.calorie_counter import run as run_calorie_counter
        return run_calorie_counter(parameters=parameters, player=player) or "Done."

    elif tool == "pushup_counter":
        from actions.pushup_counter import run as run_pushup_counter
        return run_pushup_counter(parameters=parameters, player=player) or "Done."

    elif tool == "system_monitor":
        from actions.system_monitor import run as run_system_monitor
        return run_system_monitor(parameters=parameters, player=player) or "Done."

    elif tool == "upload_video":
        from actions.upload_video import run as run_upload_video
        return run_upload_video(parameters=parameters, player=player) or "Done."

    elif tool in ("office_builder", "presentation", "spreadsheet"):
        from actions.office_builder import create_presentation, create_spreadsheet
        action = (parameters or {}).get("action", "").lower()
        if "spreadsheet" in action or "excel" in action or "tracker" in action:
            return create_spreadsheet(parameters=parameters, player=player) or "Spreadsheet created."
        return create_presentation(parameters=parameters, player=player) or "Presentation created."

    elif tool in ("docx_tools", "word_document", "document"):
        from actions.docx_tools import word_document
        return word_document(parameters=parameters, player=player, speak=speak) or "Document created."

    elif tool in ("pdf_tools", "create_pdf", "pdf"):
        from actions.pdf_tools import create_pdf
        return create_pdf(parameters=parameters, player=player) or "PDF generated."

    elif tool in ("website_builder", "build_website"):
        from actions.website_builder import website_builder
        ws = (parameters or {}).get("output_dir")
        if not ws:
            default_ws = Path.home() / "Desktop" / "VedaWebsites"
            default_ws.mkdir(parents=True, exist_ok=True)
            parameters["output_dir"] = str(default_ws)
        return website_builder(parameters=parameters, player=player) or "Website built."

    elif tool in ("auto_tidy", "auto_tidy_daemon", "tidy_downloads"):
        from actions.auto_tidy_daemon import auto_tidy
        return auto_tidy(parameters=parameters, player=player, speak=speak) or "Auto-tidy completed."

    elif tool in ("form_filler", "fill_form"):
        from actions.form_filler import form_filler
        return form_filler(parameters=parameters, player=player) or "Form filler completed."

    elif tool in ("window_orchestrator", "window_manager", "snap_window", "split_screen"):
        from actions.window_orchestrator import window_orchestrator
        return window_orchestrator(parameters=parameters, player=player) or "Window action completed."

    elif tool in ("routines", "routine", "system_macro"):
        from actions.routines import routines_action
        return routines_action(parameters=parameters, player=player, speak=speak) or "Routine completed."

    else:
        print(f"[Executor] ⚠️ Unknown tool '{tool}' — checking plugins fallback")
        return f"Completed {tool}."

class AgentExecutor:

    MAX_REPLAN_ATTEMPTS = 2

    def __init__(self, player: Any = None, speak: Callable | None = None):
        self.player = player
        self.speak  = speak

    def execute_plan(
        self,
        plan: dict,
        speak: Callable | None = None,
        cancel_flag: threading.Event | None = None,
    ) -> str:
        effective_speak = speak or self.speak
        goal = plan.get("goal", "")
        print(f"\n[Executor] 🎯 Executing Plan for Goal: {goal}")
        return self._run_plan_loop(plan, goal, speak=effective_speak, cancel_flag=cancel_flag)

    def execute(
        self,
        goal:        str,
        speak:       Callable | None        = None,
        cancel_flag: threading.Event | None = None,
    ) -> str:
        effective_speak = speak or self.speak
        print(f"\n[Executor] 🎯 Goal: {goal}")
        plan = create_plan(goal)
        return self._run_plan_loop(plan, goal, speak=effective_speak, cancel_flag=cancel_flag)

    def _run_plan_loop(
        self,
        plan: dict,
        goal: str,
        speak: Callable | None = None,
        cancel_flag: threading.Event | None = None,
    ) -> str:
        replan_attempts = 0
        completed_steps = []
        step_results    = {}

        while True:
            steps = plan.get("steps", [])

            if not steps:
                msg = "I couldn't create a valid plan for this task, Rohan."
                if speak: speak(msg)
                return msg

            success      = True
            failed_step  = None
            failed_error = ""

            for step in steps:
                if cancel_flag and cancel_flag.is_set():
                    if speak: speak("Task cancelled, Rohan.")
                    return "Task cancelled."

                step_num = step.get("step", "?")
                tool     = step.get("tool", "generated_code")
                desc     = step.get("description", "")
                params   = step.get("parameters", {})

                params = _inject_context(params, tool, step_results, goal=goal)

                print(f"\n[Executor] ▶️ Step {step_num}: [{tool}] {desc}")
                if self.player and hasattr(self.player, "update_task_workspace"):
                    try:
                        self.player.update_task_workspace(
                            status=f"Executing Step {step_num}",
                            output=desc or f"Running {tool}...",
                        )
                    except Exception:
                        pass

                attempt = 1
                step_ok = False

                while attempt <= 3:
                    if cancel_flag and cancel_flag.is_set():
                        break
                    try:
                        result = _call_tool(tool, params, speak, player=self.player)
                        step_results[step_num] = result 
                        completed_steps.append(step)
                        print(f"[Executor] ✅ Step {step_num} done: {str(result)[:100]}")
                        step_ok = True
                        break

                    except Exception as e:
                        error_msg = str(e)
                        print(f"[Executor] ❌ Step {step_num} attempt {attempt} failed: {error_msg}")

                        recovery = analyze_error(step, error_msg, attempt=attempt)
                        decision = recovery["decision"]
                        user_msg = recovery.get("user_message", "")

                        if speak and user_msg:
                            speak(user_msg)

                        if decision == ErrorDecision.RETRY:
                            attempt += 1
                            import time; time.sleep(2)
                            continue

                        elif decision == ErrorDecision.SKIP:
                            print(f"[Executor] ⏭️ Skipping step {step_num}")
                            completed_steps.append(step)
                            step_ok = True
                            break

                        elif decision == ErrorDecision.ABORT:
                            msg = f"Task aborted, Rohan. {recovery.get('reason', '')}"
                            if speak: speak(msg)
                            return msg

                        else: 
                            fix_suggestion = recovery.get("fix_suggestion", "")
                            if fix_suggestion and tool != "generated_code":
                                try:
                                    fixed_step = generate_fix(step, error_msg, fix_suggestion)
                                    if speak: speak("Trying an alternative approach, Rohan.")
                                    res = _call_tool(
                                        fixed_step["tool"],
                                        fixed_step["parameters"],
                                        speak,
                                        player=self.player,
                                    )
                                    step_results[step_num] = res
                                    completed_steps.append(step)
                                    step_ok = True
                                    break
                                except Exception as fix_err:
                                    print(f"[Executor] ⚠️ Fix failed: {fix_err}")

                            failed_step  = step
                            failed_error = error_msg
                            success      = False
                            break

                if not step_ok and not failed_step:
                    failed_step  = step
                    failed_error = "Max retries exceeded"
                    success      = False

                if not success:
                    break

            if success:
                return self._summarize(goal, completed_steps, speak)

            if replan_attempts >= self.MAX_REPLAN_ATTEMPTS:
                msg = f"Task failed after {replan_attempts} replan attempts, Rohan."
                if speak: speak(msg)
                return msg

            if speak: speak("Adjusting my approach, Rohan.")

            replan_attempts += 1
            plan = replan(goal, completed_steps, failed_step, failed_error)

    def _summarize(self, goal: str, completed_steps: list, speak: Callable | None) -> str:
        fallback = f"All done, Rohan. Completed {len(completed_steps)} steps for: {goal[:60]}."
        prompt = (
            f'User goal: "{goal}"\n'
            f"Completed steps:\n" + "\n".join(f"- {s.get('description', '')}" for s in completed_steps) + "\n\n"
            "Write a single natural sentence summarizing what was accomplished. "
            "Address the user as 'Rohan'. Be direct, helpful, and positive."
        )
        key = _get_api_key()
        if not key.startswith("AIza"):
            try:
                from or_client import client as ai_client
                res = ai_client.chat(prompt)
                summary = (res or fallback).strip()
                if speak: speak(summary)
                return summary
            except Exception:
                if speak: speak(fallback)
                return fallback

        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model     = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
            response = model.generate_content(prompt)
            summary  = response.text.strip()
            if speak: speak(summary)
            return summary
        except Exception:
            if speak: speak(fallback)
            return fallback
